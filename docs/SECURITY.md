# Security — secrets, authentication, and what is not protected

## Secrets

Nothing sensitive is committed. `.env.local` and `.env.supabase` are ignored, and the CI
and the deployment target inject their own values as repository and Space secrets.

The variables that carry something worth protecting:

| Variable | What leaking it costs |
|---|---|
| `API_KEY` | anyone can score employees against the model and write to the decision log |
| `DATABASE_URL` | direct read and write on the decision log, including the payloads |
| `ANONYMIZATION_KEY` | the HMAC key: with it, an anonymised employee id can be reversed by trying candidates |

`.env.example` carries the names and no values. It is also the file the documentation tells
you to copy, so it is deliberately silent about the threshold: an operator who wants to
override the model card's operating point has to do it knowingly, not by inheriting a
default from an example file.

## Authentication

Every route except `/health` requires an `X-API-Key` header. `/health` is open because a
health check that needs a secret is a health check that fails for the wrong reason.

A single shared key is what this is: a lock on a demonstration service, not an
authorisation model. It gives no notion of who called, so the decision log records *what*
was decided and never *by whom*. A service that fed a real HR process would need per-caller
identity, because "who asked for this employee to be scored" is a question the log would
have to answer.

## The HR data

The extracts describe real employees, and a repository is a public place.

- No complete HR dataset is loaded into the database or committed to the repository.
- The only rows in the repository are ten, kept as request fixtures for the API tests:
  `data/processed/api_test/X_test_sample.json`.
- Employee identifiers are anonymised with HMAC-SHA256 under a key held in the environment.
  HMAC rather than a plain hash because the identifier space is small enough to enumerate:
  an unkeyed SHA-256 of an employee number is reversible by trying every number.

The anonymisation protects the identifier, not the record. A row carries age, department,
job title, salary, marital status and tenure — enough to re-identify someone inside a small
department. That is why the extracts stay out of the repository rather than being published
under pseudonymous ids.

## What the decision log holds

Every prediction writes the exact input payload, the probability, the decision, the
threshold that produced it and the model version. That is what makes a decision auditable
six months later — and it also means **the log contains the same personal data the request
did**. It is a database that would fall under the same handling rules as the source
extracts, and treating it as ordinary application logging would be a mistake.

## What is not protected

- **No rate limiting.** A valid key can be used as fast as the service can answer.
- **No TLS in the local stack.** `docker compose` serves plain HTTP; the header carrying the
  API key is in clear on the wire. The hosted deployment terminated TLS in front of it.
- **No key rotation.** One key, changed by hand.
- **No audit of reads.** `/history` returns decisions and logs nothing about having done so.

None of these matter for an archived demonstration service. All of them would have to be
answered before anything like it went near a real HR system, and listing them is more use
than a security section that says the endpoints are protected and stops there.
