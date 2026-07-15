# Quickstart: Personal Finance Tracking System

**Purpose**: Validate the Personal Finance Tracking System end-to-end

**Status**: Phase 1 Design (Ready for Implementation)

---

## Prerequisites

Before running validation scenarios, ensure:

1. **Backend Running**:
   ```bash
   cd backend
   docker-compose up -d  # Postgres, Redis (if using)
   go run ./cmd/server/main.go
   ```
   Backend listens on `http://localhost:8080`

2. **Database Migrated**:
   ```bash
   go run ./cmd/migration/main.go up
   ```
   Creates all tables with RLS policies, indexes, and initial data

3. **Mobile App Built & Running**:
   - iOS: Run in simulator via Xcode
   - Android: Run in emulator via Android Studio
   - App configured to call `http://localhost:8080` (or exposed IP for device testing)

4. **Test Bank API Credentials** (mock/sandbox):
   - GoCardless: Sandbox credentials from dashboard
   - Salt Edge: Sandbox test account with demo transactions
   - Both available in local environment variable `.env.test`

5. **Network Isolation** (for offline testing):
   - Emulator/simulator network can be toggled offline
   - Or test with airplane mode on device

---

## Core Feature Validation Scenarios

### Scenario 1: Manual Transaction Entry (Offline)

**Goal**: Verify users can add transactions without internet and persist them locally

**Steps**:

1. **App Launch**
   - Launch mobile app
   - Register account: email `test@example.com`, password `TestPassword123!`
   - Verify user created in backend: `SELECT * FROM users WHERE email = 'test@example.com'`

2. **Create Account**
   - In app, create account: name "My Checking", type "debit_card", currency "GBP"
   - Verify in backend: `SELECT * FROM accounts WHERE user_id = ? AND name = 'My Checking'`

3. **Add Transaction (Online)**
   - Add transaction: amount 50.00, type "expense", description "Coffee", category "Food & Dining", posted_date today
   - Verify in app: Transaction appears in list
   - Verify in backend: `SELECT * FROM transactions WHERE user_id = ? AND description = 'Coffee'`

4. **Go Offline** (toggle network or airplane mode)

5. **Add More Transactions (Offline)**
   - Add 3 more transactions while offline
   - Verify in app: All 4 transactions visible in list (local storage)
   - Verify UI: Offline indicator shows (⚠️ offline or similar)

6. **Close & Reopen App (Still Offline)**
   - Force close app (kill process or swipe away)
   - Reopen app
   - Verify: All 4 transactions still visible (persisted to local DB)

7. **Reconnect to Network**
   - Re-enable network
   - Observe sync status: "Syncing..." → "Synced"
   - Wait for sync to complete (should be <5 seconds)

8. **Verify Server State**
   - Check backend database: All 4 transactions now in server DB
   - `SELECT COUNT(*) FROM transactions WHERE user_id = ?` should return 4
   - Verify balance updated: `SELECT balance FROM accounts WHERE id = ?` (should reflect all transactions)

**Expected Outcome**: ✅ All transactions persist offline and sync to server without data loss

---

### Scenario 2: Bank API Integration (GoCardless)

**Goal**: Verify bank connection, transaction retrieval, and API source marking

**Prerequisites**: Bank connection must work; use sandbox GoCardless account

**Steps**:

1. **Initiate Bank Connection**
   - In app, go to Settings → Bank Connections
   - Tap "Connect Bank"
   - Select "GoCardless"
   - Verify: Redirected to GoCardless OAuth login (sandbox)

2. **Authorize Connection**
   - In OAuth screen, authorize access to account data
   - Grant permissions: `ReadAccountsBasic`, `ReadTransactions`
   - Verify: Redirected back to app

3. **Link to Account**
   - App should match GoCardless account to existing "My Checking" account (if amount matches)
   - Or create new account: "My Bank Checking (via GoCardless)"
   - Verify in backend: `SELECT * FROM bank_api_connections WHERE user_id = ?`
   - Verify: `sync_status = 'active'`

4. **Trigger Sync**
   - Tap "Sync Now" button
   - Observe progress: "Syncing... 23/100 transactions"
   - Wait for completion (should be <30 seconds for 100 transactions)

5. **Verify Transactions Retrieved**
   - In app, view transaction list
   - See transactions marked with "GoCardless" source badge
   - Example: "[💳 GoCardless] Starbucks £5.00"
   - Verify in backend: `SELECT COUNT(*) FROM transactions WHERE user_id = ? AND source = 'gocardless'`

6. **Check Transaction Details**
   - Tap on a GoCardless transaction
   - Verify: Shows source, description from API, posted_date from API
   - Verify: Cannot edit or delete (API-sourced transactions immutable)

7. **Verify Balance Updated**
   - Dashboard should show account balance reflecting both manual + API transactions
   - Manual: 4 × transactions
   - API: N transactions from GoCardless
   - Total balance = sum of all

**Expected Outcome**: ✅ Bank integration works; transactions retrieved, marked, and balance accurate

---

### Scenario 3: Transaction Matching & Deduplication

**Goal**: Verify system detects potential duplicate transactions and allows user confirmation

**Steps**:

1. **Create Scenario**
   - Manually add transaction: £50.00, description "Sainsburys", category "Groceries", date July 15
   - Verify in app: Transaction created

2. **Sync Bank API**
   - Manually trigger bank sync
   - Bank API returns transaction: £50.00, description "Sainsburys plc", date July 15 (from GoCardless)

3. **Observe Pending Match**
   - In app, go to "Matches" or "Review" section
   - See: "Possible Match Found" with confidence score (should be high, e.g., 95%)
   - Shows both sides: manual vs API transaction

4. **Review Match Details**
   - Tap match to see:
     - Amount delta: £0 (exact match)
     - Date delta: 0 days (same day)
     - Description similarity: 98% (nearly identical)
     - Confidence score: 95%

5. **Confirm Match**
   - Tap "Yes, this is the same transaction"
   - Observe: Status changes to "Confirmed" ✅
   - Verify in backend: `SELECT * FROM transaction_matches WHERE status = 'confirmed'`

6. **Verify No Double-Counting**
   - Dashboard balance: Should reflect only ONE transaction, not both
   - Expected: 4 manual + N API - 1 (matched) = total
   - Verify in backend: Ledger has single posting for matched pair
   - `SELECT * FROM ledger_events WHERE transaction_match_id = ?`

7. **Verify Transaction Marked as Matched**
   - In transaction list, find the matched transaction
   - Verify: Shows "Matched to [API source]" badge
   - Verify: Both transactions linked (tapping one shows the other)

**Expected Outcome**: ✅ Matching works; prevents double-counting; maintains data integrity

---

### Scenario 4: Multi-Account Management

**Goal**: Verify support for multiple account types with accurate balance tracking

**Steps**:

1. **Create Multiple Accounts**
   - Account 1: "Credit Card" (credit_card type, credit_limit 5000)
   - Account 2: "Savings" (savings type, interest_rate 0.5%)
   - Account 3: "Cash Envelope" (cash type)
   - Verify in app: All 3 shown in dashboard with type icons

2. **Add Transactions to Each**
   - Account 1: Expense £100, income (payment) £500
   - Account 2: Income £1000 (interest)
   - Account 3: Expense £50

3. **Verify Per-Account Balances**
   - Account 1 (Credit Card): Shows balance and available credit
     - Available credit = limit - balance = 5000 - 100 + 500 = 5400
   - Account 2 (Savings): Shows balance and interest rate
   - Account 3 (Cash): Shows balance

4. **Filter Transactions**
   - In transaction list, filter by Account 1
   - Should see only 2 transactions (expense + income)
   - Switch filters, verify isolation works

5. **Transfer Between Accounts**
   - Transfer £200 from Savings to Cash
   - Verify: Savings balance decreases by 200
   - Verify: Cash balance increases by 200
   - Verify in backend: Transfer creates two ledger postings (debit Savings, credit Cash)

6. **Archive Account**
   - Archive Account 3 (Cash)
   - Verify: Account moves to "Archived" view
   - Verify: Transactions still visible (read-only)
   - Verify: Cannot add new transactions to archived account

**Expected Outcome**: ✅ Multi-account support works; balances accurate; isolation maintained

---

### Scenario 5: Offline Sync & Conflict Resolution

**Goal**: Verify pending changes sync when network restored; conflicts handled gracefully

**Steps**:

1. **Device A: Add Offline Transactions**
   - On device/emulator A, go offline
   - Add 5 transactions
   - Verify: All visible in app (local), offline indicator shown

2. **Device B: Separate Session**
   - On second device/emulator B, login same account
   - Verify: Device B shows no pending offline transactions (different local DB)
   - Add 3 transactions on Device B (online)
   - Sync completes; transactions visible

3. **Device A: Reconnect Network**
   - Re-enable network on Device A
   - Observe: Auto-sync starts
   - Status: "Syncing..." → "Synced"

4. **Verify Consistency**
   - Device A: Refresh/reload
   - Should see: 5 (local) + 3 (from Device B) = 8 transactions total
   - All transactions unified in list
   - No data loss

5. **Test Conflict Scenario** (optional, if concurrent edits possible)
   - Device A: Edit transaction (local, but sync not started yet)
   - Device B: Edit SAME transaction (different field)
   - Device A: Go online
   - Verify: Conflict detected, user prompted to resolve
   - Verify: UI shows both versions, allows user to choose or merge

**Expected Outcome**: ✅ Offline sync works; conflicts handled; eventual consistency achieved

---

### Scenario 6: Compliance & Security Validation

**Goal**: Verify security measures are in place and working

**Steps**:

1. **Authentication Validation**
   - Attempt login with wrong password
   - Verify: Attempt count incremented
   - After 5 failed attempts: Locked out with "Try again in 15 minutes"
   - Verify in backend: Rate limiting enforced

2. **Session Management**
   - Login successfully
   - Verify: Access token in Authorization header for subsequent requests
   - Wait for token to expire (or trigger manually)
   - Verify: Next request fails with 401 Unauthorized
   - Use refresh token to get new access token
   - Verify: Can continue using app

3. **Data Isolation (RLS)**
   - Create User A (test@a.com), User B (test@b.com)
   - User A: Create account with transaction
   - User B: Login, verify cannot see User A's data
   - Verify in backend: SQL injection attempt `SELECT * FROM transactions WHERE user_id = ? OR 1=1` returns only current user's data (RLS policy enforced)

4. **Sensitive Data Handling**
   - Add transaction with sensitive description (e.g., "Psychiatrist visit £100")
   - Check backend logs: Verify transaction is NOT logged in plaintext
   - Check error responses: Verify no account numbers or PII exposed
   - Verify: Logs only contain `user_id`, `amount`, category (no sensitive details)

5. **Encryption Verification**
   - Bank API credentials stored in vault service
   - Verify: Credentials never appear in application logs
   - Verify: Credentials encrypted before storage
   - Attempt to read from DB directly: `SELECT encrypted_credentials FROM bank_api_connections` should be gibberish (encrypted)

6. **Audit Trail**
   - Perform sensitive operation (e.g., connect bank, confirm match)
   - Check audit logs: `SELECT * FROM ledger_events ORDER BY sequence_number DESC`
   - Verify: Event recorded with timestamp, user, operation type
   - Verify: Ledger is append-only (no UPDATE/DELETE on events)

7. **Consent & Permissions**
   - Check consent table: User has GDPR consent for account management
   - Check permission table: PSD2 permission expires in 90 days
   - Verify: UI reminds user when permission about to expire
   - Revoke permission: Verify immediate effect (cannot sync until re-authorized)

**Expected Outcome**: ✅ Security measures enforced; sensitive data protected; audit trail intact

---

## Validation Checklists

### Backend Implementation Readiness

- [ ] All 9 domain packages (identity, permission, consent, ingestion, matching, ledger, categorisation, insights, vault) compiling without errors
- [ ] Database migrations running successfully with RLS policies applied
- [ ] All 39 functional requirements mapped to at least one endpoint or background job
- [ ] Unit tests passing for core logic (matching, ledger, balance calc) with ≥85% coverage
- [ ] Integration tests passing with testcontainers (Postgres in Docker)
- [ ] Contract tests validating mobile ↔ backend API compatibility
- [ ] Performance tests showing <500ms p95 latency for transaction queries with 100k+ test records
- [ ] Security review completed: Auth (passkeys+JWT), encryption, OWASP Top 10
- [ ] GDPR compliance: Data export/deletion endpoints functional
- [ ] PSD2 compliance: Permission state machine enforces 90-day expiry

### Mobile App Implementation Readiness

- [ ] Manual transaction entry screen functional and validated
- [ ] Local database (Realm/SQLite) persisting transactions offline
- [ ] Network state detection (online/offline indicators) working
- [ ] Offline queue implemented for pending changes
- [ ] Sync manager successfully uploading queued changes when online
- [ ] Transaction list displaying both manual and API transactions
- [ ] Transaction matching UI showing pending matches with confidence scores
- [ ] Bank API integration screen allowing GoCardless/Salt Edge connection
- [ ] Account management (create, edit, archive) functional
- [ ] Dashboard showing aggregate balance across all accounts
- [ ] Error handling and retry logic for failed API calls
- [ ] Accessibility: WCAG 2.1 AA compliance for key screens (manual testing)

### System Integration Readiness

- [ ] End-to-end scenario: offline transaction entry → sync → server persistence
- [ ] End-to-end scenario: bank API sync → transaction retrieval → matching
- [ ] Multi-device sync: Changes on Device A visible on Device B within 30 seconds
- [ ] Conflict resolution: Concurrent edits handled gracefully
- [ ] Performance: Dashboard loads in <2s on 4G network
- [ ] Reliability: Sync survives brief network interruptions (retry logic)
- [ ] Compliance: Sensitive data never appears in logs or error messages

---

## Running Validation

### Automated Integration Tests

```bash
cd backend/tests/integration
go test -v -timeout 5m ./...
```

Expected output:
```
TestTransaction/Manual_Entry - PASS
TestTransaction/API_Retrieval - PASS
TestMatching/Fuzzy_Match - PASS
TestLedger/Double_Entry - PASS
TestOfflineSync/Pending_Changes - PASS
TestComplianceAudit/RLS_Enforcement - PASS
```

### Contract Tests

```bash
cd backend/tests/contract
go test -v ./... -run Pact
```

Validates mobile ↔ backend API requests/responses against contract.

### Manual Device Testing

Device testing (not automated) for:
- Offline transaction entry and persistence
- Bank API OAuth flow
- Network transition scenarios (online → offline → online)
- UI responsiveness and error messaging
- Accessibility (screen reader testing)

---

## Success Criteria

Feature is ready for implementation when:

1. ✅ All 6 validation scenarios pass (manual + API transactions sync, matching works, multi-account isolated, offline resilient, compliance enforced)
2. ✅ Data model fully normalized and validated (zero N+1 queries, RLS enforced, indexes optimized)
3. ✅ API contract frozen (no breaking changes to mobile ↔ backend interface)
4. ✅ Backend code passes linting (golangci-lint), unit tests (≥85% coverage), and integration tests
5. ✅ Mobile code follows platform conventions and passes accessibility checks
6. ✅ Security review completed and signed off (no critical findings)
7. ✅ Compliance audit passed (GDPR, PSD2, DORA, PCI-DSS applicable requirements met)
8. ✅ Performance benchmarks met (<500ms API latency, <2s mobile load time)

---

## Troubleshooting Common Issues

### Transaction Not Syncing
- Check: Is device online? (WiFi/cellular)
- Check: Is token expired? (Re-login)
- Check: Backend running and accessible? (`curl http://localhost:8080/health`)
- Check: Database migrations applied? (`SELECT * FROM transactions`)

### Bank API Connection Fails
- Check: Sandbox credentials correct? (Check `.env.test`)
- Check: OAuth callback URL configured? (Must match app's registered scheme)
- Check: Network accessible to sandbox API? (Try `curl` to GoCardless endpoint)

### Matching Not Detecting Duplicates
- Check: Amounts match exactly? (Algorithm requires ≤10% delta)
- Check: Dates within ±1 day? (Algorithm checks date delta)
- Check: Description similar? (Algorithm uses Levenshtein distance)
- Check: Backend matching service running? (Check logs for matching messages)

### RLS Preventing Data Access
- Check: JWT token contains correct `user_id` claim?
- Check: Postgres session variable set correctly in middleware?
- Check: RLS policy syntax correct? (Check `.sql` migration files)
