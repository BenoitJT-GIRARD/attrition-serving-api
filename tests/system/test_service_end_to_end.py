"""The service, started the way the README says, questioned the way a caller would.

One `uvicorn` in its own process, a hundred payloads over HTTP, and three assertions a unit
test cannot make: that the key is really required, that the threshold the service applies is
the one the artefact declares, and that the share of employees it flags falls inside the band
the published cost curve says it should.

That last one is the point of the tier. `reports/cost_curve.csv` claims the service flags
about 37 % of employees at the shipped operating point. Nothing in the unit or integration
tiers checks that the running product does; this does, by counting.
"""

from __future__ import annotations

import csv
import json
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest

from attrition_serving.utils.paths import MODELS_DIR, REPORTS_DIR, ROOT_DIR, TESTS_DIR

pytestmark = pytest.mark.system

#: A port nothing else in this repository listens on, so a developer's own service on 8000
#: is neither used by accident nor disturbed.
PORT = 8137
BASE = f"http://127.0.0.1:{PORT}"
KEY = "system-tier-key"

FIXTURES = TESTS_DIR / "fixtures" / "employees_sample.json"
CARD = MODELS_DIR / "model_card.json"
PIPELINE = MODELS_DIR / "pipeline.joblib"
COST_CURVE = REPORTS_DIR / "cost_curve.csv"

#: How many requests the alert rate is measured over. The fixtures hold ten rows, so each is
#: sent ten times with a small perturbation on one continuous column: a hundred draws is
#: enough for a share of 0.37 to be distinguishable from 0.0 or 1.0, which is what this test
#: is for. It is not an estimate of the model's alert rate on a fresh population.
REQUESTS = 100


def _free(port: int) -> bool:
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", port)) != 0


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    """`uvicorn`, in its own process, with no decision log behind it.

    The log is best-effort by design, so the service answers without one, and the answer
    says `stored: false`. Leaving PostgreSQL out is what keeps this tier about the HTTP
    surface: the round trip through the database is the integration tier's job, and it is
    tested there against a real container.
    """
    if not (PIPELINE.exists() and CARD.exists()):
        pytest.skip("run: uv run python scripts/train_export_pipeline.py")
    if not _free(PORT):
        pytest.skip(f"port {PORT} is busy — stop whatever is listening on it")

    environment = {
        **os.environ,
        "SKIP_DOTENV": "1",
        "API_KEY": KEY,
        # A database that answers and cannot hold the schema, which is what "the decision
        # log is unavailable" looks like from the route. An unreachable PostgreSQL would
        # say the same thing and cost two seconds of connect timeout per request, so the
        # hundred calls below would take three minutes to make one point.
        "DATABASE_URL": "sqlite://",
        "MODEL_VERSION": "system-tier",
    }
    environment.pop("MODEL_THRESHOLD", None)
    # The server's output goes to a file, never to a pipe. A hundred requests against an
    # absent database write a hundred tracebacks; a pipe nobody drains fills up, and
    # uvicorn blocks on the write with the test still waiting for its answer.
    log = tmp_path_factory.mktemp("service") / "uvicorn.log"
    handle = log.open("wb")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "attrition_serving.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
            "--log-level",
            "warning",
        ],
        cwd=str(ROOT_DIR),
        env=environment,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = log.read_text(encoding="utf-8", errors="replace")
                pytest.fail(f"the service exited before answering:\n{output[-2000:]}")
            try:
                if httpx.get(f"{BASE}/health", timeout=1.0).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.4)
        else:
            pytest.fail("the service did not answer /health within 45 seconds")
        yield BASE
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        handle.close()


@pytest.fixture(scope="module")
def payloads() -> list[dict]:
    rows = json.loads(FIXTURES.read_text(encoding="utf-8"))
    out: list[dict] = []
    for index in range(REQUESTS):
        row = dict(rows[index % len(rows)])
        # One continuous column nudged, so the hundred requests are not ten identical
        # decisions repeated. Monthly income is the column with the widest range.
        if row.get("revenu_mensuel"):
            step = (index // len(rows)) - 5
            row["revenu_mensuel"] = max(1009, int(row["revenu_mensuel"]) + step * 400)
        out.append(row)
    return out


def test_every_route_but_health_refuses_a_request_without_the_key(service, payloads) -> None:
    assert httpx.get(f"{service}/health", timeout=30).status_code == 200

    unauthorised = httpx.post(f"{service}/predict", json={"features": payloads[0]}, timeout=60)
    assert unauthorised.status_code == 401

    authorised = httpx.post(
        f"{service}/predict",
        json={"features": payloads[0]},
        headers={"X-API-Key": KEY},
        timeout=60,
    )
    assert authorised.status_code == 200


def test_the_running_service_decides_at_the_threshold_the_artefact_declares(
    service, payloads
) -> None:
    """The failure that once shipped, checked against a live process and not an import."""
    declared = float(json.loads(CARD.read_text(encoding="utf-8"))["default_threshold"])

    answer = httpx.post(
        f"{service}/predict",
        json={"features": payloads[0]},
        headers={"X-API-Key": KEY},
        timeout=60,
    ).json()

    assert answer["threshold"] == pytest.approx(declared, abs=1e-9)
    assert answer["model_version"] == "system-tier"
    assert answer["prediction"] == int(answer["proba_depart"] >= declared)
    # The documented best-effort contract, checked on the wire: no log, still an answer,
    # and the answer says so rather than pretending the decision was recorded.
    assert answer["stored"] is False
    assert answer["db_id"] is None


def test_the_alert_rate_the_product_shows_is_the_one_the_cost_curve_publishes(
    service, payloads
) -> None:
    """A hundred real requests, and the share flagged compared with the published band.

    The tolerance is the fold-to-fold spread of the alert rate at the shipped ratio, widened
    to three of them. A hundred draws from ten fixtures is a small and in-sample sample: the
    test is here to catch a threshold that has silently moved, not to re-estimate the rate.
    """
    with COST_CURVE.open(encoding="utf-8") as handle:
        rows = {int(float(row["ratio"])): row for row in csv.DictReader(handle)}
    shipped = rows[int(json.loads(CARD.read_text(encoding="utf-8"))["threshold_cost_ratio"])]
    published = float(shipped["alert_rate_mean"])
    spread = float(shipped["alert_rate_sd"])

    flagged = 0
    with httpx.Client(headers={"X-API-Key": KEY}, timeout=60) as client:
        for features in payloads:
            answer = client.post(f"{service}/predict", json={"features": features})
            assert answer.status_code == 200, answer.text
            flagged += answer.json()["prediction"]

    observed = flagged / len(payloads)
    assert abs(observed - published) <= 3 * spread, (
        f"the service flags {observed:.0%} of the requests where reports/cost_curve.csv "
        f"publishes {published:.0%} ± {spread:.0%} across folds"
    )


def test_an_incomplete_payload_names_every_field_it_is_missing(service, payloads) -> None:
    """One round trip, the whole list. A caller should not discover the contract field by field."""
    incomplete = {k: v for k, v in payloads[0].items() if k not in {"age", "revenu_mensuel"}}

    answer = httpx.post(
        f"{service}/predict",
        json={"features": incomplete},
        headers={"X-API-Key": KEY},
        timeout=60,
    )

    assert answer.status_code == 422
    body = answer.text
    assert "age" in body
    assert "revenu_mensuel" in body
