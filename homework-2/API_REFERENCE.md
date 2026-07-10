# API Reference

### Base URL

```
http://localhost:8000
```

### Authentication

None. All endpoints are publicly accessible locally.

---

## Data Models & Schemas

### Ticket

Full ticket object returned from the API.

| Field                     | Type           | Required | Description                                                   |
| ------------------------- | -------------- | -------- | ------------------------------------------------------------- |
| id                        | UUID           | Yes      | Unique ticket identifier                                      |
| customer_id               | string         | Yes      | Customer identifier                                           |
| customer_email            | string         | Yes      | Customer email address                                        |
| customer_name             | string         | Yes      | Customer name                                                 |
| subject                   | string         | Yes      | Ticket subject (1-200 chars)                                  |
| description               | string         | Yes      | Ticket description (10-2000 chars)                            |
| category                  | string         | Yes      | Ticket category (e.g., bug_report, billing_question)          |
| priority                  | string         | Yes      | Priority level (urgent, high, medium, low)                    |
| status                    | string         | Yes      | Status (new, in_progress, waiting_customer, resolved, closed) |
| created_at                | datetime       | Yes      | Creation timestamp                                            |
| updated_at                | datetime       | Yes      | Last update timestamp                                         |
| resolved_at               | datetime       | No       | Resolution timestamp (null if unresolved)                     |
| assigned_to               | string         | No       | Assigned agent name                                           |
| tags                      | array[string]  | Yes      | List of tags                                                  |
| metadata                  | TicketMetadata | Yes      | Additional metadata                                           |
| classification_confidence | float          | No       | Confidence score (0-1) for auto-classification                |
| classification_overridden | boolean        | Yes      | Whether classification was manually overridden                |

### TicketCreate

Request model for creating a new ticket.

| Field          | Type           | Required | Default       | Description                        |
| -------------- | -------------- | -------- | ------------- | ---------------------------------- |
| customer_id    | string         | Yes      | —             | Customer identifier                |
| customer_email | string         | Yes      | —             | Customer email                     |
| customer_name  | string         | Yes      | —             | Customer name                      |
| subject        | string         | Yes      | —             | Ticket subject (1-200 chars)       |
| description    | string         | Yes      | —             | Ticket description (10-2000 chars) |
| category       | string         | No       | other         | Ticket category                    |
| priority       | string         | No       | medium        | Priority level                     |
| status         | string         | No       | new           | Initial status                     |
| assigned_to    | string         | No       | null          | Agent name                         |
| tags           | array[string]  | No       | []            | Tags list                          |
| metadata       | TicketMetadata | No       | {source: api} | Metadata object                    |

### TicketUpdate

Request model for updating a ticket. All fields are optional.

| Field          | Type           | Description           |
| -------------- | -------------- | --------------------- |
| customer_id    | string         | Update customer ID    |
| customer_email | string         | Update customer email |
| customer_name  | string         | Update customer name  |
| subject        | string         | Update subject        |
| description    | string         | Update description    |
| category       | string         | Update category       |
| priority       | string         | Update priority       |
| status         | string         | Update status         |
| assigned_to    | string         | Update assigned agent |
| tags           | array[string]  | Update tags           |
| metadata       | TicketMetadata | Update metadata       |

### TicketMetadata

Metadata object for tickets.

| Field       | Type   | Description                                |
| ----------- | ------ | ------------------------------------------ |
| source      | string | Source (web_form, email, api, chat, phone) |
| browser     | string | Browser name (optional)                    |
| device_type | string | Device type (desktop, mobile, tablet)      |

### ImportSummary

Response from bulk import operation.

| Field      | Type                  | Description                             |
| ---------- | --------------------- | --------------------------------------- |
| total      | integer               | Total records in import                 |
| successful | integer               | Number of successfully imported tickets |
| failed     | integer               | Number of failed imports                |
| errors     | array[ImportRowError] | List of errors                          |

### ImportRowError

Error for a single row in import.

| Field | Type    | Description         |
| ----- | ------- | ------------------- |
| index | integer | Row index (0-based) |
| error | string  | Error message       |

### ClassificationResult

Result of auto-classification.

| Field          | Type          | Description                   |
| -------------- | ------------- | ----------------------------- |
| category       | string        | Assigned category             |
| priority       | string        | Assigned priority             |
| confidence     | float         | Confidence score (0-1)        |
| reasoning      | string        | Explanation of classification |
| keywords_found | array[string] | Keywords that matched         |

### CategoryKeywords

Category with its keywords.

| Field    | Type          | Description                         |
| -------- | ------------- | ----------------------------------- |
| category | string        | Category key                        |
| keywords | array[string] | List of keywords for classification |

### CategoryCreate

Request model for creating a category.

| Field    | Type          | Required | Description                                              |
| -------- | ------------- | -------- | -------------------------------------------------------- |
| key      | string        | Yes      | Category key (lowercase snake_case, e.g., billing_issue) |
| keywords | array[string] | No       | Initial keywords list                                    |

### CategoryKeywordsUpdate

Request model for adding keywords to a category.

| Field    | Type          | Required | Description     |
| -------- | ------------- | -------- | --------------- |
| keywords | array[string] | Yes      | Keywords to add |

---

## Enums

### Priority

- `urgent` — Critical, requires immediate action
- `high` — Important, should be addressed soon
- `medium` — Standard priority (default)
- `low` — Minor issue or suggestion

### Status

- `new` — Newly created ticket
- `in_progress` — Agent is working on it
- `waiting_customer` — Awaiting customer response
- `resolved` — Issue resolved (resolved_at timestamp set)
- `closed` — Ticket archived

### Source

- `web_form` — Submitted via web form
- `email` — Received via email
- `api` — Created via API
- `chat` — Chat support channel
- `phone` — Phone support channel

### DeviceType

- `desktop` — Desktop/laptop
- `mobile` — Mobile device
- `tablet` — Tablet device

---

## Tickets Resource

### POST /tickets

Create a new ticket.

**Query Parameters:**

- `auto_classify` (boolean, optional, default: false) — Automatically classify the ticket

**Request:**

```bash
curl -X POST http://localhost:8000/tickets?auto_classify=true \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust-001",
    "customer_email": "user@example.com",
    "customer_name": "John Doe",
    "subject": "Cannot log in to account",
    "description": "I am unable to access my account. I have tried resetting my password but it did not work.",
    "priority": "high",
    "assigned_to": "agent-1",
    "tags": ["urgent", "login"],
    "metadata": {
      "source": "web_form",
      "browser": "Chrome",
      "device_type": "desktop"
    }
  }'
```

**Success Response (201):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "cust-001",
  "customer_email": "user@example.com",
  "customer_name": "John Doe",
  "subject": "Cannot log in to account",
  "description": "I am unable to access my account. I have tried resetting my password but it did not work.",
  "category": "account_access",
  "priority": "high",
  "status": "new",
  "created_at": "2026-07-07T15:30:00",
  "updated_at": "2026-07-07T15:30:00",
  "resolved_at": null,
  "assigned_to": "agent-1",
  "tags": ["urgent", "login"],
  "metadata": {
    "source": "web_form",
    "browser": "Chrome",
    "device_type": "desktop"
  },
  "classification_confidence": 0.85,
  "classification_overridden": false
}
```

**Error Response (400):**

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "subject"],
      "msg": "String should have at least 1 characters",
      "input": ""
    }
  ]
}
```

---

### GET /tickets

List all tickets with optional filtering.

**Query Parameters:**

- `category` (string, optional) — Filter by category
- `priority` (string, optional) — Filter by priority (urgent, high, medium, low)
- `status` (string, optional) — Filter by status
- `customer_id` (string, optional) — Filter by customer ID
- `assigned_to` (string, optional) — Filter by assigned agent
- `tag` (string, optional) — Filter by tag

**Request:**

```bash
curl -X GET "http://localhost:8000/tickets?category=billing_question&priority=high"
```

**Success Response (200):**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "customer_id": "cust-001",
    "customer_email": "user@example.com",
    "customer_name": "John Doe",
    "subject": "Invoice discrepancy",
    "description": "I was charged twice for my subscription.",
    "category": "billing_question",
    "priority": "high",
    "status": "new",
    "created_at": "2026-07-07T15:30:00",
    "updated_at": "2026-07-07T15:30:00",
    "resolved_at": null,
    "assigned_to": null,
    "tags": [],
    "metadata": {
      "source": "email",
      "browser": null,
      "device_type": null
    },
    "classification_confidence": 0.9,
    "classification_overridden": false
  }
]
```

---

### GET /tickets/{ticket_id}

Get a specific ticket by ID.

**Variables:**

- `${TICKET_ID}` — UUID of the ticket

**Request:**

```bash
curl -X GET http://localhost:8000/tickets/550e8400-e29b-41d4-a716-446655440000
```

**Success Response (200):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "cust-001",
  "customer_email": "user@example.com",
  "customer_name": "John Doe",
  "subject": "Invoice discrepancy",
  "description": "I was charged twice for my subscription.",
  "category": "billing_question",
  "priority": "high",
  "status": "new",
  "created_at": "2026-07-07T15:30:00",
  "updated_at": "2026-07-07T15:30:00",
  "resolved_at": null,
  "assigned_to": null,
  "tags": [],
  "metadata": {
    "source": "email",
    "browser": null,
    "device_type": null
  },
  "classification_confidence": 0.9,
  "classification_overridden": false
}
```

**Error Response (404):**

```json
{
  "detail": "Ticket 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

### PUT /tickets/{ticket_id}

Update a ticket.

**Variables:**

- `${TICKET_ID}` — UUID of the ticket

**Request:**

```bash
curl -X PUT http://localhost:8000/tickets/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "assigned_to": "agent-2"
  }'
```

**Success Response (200):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "cust-001",
  "customer_email": "user@example.com",
  "customer_name": "John Doe",
  "subject": "Invoice discrepancy",
  "description": "I was charged twice for my subscription.",
  "category": "billing_question",
  "priority": "high",
  "status": "resolved",
  "created_at": "2026-07-07T15:30:00",
  "updated_at": "2026-07-07T15:31:00",
  "resolved_at": "2026-07-07T15:31:00",
  "assigned_to": "agent-2",
  "tags": [],
  "metadata": {
    "source": "email",
    "browser": null,
    "device_type": null
  },
  "classification_confidence": 0.9,
  "classification_overridden": false
}
```

**Error Response (404):**

```json
{
  "detail": "Ticket 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Error Response (400):**

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "status"],
      "msg": "Input should be 'new', 'in_progress', 'waiting_customer', 'resolved' or 'closed'",
      "input": "invalid_status"
    }
  ]
}
```

---

### DELETE /tickets/{ticket_id}

Delete a ticket.

**Variables:**

- `${TICKET_ID}` — UUID of the ticket

**Request:**

```bash
curl -X DELETE http://localhost:8000/tickets/550e8400-e29b-41d4-a716-446655440000
```

**Success Response (204):**
(No content)

**Error Response (404):**

```json
{
  "detail": "Ticket 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

### POST /tickets/import

Bulk import tickets from CSV, JSON, or XML file.

**Query Parameters:**

- `auto_classify` (boolean, optional, default: false) — Automatically classify imported tickets

**Variables:**

- `${FILE_PATH}` — Path to CSV, JSON, or XML file

**Request:**

```bash
curl -X POST "http://localhost:8000/tickets/import?auto_classify=true" \
  -F "file=@${FILE_PATH}"
```

**Success Response (200):**

```json
{
  "total": 50,
  "successful": 48,
  "failed": 2,
  "errors": [
    {
      "index": 5,
      "error": "1 validation error for Ticket\ndescription\n  String should have at least 10 characters [type=string_too_short, input_value='', input_type=str]"
    },
    {
      "index": 12,
      "error": "1 validation error for Ticket\ncustomer_email\n  value is not a valid email address [type=value_error, input_value='invalid-email', input_type=str]"
    }
  ]
}
```

**Error Response (400):**

```json
{
  "detail": "Unsupported file format 'xlsx'. Expected one of: csv, json, xml."
}
```

**Error Response (422):**

```json
{
  "detail": "Invalid XML: mismatched tag: line 5, column 2"
}
```

---

### POST /tickets/{ticket_id}/auto-classify

Trigger automatic classification for a ticket.

**Variables:**

- `${TICKET_ID}` — UUID of the ticket

**Request:**

```bash
curl -X POST http://localhost:8000/tickets/550e8400-e29b-41d4-a716-446655440000/auto-classify
```

**Success Response (200):**

```json
{
  "category": "billing_question",
  "priority": "high",
  "confidence": 0.95,
  "reasoning": "category 'billing_question' matched the most keywords (2): ['invoice', 'charge']; priority 'high' matched keywords ['important']",
  "keywords_found": ["invoice", "charge", "important"]
}
```

**Error Response (404):**

```json
{
  "detail": "Ticket 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

## Categories Resource

### GET /category/list

List all categories with their keywords.

**Request:**

```bash
curl -X GET http://localhost:8000/category/list
```

**Success Response (200):**

```json
[
  {
    "category": "bug_report",
    "keywords": [
      "steps to reproduce",
      "reproduction steps",
      "reproduce",
      "defect",
      "regression"
    ]
  },
  {
    "category": "account_access",
    "keywords": [
      "login",
      "log in",
      "password",
      "2fa",
      "two-factor",
      "authentication",
      "locked out",
      "sign in"
    ]
  },
  {
    "category": "billing_question",
    "keywords": [
      "invoice",
      "payment",
      "refund",
      "billing",
      "charge",
      "subscription",
      "credit card"
    ]
  }
]
```

---

### GET /category/{key}

Get a specific category by key.

**Variables:**

- `${CATEGORY_KEY}` — Category key (e.g., billing_question)

**Request:**

```bash
curl -X GET http://localhost:8000/category/billing_question
```

**Success Response (200):**

```json
{
  "category": "billing_question",
  "keywords": [
    "invoice",
    "payment",
    "refund",
    "billing",
    "charge",
    "subscription",
    "credit card"
  ]
}
```

**Error Response (404):**

```json
{
  "detail": "Category 'nonexistent_category' not found"
}
```

---

### POST /category

Create a new category.

**Request:**

```bash
curl -X POST http://localhost:8000/category \
  -H "Content-Type: application/json" \
  -d '{
    "key": "shipping_delay",
    "keywords": ["shipping", "delayed", "late delivery", "slow"]
  }'
```

**Success Response (201):**

```json
{
  "category": "shipping_delay",
  "keywords": ["shipping", "delayed", "late delivery", "slow"]
}
```

**Error Response (400):**

```json
{
  "detail": [
    {
      "type": "string_pattern",
      "loc": ["body", "key"],
      "msg": "String should match pattern '^[a-z][a-z0-9_]*$'",
      "input": "Invalid-Key"
    }
  ]
}
```

---

### PUT /category/{key}

Add keywords to an existing category.

**Variables:**

- `${CATEGORY_KEY}` — Category key (e.g., billing_question)

**Request:**

```bash
curl -X PUT http://localhost:8000/category/billing_question \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["money", "price"]
  }'
```

**Success Response (200):**

```json
{
  "category": "billing_question",
  "keywords": [
    "invoice",
    "payment",
    "refund",
    "billing",
    "charge",
    "subscription",
    "credit card",
    "money",
    "price"
  ]
}
```

**Error Response (404):**

```json
{
  "detail": "Category 'nonexistent_category' not found"
}
```

---

## Utilities

### GET /health

Health check endpoint.

**Request:**

```bash
curl -X GET http://localhost:8000/health
```

**Success Response (200):**

```json
{
  "status": "ok"
}
```

---

## Common Error Formats

### Validation Error (400)

Returned when request data fails validation.

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "subject"],
      "msg": "String should have at least 1 characters",
      "input": ""
    }
  ]
}
```

### Not Found Error (404)

Returned when a resource does not exist.

```json
{
  "detail": "Ticket 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

### Import Error (400, 422)

Returned when file format is unsupported or file is malformed.

```json
{
  "detail": "Invalid JSON: Expecting value: line 1 column 1 (char 0)"
}
```
