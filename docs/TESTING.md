# Testing — what each family of tests guarantees

```bash
uv run pytest -q                          # everything; the integration tests skip in 3s
docker compose up -d && uv run pytest -q  # everything, integration included
```

Warnings are errors. The suite has no blanket `ignore::` and needs no exemption: a
deprecation in a dependency fails the run rather than scrolling past it.

## What is covered, and why that and not more

**The served threshold matches the artefact** — `tests/unit/test_served_threshold_matches_artifact.py`.
The single most important test in the repository. The service used to read a key the model
card does not write, fall back to 0.5, and decide at an operating point nothing documented.
This loads the card, calls the service, and fails when the two disagree.

**The shipped artefact loads and predicts.** A scikit-learn pickle names the module that
defined its transformers and the version that wrote it. Renaming the package once made the
shipped model unloadable and nothing noticed, because no test opened it.

**The evaluation protocol** — `tests/unit/test_protocol.py`. That the threshold is chosen on
a split the scoring fold never sees; that a costlier miss lowers the optimal threshold; that
the reliability bins hold equal populations rather than equal widths; that a subgroup with
too few events reports its count and no rate.

**API security and validation** — a missing key is 401, a malformed payload is 422, and an
incomplete one names every field it is missing rather than one per round trip.

**Train/serve consistency** — the frame handed to the pipeline carries the expected columns
in the expected order.

**API ↔ database round trip** — a prediction is written, and the history returns it with the
threshold and the model version that produced it. These need PostgreSQL; without it they
skip in three seconds with a message naming the command that would make them run. They used
to take four and a half minutes to report the same thing, because nothing set a connect
timeout.

## Coverage

```bash
uv run pytest --cov=src --cov-report=term-missing --cov-report=html:reports/coverage_html
```

The number is not a target here. The tests that matter are the ones above, and they assert
published claims rather than executed lines.
