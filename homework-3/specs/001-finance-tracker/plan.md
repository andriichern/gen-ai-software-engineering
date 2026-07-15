# Implementation Plan: Personal Finance Tracking System

**Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-finance-tracker/spec.md`

**Note**: This plan describes the Go backend architecture with modular monolith design, dual bank API aggregators, and compliance-first implementation.

## Summary

Build a personal finance tracking system with offline-first mobile app (Flutter/Dart for iOS 14+ & Android 11+) and Go backend. Core features: manual transaction entry, bank API integration (GoCardless + Salt Edge), transaction deduplication, multi-account support, and regulatory compliance (GDPR, PSD2, PSD3, DORA). Mobile uses SQLite for local persistence and encrypted credential storage. Backend uses modular monolith architecture with Postgres 16 RLS, separate vault service for PII, and append-only ledger for financial events. Target: 99% uptime, <500ms API p95 latency, mobile-first UX, zero-knowledge architecture for transaction matching.

## Technical Context

**Language/Version**: Go 1.21+ (backend); Flutter 3.13+ with Dart 3.1+ (mobile apps for iOS 14+, Android 11+)

**Primary Dependencies**:

- **Backend**: Echo/chi HTTP framework, PostgreSQL 16 (sqlc for type-safe queries), passkeys (Webauthn), JWT, GoCardless SDK, Salt Edge SDK, OpenTelemetry, testify, testcontainers
- **Mobile**: Flutter 3.13+, Dart 3.1+, SQLite (sqflite or drift for local DB), flutter_secure_storage (encrypted credential storage), HTTP client (dio or http), local_auth (biometric), connectivity_plus (network state)
- **Infrastructure**: Docker, Kubernetes (optional), Cloud KMS (AWS/Azure) for key management

**Storage**: PostgreSQL 16 with Row-Level Security (RLS), append-only event ledger, separate encrypted vault service for PII

**Testing**: Go `testing` package + testify (unit), testcontainers (integration), pact-go (contract), Flutter test + mockito (unit), integration_test (Flutter E2E), Patrol (UI testing)

**Target Platform**: Linux server (backend), iOS/Android (mobile)

**Project Type**: Modular monolith (backend, Go) + cross-platform mobile app (Flutter/Dart for iOS & Android)

**Performance Goals**:

- API: <500ms p95 latency for all endpoints
- Mobile: <2s cold start, <500ms transaction list load
- Database: <100ms query p95 for transaction queries with 1M+ records
- Bank sync: Complete 1000+ transactions in <30s
- Matching: <1s to match 10k pending transactions

**Constraints**:

- Zero downtime deployments (blue-green, canary)
- All financial data encrypted in transit (TLS 1.3) and at rest (AES-256)
- Eventual consistency across devices (conflict-free merges)
- 99% uptime SLA (max ~7.2 hours downtime/month)
- GDPR right-to-be-forgotten in <30 days
- Compliance: GDPR, PSD2/PSD3, DORA, PCI-DSS, UK DPA 2018

**Scale/Scope**:

- 100k+ concurrent users (peak)
- 10M+ transactions/month
- 5 major bank API integrations (phase 1)
- 3-6 month MVP delivery
- 9 backend domains, 2 mobile apps (iOS/Android)

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

**Code Quality Standards** ✅

- Go code must pass `golangci-lint` with zero errors/warnings (strict config)
- All public functions require godoc comments with examples
- Transaction matching and ledger logic abstracted to reusable packages
- Maximum cyclomatic complexity: 10 per function (reconciliation may require review)
- Variable naming: `userID`, `transactionAmount`, `bankAPICredential` (no abbreviations)
- **Status**: PASS — modular monolith design enables isolated testing and clarity

**Testing Excellence** ✅

- Backend: Unit tests (testify, mockito), integration tests (testcontainers), contract tests (pact-go); target ≥85% coverage
- Mobile (Flutter): Unit tests (flutter_test + mockito), widget tests (flutter_test), integration tests (integration_test), UI tests (Patrol); target ≥80% coverage
- Edge cases: Future dates, offline weeks, concurrent syncs, matching edge cases, crash recovery, conflict resolution
- **Status**: PASS — testcontainers (backend) and flutter_test + Patrol (mobile) enable comprehensive testing

**UX Consistency** ✅

- Flutter app uses Material 3 design (default) with platform-aware widgets (CupertinoButton for iOS, Material buttons for Android)
- Consistent transaction entry flow; adaptable UI for screen sizes
- Clear offline/online state indicators (connectivity_plus integration)
- Accessible: Semantic widgets, sufficient contrast, WCAG 2.1 AA equivalent
- **Status**: PASS — Flutter's single codebase enables consistency; platform-aware widgets provide native feel

**Performance** ✅

- Backend: <500ms p95 API latency (indexed queries, connection pooling, caching)
- Mobile: <2s cold start (Flutter app initialization), <500ms incremental updates, <100ms SQLite queries
- Database: Postgres RLS + indexing for backend; SQLite optimized for local queries
- **Status**: PASS — Go backend optimized for throughput; Flutter + SQLite optimized for mobile responsiveness

**Compliance** ✅

- Security review: Auth (passkeys+JWT), API credential storage (vault), transaction encryption
- Input validation: All inputs validated; no SQL injection (sqlc), no XSS
- Sensitive data: PII isolated in vault, financial data encrypted, audit logs immutable
- OWASP Top 10: Rate limiting, CSRF tokens, secure sessions, dependency scanning
- Regulatory: GDPR (export/deletion), PSD2 (consent), DORA (observability), PCI-DSS (vault)
- **Status**: PASS — Vault service and consent/permission domains address key concerns

**Overall Gate Status**: ✅ PASS — Architecture aligns with all constitution principles. No unjustified violations.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

**Backend** (Go modular monolith):

````text
backend/
├── cmd/
│   ├── server/              # HTTP server entry point
│   ├── worker/              # Async job worker (bank sync, matching)
│   └── migration/           # DB migration runner
├── pkg/
│   ├── identity/            # Auth, sessions, passkeys
│   │   ├── auth.go
│   │   ├── session.go
│   │   └── passkey.go
│   ├── permission/          # PSD2 permission state machine
│   │   ├── permission.go    # 90-day expiry, scope validation
│   │   └── dashboard.go     # Permission dashboard
│   ├── consent/             # GDPR lawful basis tracking
│   │   ├── consent.go
│   │   └── audit.go
│   ├── ingestion/           # Bank API aggregators
│   │   ├── aggregator.go    # Common aggregator interface
│   │   ├── gocardless/      # GoCardless adapter (primary)
│   │   ├── saltedge/        # Salt Edge adapter (secondary)
│   │   └── canonical.go     # TransactionObserved canonical model
│   ├── matching/            # Transaction deduplication
│   │   ├── matcher.go       # Fuzzy matching algorithm
│   │   ├── lifecycle.go     # provisional → confirmed state machine
│   │   └── confidence.go    # Matching confidence scoring
│   ├── ledger/              # Append-only double-entry journal
│   │   ├── journal.go       # Only writer, immutable events
│   │   ├── posting.go       # Double-entry accounting primitives
│   │   └── reconcile.go     # Balance verification
│   ├── categorisation/      # Transaction categorization
│   │   ├── rules.go         # Rule-based categorization
│   │   └── model.go         # ML-based categorization (future)
│   ├── insights/            # Read models, derived data
│   │   ├── dashboard.go     # User dashboard projections
│   │   ├── trends.go        # Spending trends, analytics
│   │   └── reconcile.go     # View refresh on ledger updates
│   ├── vault/               # PII encryption (separate service)
│   │   ├── kms.go           # Key management
│   │   ├── encrypt.go       # Per-user DEK encryption
│   │   └── decrypt.go       # Decryption with audit
│   ├── http/                # HTTP handlers
│   │   ├── transaction.go
│   │   ├── account.go
│   │   ├── bank_api.go
│   │   └── middleware.go    # Auth, logging, rate limiting
│   ├── storage/             # Repository interfaces
│   │   ├── transaction.go
│   │   ├── account.go
│   │   └── ledger.go
│   └── telemetry/           # Observability
│       ├── logger.go        # Structured logging
│       ├── metrics.go       # Prometheus/OpenTelemetry
│       └── tracer.go        # Distributed tracing
├── internal/
│   ├── postgres/            # PostgreSQL implementations
│   │   ├── transaction_repo.go
│   │   ├── account_repo.go
│   │   └── migrations/      # sqlc-generated code
│   └── mock/                # Test mocks
├── migrations/              # Database migrations (numbered)
│   ├── 001_create_users.sql
│   ├── 002_create_accounts.sql
│   ├── 003_create_ledger.sql
│   └── ...
├── tests/
│   ├── integration/         # Integration tests
│   ├── contract/            # Pact contract tests
│   └── fixtures/            # Test data
├── go.mod
├── Makefile
└── docker-compose.yml       # Local Postgres, Redis

Mobile (Flutter/Dart for iOS & Android):
```text
mobile/
├── pubspec.yaml                 # Flutter dependencies (sqflite, dio, local_auth, etc.)
├── lib/
│   ├── main.dart                # App entry point
│   ├── app/
│   │   ├── app.dart             # Material/Cupertino app config
│   │   └── themes/              # App theming
│   ├── features/
│   │   ├── transaction/
│   │   │   ├── presentation/    # UI (screens, widgets)
│   │   │   ├── domain/          # Business logic (entities, usecases)
│   │   │   └── data/            # Data sources (local DB, API)
│   │   ├── account/             # Account management feature
│   │   ├── bank_sync/           # Bank API integration feature
│   │   ├── auth/                # Authentication feature
│   │   └── dashboard/           # Dashboard/insights feature
│   ├── core/
│   │   ├── database/            # SQLite setup (sqflite/drift)
│   │   │   ├── database.dart
│   │   │   └── migrations/      # DB schema migrations
│   │   ├── network/             # HTTP client (dio)
│   │   │   ├── api_client.dart
│   │   │   └── interceptors/    # Auth, logging, retry
│   │   ├── local_storage/       # Offline queue, encrypted storage
│   │   │   ├── offline_queue.dart
│   │   │   └── secure_storage.dart (flutter_secure_storage)
│   │   ├── sync/                # Offline sync manager
│   │   │   ├── sync_manager.dart
│   │   │   └── conflict_resolver.dart
│   │   ├── encryption/          # Local encryption utilities
│   │   └── constants/           # App constants, error codes
│   └── shared/
│       ├── models/              # Shared DTOs
│       ├── providers/           # Dependency injection (Riverpod/GetIt)
│       └── utils/               # Utilities (formatters, validators)
├── test/
│   ├── unit/                    # Unit tests
│   ├── widget/                  # Widget tests
│   └── integration/             # Integration tests (integration_test/)
├── android/
│   └── app/build.gradle         # Android-specific configs
├── ios/
│   └── Podfile                  # CocoaPods dependencies
└── README.md
````

**Structure Decision**: Modular monolith backend (Go) with 9 domain packages supports clear separation of concerns and independent testing. Flutter mobile app uses clean architecture (presentation/domain/data layers) with feature-first organization. SQLite for local persistence; encrypted storage for credentials. Vault service isolated for PII encryption compliance. Postgres with RLS enforces data isolation at database level.

## Complexity Tracking

No constitution violations. Design aligns with all principles:

- **Modular monolith**: Clear domain boundaries enable testing and low coupling. Simpler than microservices without sacrificing maintainability.
- **Vault service isolation**: PII encryption separated from main backend. Compliance requirement (isolation) justified by security/regulatory need.
- **Append-only ledger**: Immutable audit trail required for financial compliance (DORA, PSD3). No alternative provides same guarantees.
- **Postgres RLS**: Defense-in-depth data isolation. Overhead negligible for MVP scale (<100k users).

## Design Decisions & Rationale

### Modular Monolith Architecture

**Decision**: Single Go codebase with 9 domain packages (identity, permission, consent, ingestion, matching, ledger, categorisation, insights, vault) rather than microservices.

**Why**:

- Avoids distributed transaction complexity for financial operations
- Simpler deployment (single service for MVP)
- Clear boundaries between domains while maintaining single codebase
- GoCardless + Salt Edge aggregators tested independently

**Tradeoff**: Less horizontal scalability than microservices, but Postgres connection pooling + read replicas + caching address MVP needs.

### Separate Vault Service

**Decision**: Isolated service for PII encryption with per-user Data Encryption Keys (DEKs).

**Why**:

- Compliance: GDPR requires data minimization; vault only stores encrypted data
- Security: Credential theft limited to vault instance
- Auditability: All decryption logged with user consent checks

**Implementation**: Sidecar service (same process on Linux, container in K8s) with gRPC interface. Main backend never handles unencrypted PII.

### Append-Only Ledger

**Decision**: Event-sourced financial ledger (double-entry accounting, no UPDATEs, only INSERTs).

**Why**:

- Financial compliance: Immutable audit trail required (DORA, PSD3)
- Prevents balance errors: Double-entry guarantees debits = credits
- Sole writer: Only ledger service writes transactions; reduces concurrency bugs

**Implementation**: Events table, reconciliation service verifies balance.

### TransactionObserved Canonical Model

**Decision**: Normalize GoCardless + Salt Edge responses to canonical `TransactionObserved` model before matching/ledger.

**Why**:

- Reduces coupling: Matching and ledger don't depend on API schemas
- Easier testing: Mock canonical model instead of mocking each API
- Future-proof: Adding third aggregator only requires new adapter

### Postgres RLS for Data Isolation

**Decision**: Row-level security policies enforce user data isolation at database level.

**Why**:

- Defense in depth: Even if auth bypassed, data is isolated
- No application logic needed for tenant isolation
- Compliance: PSD2 explicitly requires segregation

**Tradeoff**: Minimal performance overhead for MVP (<100k users).
