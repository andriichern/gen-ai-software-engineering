# Research Notes

## Query 1: Python project structure, module organization, imports, error handling, file I/O
- Search: "PEP 8 style conventions, module/package project structure, error handling with exceptions, file I/O and pathlib idioms, module imports and __init__.py conventions"
- context7 library ID: /python/cpython
- Applied: Used the standard package layout with `__init__.py` per package (`pipeline/`, `lib/`, each `services/<stage>/`), one class/dataclass per concern, stdlib-first import ordering (stdlib, third-party, local), and specific `except FileNotFoundError` / `except OSError` subclasses rather than bare `except Exception` for file I/O in the orchestrator and stage CLIs. Used `pathlib.Path` throughout for `shared/` tree manipulation instead of `os.path`.

## Query 2: FastAPI project structure, routing, request/response models, retries/timeouts
- Search: "FastAPI project structure, routing, request/response models, TestClient for in-process testing, calling other services with httpx including retries and timeouts"
- context7 library ID: /websites/fastapi_tiangolo
- Applied: Each service defines its request/response contract with Pydantic `BaseModel`s and a single `POST /score` (or equivalent) route via `APIRouter`, matching the "uniform contract" requirement. The gateway uses `httpx.Client(timeout=...)` for outbound calls to stage services, wrapping each call in a manual retry loop (3 attempts) per the spec's failure-handling rule.

## Query 3: FastAPI TestClient / async HTTPX client for in-process testing
- Search: "TestClient usage example importing app and making requests, using httpx.Client with timeout for outbound calls"
- context7 library ID: /websites/fastapi_tiangolo
- Applied: Self-test (Step 8) uses `fastapi.testclient.TestClient(app)` to exercise each of the 5 services in-process (no port binding, no hang risk) for the "valid request" and "empty context" checks. Only the gateway's outbound-HTTP and retry-then-skip path required actually starting uvicorn processes in the background with a hard timeout.

## Query 4: pycountry currency lookup for ISO 4217 validation
- Search: "look up currency by alpha_3 code to validate ISO 4217 currency code"
- context7 library ID: /pycountry/pycountry
- Applied: Validation uses `pycountry.currencies.get(alpha_3=code)` to check ISO 4217 compliance instead of embedding a currency list, per the spec's "research a real currency package" instruction. `pycountry` was already present in the project's environment and ranked highest (benchmark 93.17) among candidates, so it was chosen over hand-rolling a currency list.

## Query 5: Free, open, live exchange-rate source
- Search: "free open live exchange rate API for currency conversion" / "free open access endpoint without API key for latest exchange rates"
- context7 library ID: /websites/exchangerate-api
- Applied: The orchestrator fetches live rates from the Open Access endpoint `https://open.er-api.com/v6/latest/USD` (no API key required, per the docs), used by Fraud Detection to convert any transaction currency to its USD equivalent for the high-value ($10,000 USD equivalent) check. Chosen because it is genuinely free/open (no key, no signup) and returns a real-time `rates` object keyed by ISO 4217 code, matching the spec's requirement for a "real free/open live exchange-rate source."
