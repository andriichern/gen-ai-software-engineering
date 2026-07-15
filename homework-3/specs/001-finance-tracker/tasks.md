---
description: "Task list for Personal Finance Tracking System implementation"
---

# Tasks: Personal Finance Tracking System

**Input**: Design documents from `/specs/001-finance-tracker/`

**Prerequisites**: spec.md (user stories), plan.md (architecture), data-model.md (entities), contracts/backend-mobile-api.md (API)

**Tests**: Tests are OPTIONAL - unit, integration, UI tests included where critical to specification compliance

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/pkg/{domain}/`, `backend/internal/postgres/`, `backend/cmd/{service}/`, `backend/migrations/`
- **Mobile**: `mobile/lib/{feature}/`, `mobile/lib/core/`, `mobile/test/`
- **Shared**: `mobile/lib/shared/`, `backend/shared/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create backend project structure: `backend/cmd/server/`, `backend/cmd/worker/`, `backend/cmd/migration/`, `backend/pkg/`, `backend/internal/`, `backend/migrations/`, `backend/tests/`
- [ ] T002 Initialize Go project: go.mod, go.sum, Makefile with build/test/run targets
- [ ] T003 [P] Configure Go linting: golangci-lint config (.golangci.yml) with strict rules
- [ ] T004 [P] Configure Go testing: testify setup, fixture directories, test utilities in backend/tests/
- [ ] T005 [P] Create Flutter mobile project structure: pubspec.yaml, lib/{features,core,shared}/, test/
- [ ] T006 [P] Configure Flutter linting: analysis_options.yaml, dart format, effective_dart rules
- [ ] T007 [P] Initialize database: Docker Compose (Postgres 16, Redis optional), local setup script
- [ ] T008 [P] Configure CI/CD pipeline: GitHub Actions for linting, testing, type checking
- [ ] T009 Set up local development environment documentation: README with setup steps, .env.example

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Backend Foundational Infrastructure

- [ ] T010 Implement database schema and migrations framework: `backend/migrations/001_initial_schema.sql` with users, accounts, transactions, audit tables
- [ ] T011 [P] Create sqlc configuration for type-safe queries: sqlc.yaml, code generation setup
- [ ] T012 [P] Implement authentication framework: JWT token generation/validation, session management in `backend/pkg/identity/auth.go`
- [ ] T013 [P] Implement passkey/Webauthn support: `backend/pkg/identity/passkey.go` with Go Webauthn library
- [ ] T014 [P] Implement RLS (Row-Level Security) policies: PostgreSQL RLS setup in migrations, user_id-based isolation
- [ ] T015 [P] Create HTTP server scaffolding: Echo framework setup, middleware in `backend/cmd/server/main.go`
- [ ] T016 [P] Implement middleware stack: auth middleware, logging, rate limiting, CORS in `backend/pkg/http/middleware.go`
- [ ] T017 [P] Set up structured logging: JSON logger in `backend/pkg/telemetry/logger.go` with context fields (user_id, request_id, operation)
- [ ] T018 [P] Configure OpenTelemetry: metrics and tracing setup in `backend/pkg/telemetry/tracer.go`
- [ ] T019 Implement vault service skeleton: PII encryption service in `backend/pkg/vault/` (can be local KMS wrapper initially)
- [ ] T020 Create base repository interfaces: `backend/pkg/storage/` with Transaction, Account, LedgerEvent repository interfaces
- [ ] T021 Implement Postgres repositories: `backend/internal/postgres/transaction_repo.go`, `account_repo.go`, `ledger_repo.go`

### Mobile Foundational Infrastructure

- [ ] T022 Set up SQLite database layer: sqflite or drift ORM in `mobile/lib/core/database/database.dart`
- [ ] T023 [P] Create database schema (SQLite): migrations in `mobile/lib/core/database/migrations/`
- [ ] T024 [P] Implement encrypted storage: flutter_secure_storage wrapper in `mobile/lib/core/local_storage/secure_storage.dart`
- [ ] T025 [P] Implement HTTP client with interceptors: dio setup in `mobile/lib/core/network/api_client.dart` (auth, logging, retry)
- [ ] T026 [P] Implement offline queue manager: `mobile/lib/core/sync/offline_queue.dart` for queuing pending changes
- [ ] T027 [P] Implement sync manager skeleton: `mobile/lib/core/sync/sync_manager.dart` for managing sync state
- [ ] T028 [P] Implement network connectivity detection: `mobile/lib/core/network/connectivity.dart` using connectivity_plus
- [ ] T029 [P] Set up dependency injection: GetIt or Riverpod configuration in `mobile/lib/shared/providers/`
- [ ] T030 Create shared models/DTOs: `mobile/lib/shared/models/` for common data structures

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Manual Transaction Entry (Priority: P1) 🎯 MVP

**Goal**: Enable users to add transactions offline with persistence

**Independent Test**: Open app offline, add transaction (amount, category, account, date), close/reopen app, verify persistence

### Tests for User Story 1 (OPTIONAL)

- [ ] T031 [P] [US1] Unit test Transaction entity validation in `backend/tests/unit/transaction_test.go`
- [ ] T032 [P] [US1] Unit test transaction repository in `backend/tests/unit/postgres/transaction_repo_test.go`
- [ ] T033 [P] [US1] Unit test Flutter transaction DAO in `mobile/test/unit/core/database/transaction_dao_test.dart`
- [ ] T034 [P] [US1] Widget test transaction entry form in `mobile/test/widget/features/transaction/transaction_entry_form_test.dart`
- [ ] T035 [US1] Integration test offline transaction persistence in `mobile/test/integration/offline_transaction_test.dart`

### Implementation for User Story 1

- [ ] T036 [P] [US1] Create Transaction entity in backend: `backend/pkg/domain/transaction.go` with validation (amount >0, date bounds)
- [ ] T037 [P] [US1] Create TransactionObserved canonical model in `backend/pkg/ingestion/canonical.go`
- [ ] T038 [P] [US1] Implement POST /transactions endpoint in `backend/pkg/http/transaction.go`
- [ ] T039 [P] [US1] Implement GET /transactions endpoint with filtering in `backend/pkg/http/transaction.go`
- [ ] T040 [US1] Create transaction service (business logic) in `backend/pkg/domain/transaction_service.go` (depends on T036, T037)
- [ ] T041 [US1] Implement transaction storage: `backend/internal/postgres/transaction_repo.go` InsertTransaction, GetTransactionsByUser methods
- [ ] T042 [P] [US1] Create Category entity in backend: `backend/pkg/domain/category.go` with predefined + custom support
- [ ] T043 [P] [US1] Implement GET /categories endpoint in `backend/pkg/http/category.go`
- [ ] T044 [P] [US1] Create Flutter transaction model: `mobile/lib/features/transaction/domain/entities/transaction.dart`
- [ ] T045 [P] [US1] Create Flutter transaction DAO: `mobile/lib/features/transaction/data/datasources/local/transaction_dao.dart` using sqflite
- [ ] T046 [US1] Implement Flutter transaction repository: `mobile/lib/features/transaction/data/repositories/transaction_repository.dart` (depends on T045)
- [ ] T047 [US1] Implement Flutter transaction usecase: `mobile/lib/features/transaction/domain/usecases/add_transaction.dart`
- [ ] T048 [P] [US1] Create Flutter transaction entry screen: `mobile/lib/features/transaction/presentation/screens/transaction_entry_screen.dart`
- [ ] T049 [P] [US1] Create Flutter transaction list screen: `mobile/lib/features/transaction/presentation/screens/transaction_list_screen.dart`
- [ ] T050 [US1] Create Flutter providers (Riverpod/GetIt): `mobile/lib/features/transaction/presentation/providers/` for state management
- [ ] T051 [US1] Wire up transaction entry form validation: amount, date, description validation in `mobile/lib/features/transaction/presentation/widgets/`
- [ ] T052 [US1] Implement local transaction persistence: save to SQLite on form submit in transaction repository

**Checkpoint**: User Story 1 fully functional and testable independently (users can add transactions offline and they persist)

---

## Phase 4: User Story 2 - Bank API Integration & Transaction Retrieval (Priority: P1)

**Goal**: Retrieve transactions from GoCardless + Salt Edge bank APIs

**Independent Test**: Connect mock bank API, trigger sync, verify transactions retrieved and displayed with API source label

### Tests for User Story 2 (OPTIONAL)

- [ ] T053 [P] [US2] Unit test GoCardless adapter in `backend/tests/unit/ingestion/gocardless_adapter_test.go`
- [ ] T054 [P] [US2] Unit test Salt Edge adapter in `backend/tests/unit/ingestion/saltedge_adapter_test.go`
- [ ] T055 [P] [US2] Unit test transaction matching algorithm in `backend/tests/unit/matching/matcher_test.go`
- [ ] T056 [P] [US2] Contract test mobile ↔ backend API in `backend/tests/contract/transactions_contract_test.go` using pact-go
- [ ] T057 [US2] Integration test bank sync workflow in `backend/tests/integration/bank_sync_test.go` with testcontainers

### Implementation for User Story 2

- [ ] T058 [P] [US2] Create Aggregator interface: `backend/pkg/ingestion/aggregator.go` with Sync() method
- [ ] T059 [P] [US2] Implement GoCardless adapter: `backend/pkg/ingestion/gocardless/adapter.go` with transaction retrieval, pagination
- [ ] T060 [P] [US2] Implement Salt Edge adapter: `backend/pkg/ingestion/saltedge/adapter.go` with transaction retrieval, pagination
- [ ] T061 [P] [US2] Create BankAPIConnection entity: `backend/pkg/domain/bank_api_connection.go` with credential storage, sync status
- [ ] T062 [US2] Implement bank connection storage: `backend/internal/postgres/bank_api_connection_repo.go` InsertConnection, GetConnections, UpdateSyncStatus
- [ ] T063 [US2] Implement ingestion service: `backend/pkg/ingestion/ingestion_service.go` orchestrates GoCardless/Salt Edge sync, transforms to TransactionObserved
- [ ] T064 [P] [US2] Create POST /bank-connections endpoint: `backend/pkg/http/bank_api.go` with OAuth initiation
- [ ] T065 [P] [US2] Create POST /bank-connections/callback endpoint: OAuth callback handler
- [ ] T066 [P] [US2] Create POST /bank-connections/{id}/sync endpoint: manual sync trigger
- [ ] T067 [P] [US2] Create GET /bank-connections endpoint: list user's connected banks
- [ ] T068 [P] [US2] Create POST /bank-connections/{id}/revoke endpoint: disconnect bank
- [ ] T069 [US2] Implement background worker for scheduled syncs: `backend/cmd/worker/main.go` with cron-based bank sync (default daily)
- [ ] T070 [US2] Create Permission entity: `backend/pkg/domain/permission.go` for PSD2 90-day scope expiry tracking (depends on T061)
- [ ] T071 [P] [US2] Create Flutter bank connection model: `mobile/lib/features/bank_sync/domain/entities/bank_connection.dart`
- [ ] T072 [P] [US2] Create Flutter bank connection repository: `mobile/lib/features/bank_sync/data/repositories/bank_connection_repository.dart`
- [ ] T073 [P] [US2] Create Flutter bank sync service: `mobile/lib/core/sync/bank_sync_service.dart` orchestrates sync, updates local DB
- [ ] T074 [P] [US2] Create Flutter bank connection screen: `mobile/lib/features/bank_sync/presentation/screens/bank_connection_screen.dart` with OAuth flow
- [ ] T075 [P] [US2] Create Flutter sync status widget: displays "Syncing...", "Synced", "Error" state in `mobile/lib/features/bank_sync/presentation/widgets/`
- [ ] T076 [US2] Wire up bank sync: integrate sync_manager with bank API calls, update transaction list on sync completion

**Checkpoint**: User Story 2 fully functional (users can connect banks, transactions retrieved and displayed with API source)

---

## Phase 5: User Story 3 - Transaction Matching & Conflict Resolution (Priority: P2)

**Goal**: Detect and allow user confirmation of duplicate transactions (manual vs API)

**Independent Test**: Add manual transaction, sync bank API with matching transaction, verify match flagged with confidence score, user can confirm/reject

### Tests for User Story 3 (OPTIONAL)

- [ ] T077 [P] [US3] Unit test matching algorithm with fuzzy logic in `backend/tests/unit/matching/matcher_test.go`
- [ ] T078 [P] [US3] Unit test TransactionMatch entity in `backend/tests/unit/domain/transaction_match_test.go`
- [ ] T079 [P] [US3] Widget test match review screen in `mobile/test/widget/features/matching/match_review_screen_test.dart`
- [ ] T080 [US3] Integration test end-to-end matching workflow in `backend/tests/integration/matching_test.go`

### Implementation for User Story 3

- [ ] T081 [P] [US3] Create TransactionMatch entity: `backend/pkg/matching/match.go` with confidence scoring
- [ ] T082 [P] [US3] Implement fuzzy matching algorithm: `backend/pkg/matching/matcher.go` with amount delta (±10%), date delta (±1 day), description similarity
- [ ] T083 [P] [US3] Create matching service: `backend/pkg/matching/matching_service.go` identifies potential matches between manual and API transactions
- [ ] T084 [US3] Implement match storage: `backend/internal/postgres/transaction_match_repo.go` InsertMatch, UpdateMatchStatus, GetPendingMatches
- [ ] T085 [P] [US3] Create POST /transaction-matches/{id}/confirm endpoint in `backend/pkg/http/matching.go`
- [ ] T086 [P] [US3] Create POST /transaction-matches/{id}/reject endpoint in `backend/pkg/http/matching.go`
- [ ] T087 [P] [US3] Create GET /transaction-matches endpoint with filtering in `backend/pkg/http/matching.go`
- [ ] T088 [US3] Implement ledger posting on match confirmation: ensure single posting for matched pair, prevent double-counting (depends on T085)
- [ ] T089 [P] [US3] Create Flutter TransactionMatch model: `mobile/lib/features/matching/domain/entities/transaction_match.dart`
- [ ] T090 [P] [US3] Create Flutter matching repository: `mobile/lib/features/matching/data/repositories/matching_repository.dart`
- [ ] T091 [P] [US3] Create Flutter match review screen: `mobile/lib/features/matching/presentation/screens/match_review_screen.dart` showing both versions with confidence
- [ ] T092 [P] [US3] Create match action buttons (confirm/reject): `mobile/lib/features/matching/presentation/widgets/match_action_buttons.dart`
- [ ] T093 [US3] Wire up match confirmation: call backend endpoint, update local DB, refresh transaction list on match confirmation

**Checkpoint**: User Story 3 fully functional (matches detected, user can confirm/reject, no double-counting)

---

## Phase 6: User Story 4 - Multi-Account Management (Priority: P2)

**Goal**: Support multiple account types (credit card, debit card, savings, cash) with account-specific metadata

**Independent Test**: Create 3 accounts (credit card + savings + cash), add transactions to each, verify balances accurate and transactions segregated

### Tests for User Story 4 (OPTIONAL)

- [ ] T094 [P] [US4] Unit test Account entity with account types in `backend/tests/unit/domain/account_test.go`
- [ ] T095 [P] [US4] Unit test balance calculation in `backend/tests/unit/domain/balance_calculation_test.go`
- [ ] T096 [P] [US4] Widget test account creation screen in `mobile/test/widget/features/account/account_creation_screen_test.dart`
- [ ] T097 [US4] Integration test account balance updates in `backend/tests/integration/account_balance_test.go`

### Implementation for User Story 4

- [ ] T098 [P] [US4] Enhance Account entity: `backend/pkg/domain/account.go` with type enum, account-specific fields (credit_limit, interest_rate)
- [ ] T099 [P] [US4] Create account service: `backend/pkg/domain/account_service.go` with balance calculation, account creation/editing
- [ ] T100 [P] [US4] Enhance account storage: `backend/internal/postgres/account_repo.go` CreateAccount, UpdateAccount, GetUserAccounts, GetAccountBalance
- [ ] T101 [P] [US4] Create POST /accounts endpoint in `backend/pkg/http/account.go`
- [ ] T102 [P] [US4] Create GET /accounts endpoint with all accounts in `backend/pkg/http/account.go`
- [ ] T103 [P] [US4] Create GET /accounts/{id} endpoint with balance details in `backend/pkg/http/account.go`
- [ ] T104 [P] [US4] Create PUT /accounts/{id} endpoint for account updates in `backend/pkg/http/account.go`
- [ ] T105 [P] [US4] Create POST /accounts/{id}/archive endpoint for soft-delete in `backend/pkg/http/account.go`
- [ ] T106 [US4] Implement balance calculation in service: sum all transactions (manual + API) for account, handle matched transactions (no double-count)
- [ ] T107 [P] [US4] Create Flutter Account model: `mobile/lib/features/account/domain/entities/account.dart` with type enum
- [ ] T108 [P] [US4] Create Flutter account DAO: `mobile/lib/features/account/data/datasources/local/account_dao.dart`
- [ ] T109 [P] [US4] Create Flutter account repository: `mobile/lib/features/account/data/repositories/account_repository.dart`
- [ ] T110 [P] [US4] Create account creation screen: `mobile/lib/features/account/presentation/screens/account_creation_screen.dart` with type selection
- [ ] T111 [P] [US4] Create account list screen: `mobile/lib/features/account/presentation/screens/account_list_screen.dart` showing all accounts with icons and balances
- [ ] T112 [P] [US4] Create account detail screen: `mobile/lib/features/account/presentation/screens/account_detail_screen.dart` with balance and credit limit info
- [ ] T113 [US4] Wire up account selection in transaction entry: allow user to select account when adding transaction

**Checkpoint**: User Story 4 fully functional (multiple accounts created, transactions segregated, balances accurate)

---

## Phase 7: User Story 5 - Offline Sync & Data Consistency (Priority: P3)

**Goal**: Auto-sync pending changes when network restored; handle conflicts gracefully

**Independent Test**: Add transactions offline, go online, verify sync completes within 30s with zero data loss, sync visible on other devices

### Tests for User Story 5 (OPTIONAL)

- [ ] T114 [P] [US5] Unit test offline queue management in `mobile/test/unit/core/sync/offline_queue_test.dart`
- [ ] T115 [P] [US5] Unit test conflict resolution in `mobile/test/unit/core/sync/conflict_resolver_test.dart`
- [ ] T116 [P] [US5] Integration test multi-device sync in `backend/tests/integration/multidevice_sync_test.go`
- [ ] T117 [US5] E2E test offline→online transition in `mobile/test/integration/offline_online_transition_test.dart`

### Implementation for User Story 5

- [ ] T118 [P] [US5] Implement offline queue: `mobile/lib/core/sync/offline_queue.dart` with local queuing of pending changes (transactions, matches, account updates)
- [ ] T119 [P] [US5] Implement conflict resolver: `mobile/lib/core/sync/conflict_resolver.dart` presenting both versions to user for selection
- [ ] T120 [P] [US5] Implement batch sync protocol: `backend/pkg/http/sync.go` POST /sync endpoint accepting batched changes
- [ ] T121 [US5] Implement sync response handler: merge server updates with local state, apply conflict resolutions (depends on T119)
- [ ] T122 [P] [US5] Enhance sync manager: `mobile/lib/core/sync/sync_manager.dart` auto-triggers on network reconnection, manages batch uploads
- [ ] T123 [P] [US5] Implement network state listener: auto-sync when connectivity changes in `mobile/lib/core/network/connectivity_listener.dart`
- [ ] T124 [P] [US5] Create sync status/UI indicator: `mobile/lib/features/dashboard/widgets/sync_status_widget.dart` showing "Syncing...", "Synced", "Pending X changes"
- [ ] T125 [US5] Implement eventual consistency validation: backend merges updates, returns confirmation with server state (depends on T121)
- [ ] T126 [US5] Create backend conflict detection: identify conflicting edits to same entity and flag for user resolution

**Checkpoint**: User Story 5 fully functional (offline changes queue, auto-sync on reconnect, conflicts resolved by user)

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories, security, compliance, performance

### Security & Compliance

- [ ] T127 [P] Conduct security review of auth system: passkey implementation, JWT handling, session timeout in `backend/pkg/identity/`
- [ ] T128 [P] Conduct security review of API credential storage: encryption in vault, access controls in `backend/pkg/vault/`
- [ ] T129 [P] Implement encryption for sensitive data: PII isolation, transaction encryption at rest in `backend/internal/postgres/`
- [ ] T130 [P] Verify OWASP Top 10 mitigations: input validation, rate limiting, CSRF tokens, secure session management, dependency scanning
- [ ] T131 [P] Verify GDPR compliance: data export endpoint, deletion endpoint, consent tracking in `backend/pkg/http/`
- [ ] T132 [P] Verify PSD2 compliance: permission state machine, 90-day expiry enforcement in `backend/pkg/permission/`
- [ ] T133 [P] Verify audit logging: immutable ledger, operation logging in `backend/pkg/telemetry/`
- [ ] T134 Conduct penetration testing: auth bypass attempts, SQL injection attempts, XSS attempts

### Testing & Coverage

- [ ] T135 [P] Add unit tests for all domain entities: transaction, account, match, permission in `backend/tests/unit/domain/`
- [ ] T136 [P] Add integration tests for all repositories: `backend/tests/integration/` with testcontainers
- [ ] T137 [P] Verify ≥85% code coverage for backend core logic: matching, ledger, balance calc
- [ ] T138 [P] Add Flutter widget tests for all screens: `mobile/test/widget/features/*/`
- [ ] T139 [P] Add Flutter integration tests for critical flows: transaction entry→persistence, bank sync, offline→online
- [ ] T140 [P] Add Flutter UI tests using Patrol: transaction entry, matching, account management
- [ ] T141 Verify ≥80% code coverage for Flutter core logic: repositories, usecases, services

### Performance Optimization

- [ ] T142 [P] Profile backend API queries: identify slow queries in transaction list, matching, balance calc
- [ ] T143 [P] Optimize Postgres queries: add indexes on user_id, posted_date, account_id; verify p95 latency <500ms
- [ ] T144 [P] Optimize mobile database queries: SQLite indexes, query optimization; verify <100ms p95
- [ ] T145 [P] Profile mobile app load time: startup, transaction list rendering; verify <2s first load on 4G
- [ ] T146 [P] Implement caching: backend API response caching (Redis optional), mobile local view caching
- [ ] T147 Profile bank sync performance: verify 1000+ transactions sync in <30s
- [ ] T148 Profile matching performance: verify 10k transaction matches in <1s

### Observability & Monitoring

- [ ] T149 [P] Configure structured logging across backend: JSON format with context fields in all services
- [ ] T150 [P] Set up metrics collection: API latency, sync latency, matching accuracy, error rates via OpenTelemetry
- [ ] T151 [P] Configure distributed tracing: trace requests mobile app → backend → external APIs
- [ ] T152 [P] Set up alerting: high latency (>1s), error rate spikes (>1%), failed syncs (>5%), DB unavailability (>30s)
- [ ] T153 [P] Create operations dashboard: system health, active users, error rates, key business metrics

### Documentation & Validation

- [ ] T154 [P] [P] Document quickstart guide in `README.md`: local dev setup, running tests, starting app/backend
- [ ] T155 [P] Document API endpoints: request/response examples for all endpoints in `docs/API.md` (or openapi.yaml)
- [ ] T156 [P] Document database schema: ER diagram, table descriptions in `docs/SCHEMA.md`
- [ ] T157 [P] Document deployment process: Docker build, CI/CD pipeline, environment variables
- [ ] T158 Run specification validation: verify all acceptance scenarios pass from quickstart.md
- [ ] T159 Run compliance validation: GDPR right-to-be-forgotten, PSD2 scope expiry, PCI-DSS handling
- [ ] T160 Run performance benchmarks: latency, throughput, concurrent users; report against SC-005, SC-006

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS all user stories**
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (Phase 3) and US2 (Phase 4): Independent, can run in parallel
  - US3 (Phase 5): Depends on US1 + US2 (needs both manual and API transactions)
  - US4 (Phase 6): Depends on US1 (needs transaction storage)
  - US5 (Phase 7): Depends on US1, US2, US3, US4 (consolidates all features)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Setup → Foundational → (US1 + US2) → US3 → US4 → US5 → Polish
                             ↓
                        (Run in parallel)
```

- **US1 (Manual entry)**: Depends on Foundational - **MVP**: Can stop after US1, feature delivers value
- **US2 (Bank sync)**: Depends on Foundational, independent from US1 (can run parallel)
- **US3 (Matching)**: Depends on US1 + US2 (needs both transaction sources)
- **US4 (Multi-account)**: Depends on US1 (transaction persistence)
- **US5 (Offline sync)**: Depends on US1-4 (consolidates all features)

### Within Each User Story

1. Tests written (FAIL by design - TDD)
2. Entity/model creation
3. Repository/service implementation
4. Endpoint/UI implementation
5. Integration & validation
6. Story marked complete and independently testable

### Parallel Opportunities

**Setup Phase**:
- All tasks [P] can run in parallel: Go setup, Flutter setup, DB setup, CI/CD setup

**Foundational Phase** (within same component):
- Backend foundation tasks [P]: auth, RLS, logging, vault (don't depend on each other)
- Mobile foundation tasks [P]: database, storage, HTTP client, sync manager (don't depend on each other)

**User Story Phases**:
- US1 and US2 can run fully in parallel (different services, endpoints, models)
- Within each story: Tests [P] can run parallel, entity creation [P] can run parallel, but services depend on entities

**Example: Parallel US1 + US2**:
```
US1 Tasks in Parallel:
  - T036: Transaction entity
  - T042: Category entity
  - T044: Flutter transaction model
  - T048: Flutter transaction entry screen

US2 Tasks in Parallel (same time):
  - T058: Aggregator interface
  - T059: GoCardless adapter
  - T061: BankAPIConnection entity
  - T072: Flutter bank connection repository
```

---

## Implementation Strategy

### MVP First (Recommended - 2-4 weeks)

**Goal**: User Story 1 only - users can add transactions offline and see them in a list

1. Complete Phase 1: Setup (1-2 days)
2. Complete Phase 2: Foundational (2-3 days)
3. Complete Phase 3: User Story 1 (3-4 days)
4. **STOP and VALIDATE**: Test User Story 1 independently per quickstart.md
5. Deploy/demo if ready
6. **Users can now add transactions offline** ✅

### Incremental Delivery (Recommended - 6-8 weeks for full feature)

1. **Sprint 1**: Setup + Foundational + US1 → users add transactions offline
2. **Sprint 2**: US2 + early US3 → users connect banks, see API transactions
3. **Sprint 3**: US3 + US4 → users match duplicates, manage multiple accounts
4. **Sprint 4**: US5 + Polish → offline sync works, security reviewed, performance optimized

### Parallel Team Strategy (3-4 developers)

1. **Developer A + B**: Setup + Foundational (days 1-5)
2. Once Foundational done:
   - **Developer A**: US1 (manual entry)
   - **Developer B**: US2 (bank sync)
   - **Developer C**: Awaits... then US3 (matching)
3. Stories complete and integrate independently
4. All team: US5 (offline sync), then Polish

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests FAIL before implementing (TDD approach, optional but recommended)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
