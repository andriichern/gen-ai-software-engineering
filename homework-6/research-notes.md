# Research Notes

## Query 1: Python style conventions, module layout, idiomatic error handling and I/O
- Search: "PEP 8 naming conventions, package/module layout, and idiomatic error handling with exceptions, pathlib file I/O, and decimal.Decimal for precise arithmetic"
- context7 library ID: /python/cpython
- Applied: snake_case function/module names, one stage per module; specific `except FileNotFoundError` / `except PermissionError` style exception handling instead of bare `except`; `pathlib.Path` used throughout for all file I/O in the orchestrator and stage modules instead of raw `os.path` string joins; `decimal.Decimal` constructed directly from the amount string (never via `float`) for every monetary value.

## Query 2: ISO 4217 currency validation package
- Search: "look up ISO 4217 currency code validity by alpha code"
- context7 library ID: /pycountry/pycountry
- Applied: `pycountry.currencies.get(alpha_3=code)` used in `pipeline/validation.py` to confirm a currency code is real ISO 4217 rather than embedding a hand-maintained code list. Chosen over hand-rolled tables because it is the highest-reputation (Medium/High source, 93.17 benchmark) dedicated ISO data package for Python found in context7, and it is already available in the local environment.

## Query 3: Python project/package structure conventions
- Search: "src layout package directory structure with multiple modules, __init__.py usage, and entry point / CLI script conventions"
- context7 library ID: /pypa/packaging.python.org
- Applied: for a non-distributed, script-run project (no `pyproject.toml`/build step), the guide's "flat layout" variant applies — a plain package directory (`pipeline/`) containing an `__init__.py` plus one flat module per stage, run directly with `python -m` or as a plain script rather than installed. Confirms `if __name__ == "__main__":` as the idiomatic per-stage CLI entry point pattern, used in every `pipeline/*.py` module and in `orchestrator.py`.

## Query 4: HTTP GET with timeout/retry and error handling
- Search: "GET request with timeout and raise_for_status error handling, retries pattern"
- context7 library ID: /psf/requests
- Applied: `requests.get(url, timeout=...)` plus `response.raise_for_status()` used in the orchestrator's exchange-rate fetch, wrapped in a manual retry loop (3 attempts, 3s delay, per specification.md Step 6) since the request is a single one-shot call (a mounted `Retry` adapter was considered but the spec's explicit "3 retries / 3s delay / hard-fail" contract is simpler to express directly).

## Query 5: Free, open, live exchange-rate source
- Search: "free live currency exchange rate API without API key"
- context7 library ID: /websites/frankfurter_dev
- Applied: `GET https://api.frankfurter.dev/v2/rates?base=USD&quotes=<currencies>` used in the orchestrator to fetch live ECB reference rates for exactly the non-USD currencies present in the input, once per run. Chosen over commercial rate APIs because it requires no API key/signup (avoiding a hard dependency the self-test could never satisfy) and is a real institutional (ECB) reference source, per specification.md's requirement for "a real free/open live exchange-rate source."

## Query 6: uuid module and UTC timestamp generation
- Search: "uuid module uuid4 generate unique identifier and datetime.now(timezone.utc) for ISO 8601 UTC timestamps"
- context7 library ID: /python/cpython
- Applied: `uuid.uuid4()` (stdlib) used for every `message_id` and settlement reference; `datetime.now(timezone.utc).isoformat()` used for every timestamp written anywhere in the pipeline (audit entries, message envelopes, status.json, settlement timestamps), never a naive/local datetime.
