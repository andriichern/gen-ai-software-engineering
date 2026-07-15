# API Contract: Backend ↔ Mobile Application

**Purpose**: Define REST API contracts between mobile apps (iOS/Android) and Go backend

**Status**: Phase 1 Design (Ready for Implementation)

**Protocol**: HTTP/1.1 REST with JSON payloads

**Base URL**: `https://api.finance-tracker.example.com/v1`

**Authentication**: Bearer JWT token in `Authorization` header

---

## Authentication Endpoints

### POST /auth/register

Register a new user account.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "timezone": "Europe/London"
}
```

**Response** (201 Created):
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "requires_email_verification": true,
  "message": "Registration successful. Check email for verification link."
}
```

**Errors**:
- 400: Invalid email format, weak password
- 409: Email already registered

---

### POST /auth/login

Authenticate user with email/password or passkey.

**Request** (password):
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Request** (passkey):
```json
{
  "email": "user@example.com",
  "passkey_credential": { /* WebAuthn credential */ }
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "expires_in": 86400,
  "user_id": "uuid",
  "email": "user@example.com"
}
```

**Errors**:
- 401: Invalid credentials, passkey validation failed
- 429: Rate limited (max 5 failed attempts, 15-min lockout)

---

### POST /auth/refresh

Refresh expired access token using refresh token.

**Request**:
```json
{
  "refresh_token": "eyJhbGci..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGci...",
  "expires_in": 86400
}
```

**Errors**:
- 401: Invalid or expired refresh token
- 403: Refresh token revoked

---

### POST /auth/logout

Revoke current session.

**Request**: Empty body

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

---

## Transaction Endpoints

### GET /transactions

List all transactions (manual + API) with filtering.

**Query Parameters**:
- `account_id` (uuid, optional): Filter by account
- `from_date` (ISO 8601 date, optional): Start date (inclusive)
- `to_date` (ISO 8601 date, optional): End date (inclusive)
- `type` (string, optional): `income`, `expense`, `transfer`
- `category` (string, optional): Expense category
- `source` (string, optional): `manual`, `gocardless`, `saltedge`
- `limit` (integer, default 50, max 500): Pagination limit
- `offset` (integer, default 0): Pagination offset

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "account_id": "uuid",
      "amount": "99.99",
      "type": "expense",
      "source": "manual",
      "description": "Coffee",
      "category": "Food & Dining",
      "posted_date": "2026-07-15",
      "matched_with": "uuid or null",
      "match_confidence": 95.5,
      "is_pending": false,
      "created_at": "2026-07-15T10:30:00Z",
      "notes": "Optional user note"
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 50,
    "total": 1234
  }
}
```

**Errors**:
- 401: Unauthorized
- 400: Invalid query parameters

---

### POST /transactions

Create a new manual transaction.

**Request**:
```json
{
  "account_id": "uuid",
  "amount": "99.99",
  "type": "expense",
  "description": "Coffee purchase",
  "category": "Food & Dining",
  "posted_date": "2026-07-15",
  "notes": "Optional note"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "account_id": "uuid",
  "amount": "99.99",
  "type": "expense",
  "source": "manual",
  "description": "Coffee purchase",
  "category": "Food & Dining",
  "posted_date": "2026-07-15",
  "created_at": "2026-07-15T10:30:00Z"
}
```

**Errors**:
- 400: Invalid amount, future date, invalid category
- 401: Unauthorized
- 404: Account not found

---

### GET /transactions/{transaction_id}

Retrieve single transaction details.

**Response** (200 OK):
```json
{
  "id": "uuid",
  "account_id": "uuid",
  "amount": "99.99",
  "type": "expense",
  "source": "manual",
  "description": "Coffee purchase",
  "category": "Food & Dining",
  "posted_date": "2026-07-15",
  "matched_with": "uuid or null",
  "match_details": {
    "confidence": 95.5,
    "matched_reason": "Amount and date match within threshold"
  },
  "created_at": "2026-07-15T10:30:00Z"
}
```

**Errors**:
- 401: Unauthorized
- 404: Transaction not found

---

### DELETE /transactions/{transaction_id}

Delete a manual transaction (logical delete for manual, immutable for API transactions).

**Response** (204 No Content)

**Errors**:
- 401: Unauthorized
- 403: Cannot delete API-sourced transaction
- 404: Transaction not found

---

## Account Endpoints

### GET /accounts

List all user accounts.

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Chase Checking",
      "type": "debit_card",
      "balance": "1234.56",
      "currency": "GBP",
      "created_at": "2026-06-01T00:00:00Z",
      "metadata": {
        "icon_color": "#FF5733",
        "position": 0
      }
    }
  ]
}
```

---

### POST /accounts

Create a new account.

**Request**:
```json
{
  "name": "Chase Checking",
  "type": "debit_card",
  "currency": "GBP",
  "metadata": {
    "icon_color": "#FF5733"
  }
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "name": "Chase Checking",
  "type": "debit_card",
  "balance": "0.00",
  "currency": "GBP",
  "created_at": "2026-07-15T10:30:00Z"
}
```

**Errors**:
- 400: Invalid account type, duplicate name
- 401: Unauthorized

---

### GET /accounts/{account_id}

Retrieve account details and balance.

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Chase Checking",
  "type": "debit_card",
  "balance": "1234.56",
  "currency": "GBP",
  "created_at": "2026-06-01T00:00:00Z",
  "available_credit": 8765.44,
  "metadata": {
    "credit_limit": 10000.00,
    "interest_rate": 0.0,
    "icon_color": "#FF5733"
  }
}
```

---

### PUT /accounts/{account_id}

Update account details.

**Request**:
```json
{
  "name": "Chase Premium Checking",
  "metadata": {
    "icon_color": "#0088FF"
  }
}
```

**Response** (200 OK): Updated account object

**Errors**:
- 400: Duplicate name, invalid metadata
- 401: Unauthorized
- 404: Account not found

---

### POST /accounts/{account_id}/archive

Archive an account (soft delete).

**Response** (200 OK):
```json
{
  "message": "Account archived",
  "archived_at": "2026-07-15T10:30:00Z"
}
```

**Errors**:
- 401: Unauthorized
- 404: Account not found

---

## Bank API Integration Endpoints

### GET /bank-connections

List connected bank accounts.

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "provider": "gocardless",
      "institution_name": "Barclays Bank",
      "account_id": "uuid (app account)",
      "sync_status": "active",
      "last_sync_at": "2026-07-15T09:30:00Z",
      "last_sync_transaction_count": 42,
      "permissions": [
        "ReadAccountsBasic",
        "ReadTransactions"
      ],
      "permission_expires_at": "2026-10-13T00:00:00Z"
    }
  ]
}
```

---

### POST /bank-connections

Initiate bank API connection (OAuth redirect or manual credential entry).

**Request**:
```json
{
  "provider": "gocardless",
  "account_id": "uuid (app account, optional)"
}
```

**Response** (200 OK):
```json
{
  "redirect_url": "https://api.gocardless.com/auth/...",
  "state": "csrf-token"
}
```

Mobile app redirects to `redirect_url`; API returns auth code via callback.

---

### POST /bank-connections/callback

Handle OAuth callback from bank API.

**Query Parameters**:
- `code`: Authorization code from bank
- `state`: CSRF token

**Response** (302 Redirect to app scheme):
```
finance-tracker://bank-connection-success?connection_id=uuid
```

**Errors**:
- 400: Invalid state (CSRF), authorization failed
- 403: User revoked consent

---

### POST /bank-connections/{connection_id}/sync

Manually trigger bank sync for a connection.

**Response** (202 Accepted):
```json
{
  "connection_id": "uuid",
  "sync_job_id": "uuid",
  "message": "Sync started in background"
}
```

Mobile app can poll `/sync-jobs/{job_id}` for progress.

**Errors**:
- 401: Unauthorized
- 404: Connection not found
- 409: Sync already in progress

---

### GET /bank-connections/{connection_id}/sync-status

Get sync job status and progress.

**Response** (200 OK):
```json
{
  "job_id": "uuid",
  "status": "running",
  "progress_percent": 45,
  "transactions_synced": 45,
  "started_at": "2026-07-15T10:00:00Z",
  "estimated_completion_at": "2026-07-15T10:05:00Z"
}
```

---

### POST /bank-connections/{connection_id}/revoke

Revoke bank connection (disconnect OAuth).

**Response** (200 OK):
```json
{
  "message": "Bank connection revoked"
}
```

Existing API transactions remain in app for user reference.

---

## Transaction Matching Endpoints

### GET /transaction-matches

List pending and confirmed transaction matches.

**Query Parameters**:
- `status` (string): `pending`, `confirmed`, `rejected`

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid",
      "manual_transaction_id": "uuid",
      "api_transaction_id": "uuid",
      "confidence_score": 95.5,
      "status": "pending",
      "manual_transaction": { /* transaction object */ },
      "api_transaction": { /* transaction object */ },
      "match_reason": {
        "amount_delta": 0,
        "date_delta": 0,
        "description_similarity": 98
      }
    }
  ]
}
```

---

### POST /transaction-matches/{match_id}/confirm

Confirm a pending match.

**Request**:
```json
{
  "confirmed": true,
  "note": "User's reasoning (optional)"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "status": "confirmed",
  "confirmed_at": "2026-07-15T10:30:00Z"
}
```

Matching service creates ledger events; balance updated.

**Errors**:
- 401: Unauthorized
- 404: Match not found
- 409: Match already confirmed/rejected

---

### POST /transaction-matches/{match_id}/reject

Reject a pending match (keep both transactions separate).

**Response** (200 OK):
```json
{
  "id": "uuid",
  "status": "rejected",
  "rejected_at": "2026-07-15T10:30:00Z"
}
```

---

## Dashboard & Insights Endpoints

### GET /dashboard

Get user's financial dashboard summary.

**Response** (200 OK):
```json
{
  "total_balance": "12345.67",
  "accounts": [
    {
      "account_id": "uuid",
      "name": "Chase Checking",
      "type": "debit_card",
      "balance": "5000.00"
    }
  ],
  "monthly_expense": "2345.67",
  "monthly_income": "3500.00",
  "spending_by_category": [
    {
      "category": "Food & Dining",
      "amount": "567.89",
      "percentage": 24.2
    }
  ],
  "pending_matches": 3,
  "unsynced_changes": 0,
  "sync_status": "synced"
}
```

---

### GET /insights/trends

Get spending trends and analytics.

**Query Parameters**:
- `period` (string): `week`, `month`, `quarter`, `year`
- `category` (string, optional): Filter by category

**Response** (200 OK):
```json
{
  "period": "month",
  "data": [
    {
      "date": "2026-07-01",
      "expense": "500.00",
      "income": "2500.00",
      "balance_change": 2000.00
    }
  ]
}
```

---

## Categories Endpoints

### GET /categories

List all spending/income categories.

**Response** (200 OK):
```json
{
  "expense_categories": [
    "Food & Dining",
    "Transportation",
    "Utilities",
    "Entertainment"
  ],
  "income_categories": [
    "Salary",
    "Freelance",
    "Investment"
  ],
  "custom_categories": [
    "Custom Category 1"
  ]
}
```

---

### POST /categories

Create a custom category.

**Request**:
```json
{
  "name": "Pet Care",
  "type": "expense",
  "icon": "🐾"
}
```

**Response** (201 Created): Category object

---

## Error Response Format

All error responses follow this format:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Descriptive error message",
    "details": {
      "field": "amount",
      "reason": "Must be positive"
    }
  },
  "request_id": "uuid",
  "timestamp": "2026-07-15T10:30:00Z"
}
```

**Common Error Codes**:
- `INVALID_REQUEST`: 400 Bad Request
- `UNAUTHORIZED`: 401 Unauthorized
- `FORBIDDEN`: 403 Forbidden (auth succeeded but action denied)
- `NOT_FOUND`: 404 Not Found
- `CONFLICT`: 409 Conflict (e.g., duplicate name)
- `RATE_LIMITED`: 429 Too Many Requests
- `INTERNAL_ERROR`: 500 Internal Server Error

---

## Offline Sync Protocol

Mobile apps maintain a local queue of changes (transactions, matches) while offline. When connection restored:

1. **POST /sync** (batched changes)
   ```json
   {
     "changes": [
       {
         "type": "transaction_created",
         "data": { /* transaction */ }
       },
       {
         "type": "match_confirmed",
         "data": { /* match ID and confirmation */ }
       }
     ],
     "client_version": "1.2.3"
   }
   ```

2. **Response** (200 OK):
   ```json
   {
     "synced_count": 2,
     "conflicts": [],
     "server_updates": [
       { /* any server-side updates to pull */ }
     ]
   }
   ```

3. Mobile app reconciles response and updates local state.

---

## Rate Limiting

All endpoints rate-limited per user:
- 100 requests/minute for list endpoints
- 10 requests/minute for write endpoints
- 5 requests/minute for bank sync initiation

Headers included in responses:
- `X-RateLimit-Limit`: Rate limit ceiling
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp of next reset
