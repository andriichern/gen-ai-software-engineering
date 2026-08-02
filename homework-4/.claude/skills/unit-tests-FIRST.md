---
name: unit-tests-FIRST
description: Framework for writing high-quality unit tests following FIRST principles. Applicable to any programming language and test framework. Defines Fast, Independent, Repeatable, Self-validating, Timely principles with universal guidance for creating maintainable, reliable test suites.
---

# Unit Tests FIRST Principles

## Overview

**FIRST** is a mnemonic for creating high-quality unit tests applicable across all programming languages and test frameworks. These principles ensure tests are reliable, maintainable, and valuable to the development process.

---

## The Five Principles

### F — Fast

**Definition**: Unit tests should execute quickly.

**Why it matters**: 
- Fast tests encourage developers to run them frequently during development
- Slow tests cause developers to skip running them
- Fast feedback loop enables rapid iteration and bug detection

**How to apply** (language/framework agnostic):
- Avoid external I/O (network requests, file operations, database queries)
- Avoid heavy computations or long loops
- Use mocks, stubs, or in-memory equivalents for dependencies
- Mock external services (APIs, databases, file systems)
- Keep test setup and teardown minimal
- Use test fixtures efficiently (don't create unnecessary objects)

**Guidance**:
- Unit tests should execute in milliseconds, not seconds
- If a test takes >1 second, consider if it's truly a unit test (not integration test)
- Mock or eliminate slow dependencies

**Example concept** (pseudocode):
```
// SLOW - Hits real database
test("should create user") {
  db.connect()
  user = createUser("john@example.com")
  assert user.id is not empty
  db.disconnect()
}

// FAST - Uses mock database
test("should create user") {
  mockDb = MockDatabase()
  user = createUser("john@example.com", mockDb)
  assert user.id is not empty
}
```

---

### I — Independent

**Definition**: Each test should be able to run in isolation, in any order, without affecting other tests.

**Why it matters**:
- Independent tests can run in parallel
- Failures are easier to diagnose (isolated failure)
- Tests can be skipped, reordered, or refactored without breaking others
- Test suite reliability increases

**How to apply**:
- Don't share state between tests
- Don't create dependencies between tests
- Each test should set up its own test data
- Each test should clean up after itself (if needed)
- Don't rely on execution order
- Avoid global variables or shared fixtures that get modified
- Don't assume one test runs before/after another

**Guidance**:
- If Test B only passes when Test A runs first, they're not independent
- Each test must be complete and self-contained
- Use setup/teardown to isolate each test
- Use separate fixtures or data for each test

**Example concept**:
```
// BAD - Dependent tests
test("should create user") {
  userId = createUser("john@example.com")
  assert userId > 0
}

test("should delete user") {
  deleteUser(userId)  // Relies on previous test
  assert userExists(userId) == false
}

// GOOD - Independent tests
test("should create user") {
  userId = createUser("john@example.com")
  assert userId > 0
  cleanupUser(userId)
}

test("should delete user") {
  userId = createUser("john@example.com")  // Set up own data
  deleteUser(userId)
  assert userExists(userId) == false
}
```

---

### R — Repeatable

**Definition**: Tests should produce the same results every time they run, regardless of environment or external state.

**Why it matters**:
- Flaky tests (passing sometimes, failing other times) are useless
- Reliable tests give confidence in code changes
- Failures indicate real bugs, not random timing issues
- Tests can be debugged and fixed

**How to apply**:
- Avoid random data or random ordering in tests
- Avoid time-dependent assertions (unless testing time-specific logic)
- Avoid environment-dependent paths or configuration
- Use fixed, known test data
- Mock time if testing time-based behavior
- Don't rely on external state (file system state, environment variables, etc.)
- Use deterministic values, not current time or random values

**Guidance**:
- If a test passes sometimes and fails other times, it's not repeatable
- Use fixed seed values for any randomness (if needed)
- Mock date/time functions if testing time-based logic
- Clear any state before each test

**Example concept**:
```
// BAD - Not repeatable (depends on current time)
test("should apply discount for weekend") {
  order = createOrder(amount: 100)
  discount = calculateDiscount(order)
  assert discount == 10  // Fails if not run on weekend
}

// GOOD - Repeatable (uses fixed date)
test("should apply discount for weekend") {
  mockTime.setDate("Saturday, 2024-01-20")
  order = createOrder(amount: 100)
  discount = calculateDiscount(order, mockTime)
  assert discount == 10  // Always passes
}
```

---

### S — Self-Validating

**Definition**: Tests should pass or fail clearly without manual inspection or interpretation.

**Why it matters**:
- Clear pass/fail is unambiguous
- Test results are obvious in CI/CD pipelines
- No manual verification needed
- Results can be parsed automatically

**How to apply**:
- Use clear, specific assertions
- Assert expected vs actual values explicitly
- Use meaningful assertion messages
- Avoid tests that require manual inspection of output
- Don't print output and say "check the logs"
- Assert on specific values, not vague conditions
- Use assertion libraries effectively

**Guidance**:
- Every test should have at least one assertion
- Assertions should be specific and clear
- Error messages should explain what went wrong
- Avoid: "test output should look reasonable" (needs manual inspection)
- Use: "assert actual == expected" (clear pass/fail)

**Example concept**:
```
// BAD - Not self-validating (requires manual inspection)
test("should format data") {
  result = formatData(input)
  print result  // Manual inspection needed
  // No assertion - tester must look at output
}

// GOOD - Self-validating (clear assertion)
test("should format data") {
  result = formatData(input)
  assert result == "formatted: [data]"  // Clear expected value
}

// GOOD - With clear error message
test("should format data") {
  result = formatData(input)
  assert result == "formatted: [data]", 
    message: "Expected formatted string but got: " + result
}
```

---

### T — Timely

**Definition**: Tests should be written close to the production code they test—ideally before or immediately after.

**Why it matters**:
- Tests written later often focus on happy path only
- Writing tests with code clarifies requirements
- Easier to test code that's not yet entangled with other code
- Encourages writing testable code

**How to apply**:
- Write tests for new code immediately
- Write tests for changed code immediately
- Don't postpone test writing ("we'll test it later")
- Test-Driven Development (TDD): write tests first
- Write tests as you write code
- Cover new/modified functionality with tests

**Guidance**:
- Tests for new code should be written in the same commit/PR
- If a function is changed, its tests should be updated
- Backfilling tests for old code is valuable but less ideal than timely tests
- Timely tests catch issues early, before code is deployed

**Example concept**:
```
// BAD - Timely (tests written months later)
// Code written 2024-01: validate user email
function validateEmail(email) { ... }

// Tests written 2024-06 (only covers happy path)
test("should validate valid email") { ... }

// GOOD - Timely (tests written with code)
// Code written 2024-01: validate user email
function validateEmail(email) { ... }

// Tests written 2024-01 (same time as code)
test("should validate valid email") { ... }
test("should reject empty email") { ... }
test("should reject invalid format") { ... }
```

---

## Applying FIRST Across Languages and Frameworks

### Universal Principles

These principles apply regardless of:
- **Language**: TypeScript, Python, Go, Java, C#, Rust, Ruby, PHP, etc.
- **Framework**: Jest, pytest, unittest, Mocha, Vitest, Go testing, JUnit, xUnit, etc.
- **Project Type**: Web apps, APIs, CLI tools, libraries, microservices, etc.

### Framework-Specific Implementation

Each test framework has mechanisms to support FIRST:

**Setup/Teardown** (isolation):
- Jest: `beforeEach()`, `afterEach()`
- pytest: `@pytest.fixture`, `setup()`, `teardown()`
- Go: `t.Run()`, setup/cleanup patterns
- JUnit: `@Before`, `@After`, `@BeforeEach`, `@AfterEach`

**Mocking/Stubbing** (speed and independence):
- Jest: `jest.mock()`, `jest.spyOn()`
- pytest: `unittest.mock`, `pytest-mock`
- Go: Interface-based mocks
- Java: Mockito, PowerMock

**Assertions** (self-validating):
- Jest: `expect().toBe()`, `expect().toEqual()`
- pytest: `assert`, `pytest.raises()`
- Go: `t.Errorf()`, `t.Fatal()`
- JUnit: `assertEquals()`, `assertTrue()`

---

## Guidelines for Test Quality

### Coverage Target
- Aim for high coverage (95%+) of changed/new code
- Coverage alone doesn't mean quality—also test logic, edge cases, error handling

### Test Types
- **Happy Path**: Normal, expected behavior
- **Error Cases**: Invalid inputs, exceptions, boundary violations
- **Edge Cases**: Empty values, null, extreme values, type mismatches

### Test Organization
- Group related tests (describe blocks, test classes)
- Use clear, descriptive test names
- One assertion concept per test (though multiple assertions are OK)
- Keep tests small and focused

### Test Naming Convention
```
should [expected behavior] when [condition/input]

Examples:
- should return user when valid ID provided
- should throw error when user not found
- should handle null input gracefully
```

---

## Checklist for FIRST-Compliant Tests

For each test, verify:

- ✅ **Fast**: Runs in milliseconds, no slow I/O or dependencies
- ✅ **Independent**: Runs in isolation, doesn't depend on other tests
- ✅ **Repeatable**: Same results every run, deterministic
- ✅ **Self-Validating**: Clear pass/fail, explicit assertions
- ✅ **Timely**: Written for new/changed code

---

## References

- **Original FIRST Principles**: Robert C. Martin ("Clean Code")
- **Test-Driven Development**: Kent Beck
- **Unit Testing Best Practices**: Various frameworks and communities
