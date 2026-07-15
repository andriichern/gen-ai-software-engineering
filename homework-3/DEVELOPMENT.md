## Development Workflow

### Before Starting Any Task

1. Read the [feature specification](specs/001-finance-tracker/spec.md)
2. Read the [implementation plan](specs/001-finance-tracker/plan.md)
3. Check the [agent guidelines](.claude/AGENTS.md) for code style and domain rules

### During Development

1. **Write tests first** (Test-Driven Development preferred)
2. **Implement domain logic** — business logic in `pkg/domain/` (backend) or `domain/` (mobile)
3. **Implement storage** — repositories in `internal/postgres/` (backend) or DAOs (mobile)
4. **Implement endpoints** — HTTP handlers in `pkg/http/` (backend) or UI screens (mobile)
5. **Verify coverage** — ≥85% backend core, ≥80% mobile core
6. **Verify performance** — measure latency, no unexplained regressions
7. **Security review** — no sensitive data in logs, encryption verified

### Before Submitting PR

- [ ] Linting passes: `golangci-lint run` (backend), `flutter analyze` (mobile)
- [ ] Type checking passes: `go vet` (backend), Dart analyzer (mobile)
- [ ] Tests pass locally: `go test ./...` (backend), `flutter test` (mobile)
- [ ] Coverage meets targets: ≥85% backend core, ≥80% mobile core
- [ ] Performance verified: no unexplained regressions
- [ ] Security review: no sensitive data logged
- [ ] PR references spec requirements (FR-###, SC-###)

## Project Structure

```
├── backend/                          # Go backend (modular monolith)
│   ├── cmd/
│   │   ├── server/                  # HTTP server entry point
│   │   ├── worker/                  # Async job worker
│   │   └── migration/               # DB migration runner
│   ├── pkg/
│   │   ├── identity/                # Auth, sessions, passkeys
│   │   ├── permission/              # PSD2 permission state machine
│   │   ├── consent/                 # GDPR lawful basis
│   │   ├── ingestion/               # Bank API aggregators
│   │   ├── matching/                # Transaction deduplication
│   │   ├── ledger/                  # Append-only double-entry ledger
│   │   ├── categorisation/          # Transaction categorization
│   │   ├── insights/                # Read models & analytics
│   │   ├── vault/                   # PII encryption service
│   │   ├── http/                    # HTTP handlers
│   │   ├── storage/                 # Repository interfaces
│   │   └── telemetry/               # Observability
│   ├── internal/
│   │   ├── postgres/                # PostgreSQL implementations
│   │   └── mock/                    # Test mocks
│   ├── migrations/                  # Database migrations
│   ├── tests/
│   │   ├── integration/             # Integration tests
│   │   ├── contract/                # Contract tests
│   │   └── fixtures/                # Test data
│   ├── go.mod / go.sum
│   ├── Makefile
│   └── docker-compose.yml
│
├── mobile/                           # Flutter mobile app
│   ├── lib/
│   │   ├── main.dart
│   │   ├── features/
│   │   │   ├── transaction/
│   │   │   ├── account/
│   │   │   ├── bank_sync/
│   │   │   ├── matching/
│   │   │   └── dashboard/
│   │   ├── core/
│   │   │   ├── database/            # SQLite setup
│   │   │   ├── network/             # HTTP client
│   │   │   ├── local_storage/       # Encrypted storage
│   │   │   ├── sync/                # Offline sync manager
│   │   │   └── encryption/          # Local crypto
│   │   └── shared/
│   │       ├── models/
│   │       ├── providers/           # Dependency injection
│   │       └── utils/
│   ├── test/
│   │   ├── unit/
│   │   ├── widget/
│   │   └── integration/
│   ├── pubspec.yaml
│   ├── analysis_options.yaml
│   └── README.md
│
├── specs/                            # Feature specifications
│   └── 001-finance-tracker/
│       ├── spec.md                  # User stories, requirements
│       ├── plan.md                  # Architecture, design decisions
│       ├── data-model.md            # Entity definitions
│       ├── tasks.md                 # Implementation tasks
│       ├── contracts/               # API contracts
│       ├── quickstart.md            # Validation scenarios
│       └── checklists/
│
├── docs/                            # Documentation
│   ├── API.md                       # REST API endpoints
│   ├── SCHEMA.md                    # Database schema
│   └── DEPLOYMENT.md                # Deployment process
│
├── .claude/                         # Agent & development guidelines
│   ├── AGENTS.md                    # Agent guidelines (tech stack, domain rules, security)
│   └── settings.json
│
├── .github/
│   └── workflows/                   # CI/CD pipelines
│       ├── lint.yml
│       ├── test.yml
│       └── type-check.yml
│
├── README.md                        # This file
├── CLAUDE.md                        # Project instructions
└── docker-compose.yml               # Local dev environment

```

## Quick Start

### Prerequisites

- **Go 1.21+** — [Install](https://golang.org/doc/install)
- **Flutter 3.13+** with **Dart 3.1+** — [Install](https://flutter.dev/docs/get-started/install)
- **PostgreSQL 16** — [Install](https://www.postgresql.org/download/) or use Docker
- **Docker & Docker Compose** — [Install](https://docs.docker.com/get-docker/)

### Local Development Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/your-org/finance-tracker.git
cd finance-tracker
```

#### 2. Set Up Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your local configuration
# See "Environment Configuration" section below
```

#### 3. Start Backend

**Option A: Using Docker Compose (Recommended)**

```bash
# Start PostgreSQL and other services
docker-compose up -d

# Run database migrations
cd backend
go run ./cmd/migration migrate up

# Start the backend server
go run ./cmd/server/main.go
```

The backend will be available at `http://localhost:8080`.

**Option B: Local PostgreSQL**

If you have PostgreSQL running locally:

```bash
cd backend

# Run migrations
go run ./cmd/migration migrate up

# Start server
go run ./cmd/server/main.go
```

#### 4. Start Mobile App

```bash
cd mobile

# Install dependencies
flutter pub get

# Run on iOS simulator
flutter run -d macos

# OR run on Android emulator
flutter run -d emulator-5554

# OR run on connected device
flutter run
```

### Running Tests

#### Backend Tests

```bash
cd backend

# Run all tests
go test ./...

# Run specific package
go test ./pkg/matching/...

# Run with coverage
go test -cover ./...

# Run integration tests (requires Docker)
docker-compose up -d
go test -tags integration ./tests/integration/...
```

#### Mobile Tests

```bash
cd mobile

# Run unit tests
flutter test

# Run integration tests
flutter test integration_test/

# Run specific test file
flutter test test/unit/features/transaction/transaction_test.dart
```

### Linting & Type Checking

#### Backend

```bash
cd backend

# Lint with golangci-lint
golangci-lint run

# Type check
go vet ./...

# Format code
go fmt ./...
```

#### Mobile

```bash
cd mobile

# Analyze code
flutter analyze

# Format code
dart format lib/ test/
```

## Environment Configuration

Create a `.env` file in the project root:

```env
# Backend Configuration
PORT=8080
DB_HOST=localhost
DB_PORT=5432
DB_NAME=finance_tracker
DB_USER=postgres
DB_PASSWORD=postgres
DB_SSL_MODE=disable

# Database Migrations
MIGRATION_DIR=./backend/migrations

# JWT Configuration
JWT_SECRET=your-secret-key-min-32-chars
JWT_EXPIRY=2592000  # 30 days in seconds

# Bank APIs (Sandbox/Testing)
GOCARDLESS_CLIENT_ID=your-gocardless-sandbox-client-id
GOCARDLESS_CLIENT_SECRET=your-gocardless-sandbox-secret
GOCARDLESS_API_BASE=https://api.sandbox.gocardless.com

SALTEDGE_CLIENT_ID=your-saltedge-sandbox-client-id
SALTEDGE_CLIENT_SECRET=your-saltedge-sandbox-secret
SALTEDGE_API_BASE=https://www.saltedge.com/api/v5

# Encryption & Key Management
KMS_ENDPOINT=http://localhost:9000  # or AWS/Azure KMS
KMS_KEY_ID=your-kms-key-id

# Observability
LOG_LEVEL=debug
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317  # optional

# Mobile App Configuration (in pubspec.yaml or .env.local)
API_BASE_URL=http://localhost:8080
ENABLE_MOCK_BANK_API=true  # Use mock for testing
```

**See `.env.example` for all available options.**

## Troubleshooting

### Backend Issues

**Port 8080 already in use**

```bash
# Find process using port
lsof -i :8080

# Kill it or use different port
PORT=9000 go run ./cmd/server/main.go
```

**Database connection refused**

```bash
# Ensure PostgreSQL is running
docker-compose up -d postgres

# Check connection
psql -h localhost -U postgres -d finance_tracker
```

**Migrations failed**

```bash
# Reset database (development only!)
dropdb finance_tracker
createdb finance_tracker

# Re-run migrations
go run ./cmd/migration migrate up
```

### Mobile Issues

**Flutter SDK not found**

```bash
# Check Flutter installation
flutter doctor

# Update Flutter
flutter upgrade
```

**iOS build fails**

```bash
cd mobile/ios
pod repo update
pod install
cd ../..
flutter run -d macos
```

**Android build fails**

```bash
# Accept licenses
flutter doctor --android-licenses

# Clean build
flutter clean
flutter pub get
flutter run
```

## Performance & Monitoring

### Backend Profiling

```bash
# CPU profile
go test -cpuprofile=cpu.prof ./...
go tool pprof cpu.prof

# Memory profile
go test -memprofile=mem.prof ./...
go tool pprof mem.prof
```

### Database Monitoring

```bash
# Connect to database
psql -h localhost -U postgres -d finance_tracker

# Show slow queries
SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

# Check indexes
SELECT * FROM pg_indexes WHERE tablename = 'transactions';
```

### Mobile Performance

```bash
# Run with performance monitoring
flutter run --profile

# Analyze frame times
flutter run --verbose
```

## Contributing

See [.claude/AGENTS.md](.claude/AGENTS.md) for:

- **Tech Stack**: Go 1.21+, Flutter 3.13+, PostgreSQL 16, SQLite
- **Code Style**: Naming conventions, structure, testing patterns
- **Domain Rules**: Financial, offline-first, security principles
- **Security Requirements**: Encryption, authentication, compliance
- **Edge Cases**: Transaction, account, API, and sync scenarios
