# Data Model: Personal Finance Tracking System

**Purpose**: Define entities, relationships, and validation rules for the finance tracker backend

**Status**: Phase 1 Design (Ready for Implementation)

---

## Core Entities

### User

Represents an individual user of the system.

**Fields**:
- `id` (UUID, primary key): Unique user identifier
- `email` (string, unique): User's email; validated RFC 5322
- `phone` (string, optional): User's phone number for optional MFA
- `created_at` (timestamp): Account creation time
- `last_login_at` (timestamp, nullable): Last successful login
- `status` (enum): `active`, `suspended`, `deleted` (soft-delete)
- `preferences` (JSON): User settings (currency, language, timezone)
- `audit_metadata` (JSON): Compliance tracking (consent date, IP, device info)

**Relationships**:
- Has many `Account`
- Has many `Consent`
- Has many `Session`
- Has many `Transaction` (manual entries)

**Validation Rules**:
- Email: Unique, RFC 5322 compliant, verified via email link
- Password (if used): Minimum 8 chars, complexity requirements, or passkey required
- Deleted users: Retention period 30 days before permanent purge (GDPR right-to-be-forgotten)

**State Machine**:
- `active` → `suspended` (via compliance team action)
- `active` → `deleted` (via user request)
- `suspended` → `active` (via compliance team action)
- `deleted` → (permanent deletion after 30 days)

---

### Account

Represents a financial account (credit card, debit card, savings, cash).

**Fields**:
- `id` (UUID, primary key)
- `user_id` (UUID, foreign key): Account owner
- `account_type` (enum): `credit_card`, `debit_card`, `savings`, `cash`
- `name` (string): User-provided account name (e.g., "Chase Checking")
- `balance` (decimal, precision 19,4): Current balance in account currency
- `currency` (string): ISO 4217 code (e.g., "GBP", "EUR", "USD")
- `created_at` (timestamp): When account was added to app
- `archived_at` (timestamp, nullable): When account was archived
- `institution_name` (string, optional): Bank name if known
- `account_number_last4` (string, optional): Last 4 digits (encrypted in vault)
- `metadata` (JSON): Account-specific data:
  - `credit_limit` (decimal): For credit cards
  - `interest_rate` (decimal): For savings accounts
  - `icon_color` (string): UI color preference
  - `position` (integer): Display order

**Relationships**:
- Belongs to `User`
- Has many `Transaction`
- Has many `BankAPIConnection` (for API-linked accounts)
- Has many `LedgerPosting` (for balance tracking)

**Validation Rules**:
- Name: Required, max 255 chars, unique per user
- Balance: Updated only via ledger postings (read-only to application layer)
- Currency: Valid ISO 4217 code
- Credit limit: Only for credit card type
- Interest rate: Only for savings account type
- Archived accounts: Transactions remain visible but no new transactions allowed

**Constraints**:
- RLS policy: User can only access own accounts
- Only ledger service updates balance (ensures consistency)

---

### Transaction

Represents a single financial movement (manual or API-sourced).

**Fields**:
- `id` (UUID, primary key)
- `account_id` (UUID, foreign key)
- `user_id` (UUID, foreign key): Denormalized for RLS
- `amount` (decimal, precision 19,4): Absolute value; sign determined by type
- `type` (enum): `income`, `expense`, `transfer`
- `source` (enum): `manual`, `gocardless`, `saltedge`
- `source_transaction_id` (string, nullable): External API transaction ID (for matching)
- `description` (string): User-provided or from API
- `category` (string, nullable): Categorization (expense, income type)
- `matched_with` (UUID, nullable): ID of matched transaction (if part of match pair)
- `match_confidence` (decimal, nullable): 0-100 confidence score
- `posted_date` (date): When transaction occurred in real world
- `created_at` (timestamp): When record was created locally
- `updated_at` (timestamp): Last modification
- `notes` (string, optional): User notes on transaction
- `metadata` (JSON): API-specific fields, user tags, attachment references
- `is_pending` (boolean): True for provisional/unconfirmed matches

**Relationships**:
- Belongs to `Account`
- Belongs to `User`
- May be linked to `TransactionMatch`
- Creates `LedgerEvent` (via matching service)

**Validation Rules**:
- Amount: Positive, non-zero, within reasonable bounds (e.g., <1,000,000)
- Type: Required; must be `income`, `expense`, or `transfer`
- Source: Determines who created (manual, GoCardless, Salt Edge)
- Posted date: Not more than 10 years in past or 1 year in future
- Description: Max 500 chars, no control characters
- Category: Must be valid category from predefined or user-defined list
- Matched transactions: Both sides of match must be confirmed before finalization

**State Machine** (for matched transactions):
- `pending_match` → `confirmed_match` (user confirms)
- `pending_match` → `rejected_match` (user rejects)
- `confirmed_match` → (final, immutable)

---

### TransactionMatch

Represents a potential or confirmed match between manual and API transactions.

**Fields**:
- `id` (UUID, primary key)
- `manual_transaction_id` (UUID, foreign key): Manually entered transaction
- `api_transaction_id` (UUID, foreign key): API-sourced transaction
- `user_id` (UUID, foreign key): Denormalized for RLS
- `confidence_score` (decimal): 0-100 matching confidence
- `match_reason` (JSON): Matching algorithm details
  - `amount_delta`: Difference in amounts (cents)
  - `date_delta`: Days between posted dates
  - `description_similarity`: Levenshtein distance or similar metric
  - `rule_matches`: Which matching rules triggered
- `status` (enum): `pending`, `confirmed`, `rejected`
- `user_action_at` (timestamp, nullable): When user confirmed/rejected
- `user_action_ip` (string, nullable): IP address of user action (audit)
- `created_at` (timestamp)
- `metadata` (JSON): Additional context

**Relationships**:
- References two `Transaction` records
- Belongs to `User`
- May trigger `LedgerEvent` (if confirmed)

**Validation Rules**:
- Both transactions must belong to same user
- Manual transaction must have source `manual`
- API transaction must have source `gocardless` or `saltedge`
- Confidence score: 0-100 range
- Status: `pending` initially; only user can confirm/reject

**Constraints**:
- Immutable once confirmed: prevents accidental data loss
- RLS policy: User can only access own matches

---

### BankAPIConnection

Represents a user's connected bank account via GoCardless or Salt Edge.

**Fields**:
- `id` (UUID, primary key)
- `user_id` (UUID, foreign key)
- `account_id` (UUID, nullable, foreign key): Associated app account (if matched)
- `provider` (enum): `gocardless`, `saltedge`
- `provider_account_id` (string): External account ID from bank API
- `institution_id` (string): Bank identifier from API
- `permissions_granted` (JSON): List of permissions user granted
  - `scopes`: Array of PSD2 scopes (e.g., `ReadAccountsBasic`, `ReadTransactions`)
  - `expires_at`: PSD2 consent expiration (max 90 days)
- `encrypted_credentials` (string): Encrypted refresh tokens/API keys (stored in vault)
- `sync_status` (enum): `active`, `paused`, `error`, `revoked`
- `last_sync_at` (timestamp, nullable): When last sync succeeded
- `last_sync_error` (text, nullable): Error message from last failed sync
- `last_sync_transaction_count` (integer): Transactions retrieved in last sync
- `created_at` (timestamp)
- `revoked_at` (timestamp, nullable): When user revoked connection

**Relationships**:
- Belongs to `User`
- References `Account` (optional; may be matched automatically)
- Has many `TransactionObserved` (API transactions fetched)
- Relates to `Permission` (PSD2 scope tracking)

**Validation Rules**:
- Provider: Must be valid API provider
- Credentials: Encrypted via vault service; never decrypted outside vault
- Permissions: Must match scopes granted by user
- Consent expiry: Automatically tracked; alerts before expiry
- Last sync error: Cleared on successful sync

**State Machine**:
- `active` → `paused` (user pause)
- `active` → `revoked` (user revoke)
- `active` → `error` (sync failure)
- `error` → `active` (retry succeeds)
- `paused`/`error` → `active` (user resumes)
- `revoked` → (no reactivation; requires new connection)

---

### LedgerEvent

Represents an immutable financial event (append-only log).

**Fields**:
- `sequence_number` (bigint, primary key): Immutable global ordering
- `id` (UUID): Event ID for reference
- `user_id` (UUID): Event owner
- `event_type` (enum): `transaction_posted`, `transfer_received`, `match_recorded`, `balance_adjustment`
- `account_id` (UUID): Primary account involved
- `related_account_id` (UUID, nullable): For transfers
- `amount` (decimal, precision 19,4): Event amount
- `currency` (string): ISO 4217
- `debit_account_id` (UUID): Double-entry: account debited
- `credit_account_id` (UUID): Double-entry: account credited
- `source_transaction_id` (UUID): Transaction that triggered event
- `transaction_match_id` (UUID, nullable): If match-related
- `posting_timestamp` (timestamp): When event was recorded
- `metadata` (JSON): Event context
- `created_at` (timestamp): Record creation time

**Relationships**:
- References `User`
- References `Transaction`
- References `Account` (both debit and credit sides)
- Immutable: Never updated or deleted

**Validation Rules**:
- Immutable: Only INSERTs allowed, no UPDATEs
- Double-entry: Debit account amount = credit account amount
- Amount: Must be positive (sign handled by debit/credit designation)
- Sequence number: Auto-incremented, gap-free

**Constraints**:
- Primary key on sequence_number ensures ordering
- RLS policy: User can only access own events
- Append-only: No deletes except via compliance procedures (legal hold)

---

### Permission

Represents PSD2 permission grants with 90-day expiry.

**Fields**:
- `id` (UUID, primary key)
- `user_id` (UUID, foreign key)
- `bank_api_connection_id` (UUID, foreign key)
- `scope` (string): PSD2 scope (e.g., `ReadAccountsBasic`, `ReadTransactions`)
- `granted_at` (timestamp): When user granted permission
- `expires_at` (timestamp): Automatic expiry (max 90 days after grant)
- `revoked_at` (timestamp, nullable): If user manually revoked
- `last_used_at` (timestamp, nullable): For analytics
- `metadata` (JSON): Scope-specific metadata

**Relationships**:
- Belongs to `User`
- Belongs to `BankAPIConnection`

**Validation Rules**:
- Scope: Valid PSD2 scope per specification
- Expiry: Set to granted_at + 90 days
- Immutable: Permission records never updated (only revoked)

**Constraints**:
- Auto-expiry: Background job revokes expired permissions
- RLS policy: User can only access own permissions

---

### Consent

Represents GDPR lawful basis for data processing.

**Fields**:
- `id` (UUID, primary key)
- `user_id` (UUID, foreign key)
- `purpose` (enum): `account_management`, `transaction_categorization`, `fraud_detection`, `marketing` (separate from account_management)
- `lawful_basis` (enum): `consent`, `contract`, `legal_obligation`, `legitimate_interest`
- `granted_at` (timestamp): When consent given
- `expires_at` (timestamp, nullable): If time-limited
- `revoked_at` (timestamp, nullable)
- `metadata` (JSON): Related consent version, IP, device, language, etc.

**Relationships**:
- Belongs to `User`

**Validation Rules**:
- Purpose: Specific, not vague
- Lawful basis: Required per GDPR; documented
- Immutable: Records never updated (only revoked)

**Constraints**:
- RLS policy: User can only access own consents
- Separate from Permission: Consent is about data processing; Permission is about API scope

---

### Session

Represents an authenticated user session.

**Fields**:
- `id` (UUID, primary key): Session token
- `user_id` (UUID, foreign key)
- `auth_method` (enum): `passkey`, `password+mfa` (if password enabled), `sso`
- `created_at` (timestamp)
- `expires_at` (timestamp): Session lifetime
- `last_activity_at` (timestamp): Last API call
- `ip_address` (string): For audit
- `user_agent` (string): Browser/app identifier
- `metadata` (JSON): Device fingerprint, location, etc.

**Relationships**:
- Belongs to `User`

**Validation Rules**:
- Token: Cryptographically secure, random
- Expiry: Configurable (default 30 days); can be extended on activity
- Immutable: Never updated (new session for changes)

**Constraints**:
- RLS policy: User can only access own sessions
- Automatic cleanup: Expired sessions deleted after 90 days

---

## Relationships Summary

```
User
├── has many Account
├── has many Transaction (manual)
├── has many TransactionMatch
├── has many BankAPIConnection
├── has many Permission
├── has many Consent
├── has many Session
└── has many LedgerEvent

Account
├── belongs to User
├── has many Transaction
├── has many BankAPIConnection
├── has many LedgerEvent (debit/credit)
└── may be archived

Transaction
├── belongs to Account
├── belongs to User
├── may link to TransactionMatch
└── may create LedgerEvent

BankAPIConnection
├── belongs to User
├── references Account (optional)
└── has many Permission

LedgerEvent (immutable, append-only)
├── belongs to User
├── references Account (debit and credit)
└── references Transaction
```

---

## Database Constraints

### Row-Level Security (RLS)

All tables with user data enforce RLS:
- `current_user_id` set via JWT claim in session variable
- Queries filtered: `WHERE user_id = current_user_id`
- Exceptions: System/audit operations via special role

### Indexes

**Performance-critical**:
- `transaction(user_id, account_id, posted_date DESC)` — Dashboard queries
- `ledger_event(user_id, posting_timestamp DESC)` — Ledger queries
- `ledger_event(debit_account_id, credit_account_id)` — Reconciliation
- `bank_api_connection(user_id, provider, sync_status)` — Sync job queries
- `transaction_match(user_id, status)` — Pending matches
- `permission(user_id, expires_at)` — Permission expiry job

### Unique Constraints

- `user(email)` — Email uniqueness
- `account(user_id, name)` — Account name unique per user
- `bank_api_connection(user_id, provider, provider_account_id)` — Prevent duplicate connections
- `transaction_match(manual_transaction_id, api_transaction_id)` — Only one match per pair

---

## Audit & Compliance

### Immutable Audit Trail

- `ledger_event` table: Append-only, only INSERTs, never UPDATEs
- `permission` table: Records kept (never deleted), revoked marked with timestamp
- `consent` table: Records kept (never deleted), revoked marked with timestamp
- `transaction_match` table: Status immutable once confirmed

### Data Retention

- Default: Indefinite (user-owned data)
- Audit logs (ledger, consent, permission): Minimum 7 years (regulatory requirement)
- Deleted user data: Purged after 30-day grace period (GDPR)
- Session data: Purged after 90 days

### Encryption

- Vault service: Encrypts PII (account numbers, SSN) with per-user DEKs
- Credentials: Bank API credentials encrypted before storage
- Passwords (if used): bcrypt or Argon2 hashing
- Database: All financial data encrypted at rest (TLS for transit)
