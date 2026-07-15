# 🎧 Homework 3: Personal Finance Tracking System

> **Student Name**: Andrii Chernenko
> **Date Submitted**: 15.07.2026
> **AI Tools Used**: Claude Code with speckit plugin

---

## Rationale

As soon as this is a finance-related project some specific considerations were taken into account:

- Security - project must follow best and strict security rules
- Availability - project should be accessible at any given time as a mobile app. Also as it is not a high-critical system backend can comply with 99% value
- Compliance - project complies with GDPR, DORA, PSD2, PSD3 rules
- Data protection - project should follow industry' best practices for encryption, data consistency and integrity
- Traceability - project should implement tracing mechanism
- Observability - project should have monitoring for its crytical parts

### All description below is AI-generated 🙃

---

## 📖 Project Overview

**What It Does**: A personal finance tracking system that helps users manage their money across multiple accounts and understand their spending patterns. Users can record transactions manually (even offline), connect to their banks for automatic transaction retrieval, and the system automatically detects and consolidates duplicate entries to prevent double-counting.

**Why It Matters**:

- Empowers users to track finances without internet (critical for developing regions, unreliable connections)
- Eliminates manual reconciliation through intelligent matching of manual vs. bank-provided transactions
- Respects user privacy with strict data protection and encryption
- Complies with strict EU/UK financial regulations (GDPR, PSD2, PSD3)

**For Whom**: Individual consumers aged 18+ who want to manage their personal finances with confidence in data privacy and accuracy.

---

## 🏗️ Architecture & Design Philosophy

This system is built on several core principles ([see specification](specs/001-finance-tracker/spec.md)):

| Principle                 | Benefit                               | Details                                                                                                                                                                            |
| ------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Offline-First**         | Users never blocked by internet       | Mobile app works completely offline; transactions sync when online ([spec: User Story 1](specs/001-finance-tracker/spec.md#user-story-1---manual-transaction-entry-priority-p1))   |
| **Double-Entry Ledger**   | Financial accuracy guaranteed         | Every transaction creates balanced debit+credit entries; balance always calculated from ledger ([plan: Append-Only Ledger](specs/001-finance-tracker/plan.md#append-only-ledger))  |
| **Conflict-Free Merging** | Multi-device sync without data loss   | When same transaction edited on Device A and B, user chooses which version to keep ([clarifications](specs/001-finance-tracker/spec.md#session-2026-07-15-initial-clarifications)) |
| **Zero-Trust Encryption** | Data never exposed unencrypted        | Per-user encryption keys; PII stored in separate vault; TLS 1.3 everywhere ([spec: FR-023](specs/001-finance-tracker/spec.md#functional-requirements))                             |
| **Compliance-First**      | Regulatory requirements met by design | GDPR/PSD2/DORA/PCI-DSS built in from day one, not retrofitted ([plan: Compliance](specs/001-finance-tracker/plan.md#compliance))                                                   |

---

## 🎯 Non-Functional Requirements

These constraints guide all development decisions ([see spec success criteria](specs/001-finance-tracker/spec.md#measurable-outcomes)):

| Attribute        | Target                                 | Why                                                                |
| ---------------- | -------------------------------------- | ------------------------------------------------------------------ |
| **Availability** | 99% uptime (~7.2 hours downtime/month) | Financial users expect reliable access; 99.99% reserved for future |
| **Performance**  | API <500ms p95, mobile <2s load        | Slow apps frustrate users; measured and monitored                  |
| **Accuracy**     | Transaction matching ≥90%              | Bad matches cost user trust                                        |
| **Sync Speed**   | 1000+ transactions in <30s             | Bank syncs shouldn't block users                                   |
| **Data Safety**  | Zero data loss on app crash            | Financial data too valuable to lose                                |
| **Usability**    | 90% first-time success without docs    | Good design speaks for itself                                      |
| **Compliance**   | Zero critical audit findings           | Non-negotiable for regulated financial product                     |

---

## 💡 Selected Best Practices

The system demonstrates financial software best practices:

| Practice                  | Implementation                                 | Spec Reference                                                                   |
| ------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------- |
| **Immutable Audit Trail** | Append-only event ledger (7-year retention)    | [plan: Append-Only Ledger](specs/001-finance-tracker/plan.md#append-only-ledger) |
| **Financial Accuracy**    | Double-entry accounting (debits = credits)     | [plan: Design Decisions](specs/001-finance-tracker/plan.md#append-only-ledger)   |
| **Data Minimization**     | Only collect necessary fields; delete old data | [spec: FR-030](specs/001-finance-tracker/spec.md#functional-requirements) (GDPR) |
| **User Consent Tracking** | Separate GDPR lawful basis records             | [plan: Consent Domain](specs/001-finance-tracker/plan.md#project-structure)      |
| **Permission Expiry**     | PSD2 scopes auto-expire after 90 days          | [spec: FR-032](specs/001-finance-tracker/spec.md#functional-requirements)        |
| **Rate Limiting**         | 5 failed auth attempts → 15-min lockout        | [spec: FR-027](specs/001-finance-tracker/spec.md#functional-requirements)        |
| **Structured Logging**    | JSON logs with context (user_id, request_id)   | [spec: FR-035](specs/001-finance-tracker/spec.md#functional-requirements)        |
| **Distributed Tracing**   | Track requests across mobile → backend → APIs  | [spec: FR-037](specs/001-finance-tracker/spec.md#functional-requirements)        |
| **Right to be Forgotten** | User data deleted within 30 days               | [spec: SC-011](specs/001-finance-tracker/spec.md#measurable-outcomes)            |
| **Encryption at Rest**    | AES-256 with per-user DEKs                     | [plan: Encryption](specs/001-finance-tracker/plan.md#constraints)                |

---

## 🛠️ Technology Stack

The tech stack was chosen for reliability, security, and team expertise:

### Backend Service

- **Language**: [Go 1.21+](https://golang.org) — Fast, compiled, excellent concurrency for financial operations
- **Framework**: [Echo](https://echo.labstack.com) or [chi](https://github.com/go-chi/chi) — Lightweight, zero dependencies, perfect for APIs
- **Database**: [PostgreSQL 16](https://www.postgresql.org) with Row-Level Security — Enterprise-grade, RLS enforces data isolation at DB layer
- **Query Builder**: [sqlc](https://sqlc.dev) — Type-safe queries, no ORM overhead, predictable performance
- **Encryption**: [Cloud KMS](https://aws.amazon.com/kms/) (AWS/Azure) — Hardware-backed key management, audit trails
- **Observability**: [OpenTelemetry](https://opentelemetry.io) — Vendor-neutral metrics, logs, traces

**Why**: Go's simplicity and performance suit financial operations. PostgreSQL's RLS enforces security at the DB level (can't bypass via app). sqlc eliminates ORM unpredictability. KMS removes key management from our responsibility.

### Mobile Apps

- **Framework**: [Flutter 3.13+](https://flutter.dev) with [Dart 3.1+](https://dart.dev) — Single codebase for iOS + Android
- **Local Database**: [SQLite](https://sqlite.org) via [sqflite](https://pub.dev/packages/sqflite) — Lightweight, zero-config, perfect for offline
- **Encrypted Storage**: [flutter_secure_storage](https://pub.dev/packages/flutter_secure_storage) — Uses platform keychain (Keychain on iOS, Keystore on Android)
- **HTTP Client**: [dio](https://pub.dev/packages/dio) — Built-in retry logic, interceptors for auth
- **UI**: [Material 3](https://m3.material.io) — Modern, accessible, consistent across platforms
- **State**: [Riverpod](https://riverpod.dev) — Reactive, testable, no boilerplate

**Why**: Flutter eliminates iOS/Android code duplication. SQLite offline storage is instant. Material 3 ensures accessibility (WCAG 2.1 AA).

### Bank Integrations

- **Primary**: [GoCardless](https://gocardless.com) (PSD2 aggregator) — Direct bank connections, highest data freshness
- **Secondary**: [Salt Edge](https://www.saltedge.com) — Fallback coverage, different bank connections

**Why**: PSD2 (Open Banking) standardizes access. Two aggregators ensure coverage if one fails. ([spec: FR-009](specs/001-finance-tracker/spec.md#functional-requirements))

### Regulatory Frameworks

- **GDPR** — EU data privacy (user consent, right-to-be-forgotten, DPA)
- **UK Data Protection Act 2018** — Post-Brexit equivalent
- **PSD2 / PSD3** — Open Banking (secure API access, 90-day permission expiry)
- **DORA** — Digital Operational Resilience Act (observability, 99% uptime SLA)
- **PCI-DSS** — Payment card industry (credential handling, no logging of sensitive data)

([spec: FR-030 through FR-033](specs/001-finance-tracker/spec.md#functional-requirements))

---

## Features

### 📱 Offline-First Mobile App (iOS 14+, Android 11+)

- Add transactions without internet connectivity
- All data reads served from local SQLite database
- Writes queue locally and automatically sync when online
- Sync is eventually consistent (may take minutes)
- Multi-device support with conflict resolution for concurrent edits
- No network required for core functionality

### 🏦 Bank API Integration & Transaction Matching

- GoCardless (primary PSD2 aggregator) and Salt Edge (secondary aggregator)
- Automatic transaction retrieval and matching
- Fuzzy algorithm detects duplicates (±10% amount, ±1 day date)
- Manual + API transactions matched automatically
- User confirms/rejects matches (never automatic)
- Prevents double-counting in balance calculations

### 💰 Multi-Account Support with Double-Entry Ledger

- **Account Types**: Credit cards (with limit tracking), debit cards (balance management), savings accounts (interest tracking), cash (envelope tracking)
- Multiple currencies with automatic conversion
- Double-entry accounting: every transaction creates balanced debit + credit posting
- Balance always derived from ledger sum (never stored)
- Append-only ledger: no updates, only inserts—ensures accuracy and audit trail

### 🔒 Security & Compliance

- **Encryption**: TLS 1.3 (transit), AES-256 (at-rest) with per-user Data Encryption Keys
- **Authentication**: Passkeys (Webauthn) + biometric (mobile)
- **Audit Trail**: 7-year retention of all sensitive operations
- **GDPR**: Right-to-be-forgotten, consent tracking, data export
- **PSD2/PSD3**: 90-day permission expiry, strong authentication for sensitive operations
- **DORA**: Observability (logging, metrics, alerting), 99% uptime SLA
- **PCI-DSS**: Secure credential handling, sensitive data never logged

### ⚡ Performance & Reliability

- API: <500ms p95 latency
- Mobile: <2s cold start
- Bank sync: <30s for 1000+ transactions
- 99% uptime SLA (~7.2 hours downtime/month)
- Zero data loss on app crash
- 90% first-time usability without documentation

## Documentation

| Document                                                                                                                   | Purpose                                                                      |
| -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [**specs/001-finance-tracker/spec.md**](specs/001-finance-tracker/spec.md)                                                 | User stories, functional requirements, success criteria, clarifications      |
| [**specs/001-finance-tracker/plan.md**](specs/001-finance-tracker/plan.md)                                                 | Architecture, design decisions, tech stack, project structure                |
| [**specs/001-finance-tracker/data-model.md**](specs/001-finance-tracker/data-model.md)                                     | Entity definitions, relationships, validation rules                          |
| [**specs/001-finance-tracker/tasks.md**](specs/001-finance-tracker/tasks.md)                                               | 160 implementation tasks organized by phase and user story                   |
| [**specs/001-finance-tracker/contracts/backend-mobile-api.md**](specs/001-finance-tracker/contracts/backend-mobile-api.md) | REST API contract with request/response examples                             |
| [**docs/API.md**](docs/API.md)                                                                                             | Complete API endpoint documentation                                          |
| [**docs/SCHEMA.md**](docs/SCHEMA.md)                                                                                       | Database schema and ER diagrams                                              |
| [**.claude/AGENTS.md**](.claude/AGENTS.md)                                                                                 | Agent guidelines: tech stack, domain rules, code style, security, edge cases |
| [**CLAUDE.md**](CLAUDE.md)                                                                                                 | Project-specific instructions                                                |

## Support

- **Specification**: [specs/001-finance-tracker/spec.md](specs/001-finance-tracker/spec.md)
- **Architecture**: [specs/001-finance-tracker/plan.md](specs/001-finance-tracker/plan.md)
- **Guidelines**: [.claude/AGENTS.md](.claude/AGENTS.md)
- **Issues**: Check [specs/001-finance-tracker/quickstart.md](specs/001-finance-tracker/quickstart.md) for validation scenarios

---

**Last Updated**: 2026-07-15  
**Status**: Ready for Implementation
