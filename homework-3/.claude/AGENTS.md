# Agent Guidelines for Personal Finance Tracking System

**Project**: Homework 3 - Personal Finance Tracking System  
**Last Updated**: 2026-07-15

This document defines standards, constraints, and expectations for all agents (AI or human) working on this project.

---

## 1. Project Overview

**What we're building**: A personal finance tracking system with:

- Offline-first Flutter mobile app (iOS 14+, Android 11+)
- Go backend with modular monolith architecture
- Bank API integration (GoCardless + Salt Edge)
- Transaction matching and deduplication
- Full EU/UK regulatory compliance (GDPR, PSD2/PSD3, DORA, PCI-DSS)

**Key characteristics**:

- **Financial domain** — data is sensitive; security and accuracy are non-negotiable
- **Multi-source data** — manual transactions + bank APIs → must deduplicate cleanly
- **Offline-first** — mobile works without internet; sync when connected
- **High compliance bar** — audit trails, encryption, data minimization required
- **99% uptime** — not "best effort"; architectural constraint

---

## 2. Tech Stack (Mandatory)

### Backend

- **Language**: Go 1.21+ (strictly enforced)
- **Framework**: Echo or chi HTTP framework
- **Database**: PostgreSQL 16 with Row-Level Security (RLS)
- **Query builder**: sqlc (type-safe, no ORMs)
- **Authentication**: Passkeys (Webauthn), JWT tokens, session management
- **Bank APIs**: GoCardless SDK (primary) + Salt Edge SDK (secondary)
- **Encryption**: TLS 1.3 (transit), AES-256 (at-rest), per-user DEKs via Cloud KMS
- **Observability**: OpenTelemetry (logging, metrics, distributed tracing)
- **Testing**: testify (unit), testcontainers (integration), pact-go (contract)
- **Vault service**: Separate service for PII encryption (gRPC interface)

### Mobile

- **Framework**: Flutter 3.13+ with Dart 3.1+ (cross-platform iOS + Android)
- **Local Database**: SQLite via sqflite or drift ORM
- **Encrypted Storage**: flutter_secure_storage (for API credentials)
- **HTTP Client**: dio or http package (with interceptors for auth/retry)
- **Biometrics**: local_auth package
- **Network State**: connectivity_plus package
- **State Management**: Riverpod or GetIt (not Redux/BLoC)
- **UI Design**: Material 3 (default) + platform-aware widgets (Cupertino for iOS)
- **Testing**: flutter_test (unit), integration_test (E2E), Patrol (UI)

### Infrastructure

- **Containerization**: Docker (backend)
- **Orchestration**: Kubernetes (optional; may use managed services)
- **Key Management**: Cloud KMS (AWS KMS or Azure Key Vault)
- **CI/CD**: GitHub Actions (linting, testing, type checking)

**❌ DO NOT USE**:

- Node.js, Python, Rust, C#, Java, Ruby, PHP
- Firebase, Supabase, MongoDB, DynamoDB
- Redux, BLoC, MVI, MVP (on Flutter)
- Hardcoded credentials, environment variables for secrets
- Custom encryption implementations
- ORMs (sqlc replaces them)

---

## 3. Domain Rules (Mandatory)

### Financial Domain

1. **Transactions are immutable** once matched (no edits after user confirms match)
2. **Balances derived from ledger** — never store balance in transaction; always calculate from sum
3. **Double-entry accounting** — every transaction creates debit + credit posting in ledger
4. **Account types matter** — credit cards ≠ debit cards ≠ savings ≠ cash (different metadata)
5. **Amounts always positive** — sign determined by `type` (income/expense/transfer), not amount field
6. **Multi-currency support**:
   - Store original currency amount
   - Convert to primary currency using exchange rate at transaction time
   - Allow user to manually specify amounts in different currencies
   - Never round during conversion; use decimal128 precision

### Offline-First Principles

1. **All reads come from local DB first** — never require network for viewing data
2. **Writes queue locally** — persist immediately to SQLite, sync when online
3. **Sync is eventually consistent** — acceptable to take minutes; not real-time
4. **Conflicts resolved by user** — if Device A and B edit same transaction, present both versions
5. **No data loss on crash** — transaction-specific edits must be atomic

### Security & Compliance Domain

1. **PII isolation** — account numbers, SSNs, names always encrypted in vault service
2. **Audit everything** — log all auth, API calls, data access, config changes (7-year retention)
3. **Never log sensitive data** — no amounts, account numbers, API tokens in plaintext logs
4. **Data minimization** — collect only what's necessary; delete old data after retention period
5. **User consent tracking** — GDPR lawful basis must be documented per operation type
6. **Permission expiry** — PSD2 permissions auto-expire after 90 days
7. **Rate limiting** — 5 failed auth attempts → 15-min lockout
8. **OWASP Top 10** — input validation, CSRF tokens, secure session management, dependency scanning

---

## 4. Code Style & Conventions

### Go Backend

**Naming**:

```go
// ✅ GOOD
var userID, transactionAmount, bankAPICredential string
func calculateBalance(ctx context.Context, accountID string) (decimal.Decimal, error) {}
type TransactionObserved struct {}

// ❌ BAD
var uid, amt, cred string
var x int
func calc() {}
```

**Structure**:

- Package per domain: `pkg/identity/`, `pkg/ledger/`, `pkg/matching/`, etc.
- Layered: domain models → services → HTTP handlers → storage repos
- Interfaces in domain layer; implementations in `internal/postgres/`
- Error handling: wrap errors with context, never silent fails
- Logging: use structured logger with context (user_id, request_id, operation)

**Linting**:

```bash
golangci-lint run --deadline 5m
# MUST pass with zero errors/warnings before commit
# No `nolint` directives without justification
```

**Comments**:

```go
// ✅ GOOD - explains WHY and documents important behavior
// Ledger is append-only; no UPDATEs allowed to preserve audit trail.
// Balance derived from sum of ledger postings, never stored in transaction row.
func (r *PostgresLedgerRepo) InsertEvent(ctx context.Context, evt *LedgerEvent) error {}

// ❌ BAD - obvious from code, adds noise
// Create a new user
func CreateUser(ctx context.Context, u *User) error {}
```

**Testing**:

```go
// Table-driven tests preferred
func TestTransactionValidation(t *testing.T) {
	tests := []struct {
		name      string
		amount    decimal.Decimal
		wantErr   bool
	}{
		{"valid", decimal.New(99, 2), false},
		{"negative", decimal.New(-10, 2), true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// ...
		})
	}
}
```

### Flutter/Dart Mobile

**Naming** (Dart conventions):

```dart
// ✅ GOOD
class TransactionEntryScreen extends StatefulWidget {}
final userRepository = UserRepository();
void _buildTransactionForm() {}

// ❌ BAD
class transactionEntryScreen {}
final user_repo = UserRepository();
void buildTransactionForm() {}  // private without leading _
```

**Structure**:

- Clean architecture: `presentation/` (UI) → `domain/` (business logic) → `data/` (repos)
- Feature-first: `features/transaction/`, `features/account/`, `features/bank_sync/`
- Separate models: entity (domain), DTO (API response), UI model (presentation state)
- Use `const` constructors where possible (performance)

**UI**:

```dart
// ✅ GOOD - Material 3, platform-aware
Widget build(BuildContext context) {
  return Material(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(children: [...]),
    ),
  );
}

// ❌ BAD - hardcoded values, not responsive
child: Padding(
  padding: EdgeInsets.all(16),  // should be const
  child: Container(width: 300, ...)  // not responsive
)
```

**Testing**:

```dart
// Widget tests verify UI behavior
testWidgets('Transaction entry form validates amount', (tester) async {
  await tester.pumpWidget(MyApp());
  await tester.enterText(find.byType(TextField), '-50.00');
  await tester.tap(find.byType(SubmitButton));
  expect(find.byType(ErrorText), findsOneWidget);
});
```

---

## 5. Testing & Verification Expectations

### Mandatory Coverage Targets

- **Backend**: ≥85% code coverage for core logic (matching, ledger, balance calc)
- **Mobile**: ≥80% code coverage for core logic (repositories, usecases, services)
- **UI**: Widget tests for all critical screens, integration tests for user flows

### Test Types Required

**Backend**:

1. **Unit tests** (testify): All domain logic, repositories, services
2. **Integration tests** (testcontainers): Database interactions, API endpoints, end-to-end flows
3. **Contract tests** (pact-go): Mobile ↔ Backend API compatibility
4. **Security tests**: Auth bypass attempts, SQL injection, rate limiting

**Mobile**:

1. **Unit tests** (flutter_test + mockito): Models, repositories, usecases
2. **Widget tests**: All screens and forms (UI logic, validation, error states)
3. **Integration tests** (integration_test): User flows (transaction entry → persist → display)
4. **UI tests** (Patrol): Critical user journeys on real devices

### Verification Checklist Before Merge

- [ ] Linting passes: `golangci-lint` (backend), `dart analyze` (mobile)
- [ ] Type checking passes: no type errors in `go vet` or Dart analyzer
- [ ] Tests pass locally: all unit, integration, contract tests
- [ ] CI passes: GitHub Actions linting, testing, type checking
- [ ] Coverage verified: ≥85% (backend core), ≥80% (mobile core)
- [ ] Performance verified: No regressions in latency (use profiling tools)
- [ ] Security review: Auth, credential storage, API validation verified
- [ ] No sensitive data in logs: grep for patterns (phone, ssn, account_number, amount)

---

## 6. Security & Compliance Constraints

### Encryption (Non-Negotiable)

- **In transit**: TLS 1.3 only (no TLS 1.2, no HTTP)
- **At rest**: AES-256 via Cloud KMS or managed vault
- **Per-user keys**: Each user gets unique Data Encryption Key (DEK), encrypted with KMS master key
- **Credentials**: Always encrypted in `flutter_secure_storage` (mobile) or vault (backend)
- **No hardcoded keys**: All keys sourced from environment or KMS

### Authentication & Authorization

- **Auth methods**: Passkeys (Webauthn) OR biometric + local encryption (mobile)
- **Session tokens**: JWT with 30-day expiry, refresh tokens must rotate
- **Multi-device**: Permit same user on multiple devices; sync eventually consistent
- **Rate limiting**: Max 5 failed auth attempts per IP → 15-min lockout
- **Passwords** (if used): Minimum 8 chars with complexity; hashed with Argon2

### Data Handling

- **PII fields**: Account numbers, SSNs, names ALWAYS encrypted in vault
- **Financial data**: Transaction amounts encrypted at rest, decrypted only on authorized access
- **Audit logs**: Immutable, tamper-proof, 7-year retention minimum
- **GDPR right-to-be-forgotten**: Data deleted within 30 days of user request
- **Data minimization**: Collect only necessary fields; delete old data per retention policy
- **User consent**: Track GDPR lawful basis (consent, contract, legal obligation) separately

### Compliance Requirements

1. **GDPR** (EU):
   - Data export endpoints (CSV, JSON)
   - Deletion endpoint (right-to-be-forgotten)
   - Privacy policy integration
   - DPA with processors (if using third-party services)

2. **UK Data Protection Act 2018** (post-Brexit):
   - Equivalent to GDPR; parallel implementation

3. **PSD2 / Open Banking** (EU/UK):
   - Strong Customer Authentication (SCA) for sensitive operations
   - 90-day consent expiry enforcement
   - Secure credential handling
   - Compliance with Open Banking standards

4. **PSD3** (upcoming):
   - Designed to be PSD3-ready from day one
   - Same principles as PSD2; stricter requirements

5. **DORA** (Digital Operational Resilience Act):
   - Observability / monitoring (logging, metrics, alerting)
   - 99% uptime SLA (max ~7.2 hours downtime/month)
   - Incident reporting procedures

6. **PCI-DSS** (if handling payment cards):
   - Vault service stores credentials, not main backend
   - No card numbers in logs or error messages
   - Encrypted transmission only

### Security Review Checklist

- [ ] OWASP Top 10 mitigations verified (SQL injection, XSS, CSRF, rate limiting, etc.)
- [ ] Input validation on all user inputs (amounts, dates, descriptions)
- [ ] Sensitive data never logged (grep for account_number, amount, token patterns)
- [ ] Encryption verified (TLS 1.3, AES-256, per-user DEKs)
- [ ] Auth/rate limiting verified (5 attempts, 15-min lockout)
- [ ] Audit logs tested (all sensitive operations logged)
- [ ] GDPR/PSD2 compliance verified (consent tracking, permission expiry)

---

## 7. Edge Cases & Error Handling

### Transaction Edge Cases

| Scenario                              | Behavior                                                                                        |
| ------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Future date (>1 year)                 | Reject with validation error; document in spec                                                  |
| Past date (>10 years)                 | Allow (historical records); note assumption in spec                                             |
| Zero amount                           | Reject; amounts must be >0                                                                      |
| Negative amount                       | Reject; sign handled by `type` field                                                            |
| Duplicate manual + API transaction    | Fuzzy match algorithm (±10% amount, ±1 day date, description similarity); user confirms/rejects |
| API sync mid-crash                    | Sync queue persists locally; resumes on app restart                                             |
| Concurrent edit (Device A + Device B) | Conflict resolver presents both versions; user chooses                                          |
| Offline for weeks                     | Sync batches changes; may take minutes; no data loss                                            |
| API rate limit hit                    | Graceful error message, automatic retry with backoff                                            |

### Account Edge Cases

| Scenario                         | Behavior                                                       |
| -------------------------------- | -------------------------------------------------------------- |
| Create duplicate account names   | Reject; account name unique per user                           |
| Delete account with transactions | Soft-delete (archive); transactions remain visible (read-only) |
| No accounts exist                | Show onboarding flow; require user to create account first     |
| Credit card with zero limit      | Allow; assume unlimited (user error); log as warning           |
| Transfer between accounts        | Out of scope for MVP; deferred to Phase 9                      |

### Bank API Edge Cases

| Scenario                                    | Behavior                                                               |
| ------------------------------------------- | ---------------------------------------------------------------------- |
| API returns 1000+ transactions              | Paginate/batch; show progress; complete in <30s                        |
| API returns duplicate of manual transaction | Fuzzy matching detects; user decides                                   |
| API credentials invalid/expired             | Show error; offer re-auth flow; keep existing transactions             |
| API server down                             | Graceful error; show offline mode warning; allow manual entry          |
| Partial sync failure                        | Don't apply partial results; retry full sync on next network reconnect |

### Sync Edge Cases

| Scenario                                                   | Behavior                                                                |
| ---------------------------------------------------------- | ----------------------------------------------------------------------- |
| Network drops mid-sync                                     | Local queue persists; sync resumes when online                          |
| User adds transaction during sync                          | Queue it; process after current sync completes                          |
| Backend has newer version (Device B synced after Device A) | Conflict detected; present both versions to user                        |
| Sync takes >5 minutes                                      | Show timeout error; allow user to retry manually                        |
| Local and backend diverged significantly                   | Reconciliation task identifies discrepancy; log as alert; user notified |

### Error Messages (User-Friendly, Never Technical)

```
❌ BAD:
"NullPointerException in TransactionRepository.getTransaction()"
"SQLSTATE 23505 - unique_constraint_violation"

✅ GOOD:
"We're having trouble saving your transaction. Please check your internet connection and try again."
"Account name already exists. Please choose a different name."
"We couldn't connect to your bank. Your account may be locked; please try again in 15 minutes."
```

---

## 8. Performance Expectations

### Latency Targets (Non-Negotiable)

| Operation                         | Target     | Measurement                           |
| --------------------------------- | ---------- | ------------------------------------- |
| API transaction list              | <500ms p95 | Backend latency (no network included) |
| Mobile transaction list load      | <500ms     | User perceives result loaded          |
| Mobile app cold start             | <2s        | App launch → dashboard visible        |
| Balance calculation               | <100ms     | SQLite query for account balance      |
| Bank sync (1000 transactions)     | <30s       | End-to-end, including network         |
| Matching 10k pending transactions | <1s        | Fuzzy match algorithm runtime         |
| Auth (password)                   | <2s        | Backend processing                    |
| Auth (biometric)                  | <1s        | Local on-device processing            |

### Profiling & Optimization

- **Backend**: Profile with pprof; identify >100ms queries; add indexes
- **Mobile**: Profile with Flutter DevTools; measure frame times; target 60 FPS
- **Database**: Indexes on `user_id`, `posted_date`, `account_id` mandatory
- **Caching**: Redis optional; use for read-heavy queries (dashboard, trends)
- **Batch operations**: Bank sync must batch API calls (not 1000 individual requests)

### Measurement Tools

- **Backend**: `go test -bench`, pprof, OpenTelemetry metrics
- **Mobile**: Flutter DevTools, Dart analyzer `--report-metrics`
- **Database**: PostgreSQL `EXPLAIN ANALYZE`, slow query logs
- **Production**: OpenTelemetry dashboards, Datadog/Prometheus metrics

---

## 9. Implementation Workflow

### Before Starting Any Task

1. **Read the spec**: `specs/001-finance-tracker/spec.md` (requirements, acceptance criteria)
2. **Read the plan**: `specs/001-finance-tracker/plan.md` (architecture, design decisions)
3. **Read the data model**: `specs/001-finance-tracker/data-model.md` (entities, relationships)
4. **Read the API contract**: `specs/001-finance-tracker/contracts/backend-mobile-api.md` (request/response)

### During Implementation

1. **Write tests first** (TDD preferred): Unit test FAILS before implementation
2. **Implement domain logic**: Business logic in `pkg/domain/` (backend) or `domain/` (mobile)
3. **Implement storage**: Repositories in `internal/postgres/` (backend) or DAOs (mobile)
4. **Implement endpoints**: HTTP handlers in `pkg/http/` (backend) or UI screens (mobile)
5. **Verify coverage**: ≥85% backend core, ≥80% mobile core
6. **Verify performance**: Measure before/after; no unexplained regressions
7. **Security review**: Check logs, encryption, auth, input validation

### Before Submitting PR

1. Lint passes: `golangci-lint` or `dart analyze`
2. Tests pass locally: `go test ./...` or `flutter test`
3. Type checking: no errors in `go vet` or Dart analyzer
4. Performance verified: no regressions vs. baseline
5. Security review: no sensitive data logged
6. PR description includes:
   - Which requirement(s) this addresses (FR-###, SC-###)
   - Design decisions made
   - Testing approach
   - Compliance checklist items verified

---

## 10. Communication & Escalation

### When Stuck

1. **Check the spec** — clarifications section has prior decisions
2. **Check the plan** — architecture diagrams and design decisions documented
3. **Check the tasks.md** — dependencies and ordering explained
4. **Ask questions in PR comments** — link to spec/plan/task references
5. **Escalate to team lead** if blocking on architectural decision

### Definition of "Done"

- ✅ Spec requirement(s) implemented and testable
- ✅ Tests pass (unit, integration, or UI as applicable)
- ✅ Coverage meets targets (≥85% backend, ≥80% mobile)
- ✅ Performance meets targets (latency, throughput)
- ✅ Security review passed (no sensitive data logged)
- ✅ Accessibility verified (WCAG 2.1 AA for UI)
- ✅ PR reviewed and approved
- ✅ CI passes (linting, tests, type checking)

---

## 11. Quick Reference Checklist

**Before Every Commit**:

- [ ] Linting passes (zero warnings)
- [ ] Tests pass locally
- [ ] Type checking passes
- [ ] Coverage ≥80% for changed code
- [ ] No console.log / print statements left
- [ ] No hardcoded secrets or credentials

**Before Every PR**:

- [ ] Addresses specific FR-### or SC-### requirement(s)
- [ ] Tests added (unit, integration, or UI)
- [ ] Security review: no sensitive data logged
- [ ] Performance verified: no regressions
- [ ] Accessibility verified (UI changes): WCAG 2.1 AA
- [ ] PR description links to spec/plan/tasks

**Before Marking "Ready for Implementation"**:

- [ ] Spec complete: all requirements defined
- [ ] Plan complete: architecture and design decisions documented
- [ ] Tasks complete: all work broken down into atomic, executable tasks
- [ ] Analysis complete: no critical inconsistencies or coverage gaps
- [ ] Constitution verified: all MUST principles satisfied

---

## 12. Questions? Troubleshooting

| Question                                             | Answer                                                                |
| ---------------------------------------------------- | --------------------------------------------------------------------- |
| "Can I use X library instead of Y?"                  | Check tech stack section. If not listed, ask team lead.               |
| "The latency target seems tight, how do we meet it?" | Plan includes profiling tasks; measure baseline first, then optimize. |
| "Do we really need audit logs for everything?"       | Yes — 7-year compliance requirement (DORA, GDPR).                     |
| "Can we skip the security review?"                   | No — financial data + PII + compliance regulations = mandatory.       |
| "Can I store the balance in the transaction?"        | No — always calculate from ledger sum (double-entry accounting rule). |
| "What if the user never confirms a match?"           | Show as "pending"; let them review later; no automatic matching.      |
| "How do we handle multi-user accounts?"              | Out of scope for MVP (FR-025 deferred); single-user only.             |
| "What exchange rate API should we use?"              | Deferred to Phase 9; for now, use rate at transaction time.           |

---

**Last Updated**: 2026-07-15  
**Valid Until**: Implementation complete  
**Questions**: Refer to spec.md Clarifications section or ask team lead
