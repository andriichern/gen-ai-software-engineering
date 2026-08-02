---
name: research-quality-measurement
description: Generic framework for categorizing any bugs by severity level. Classifies issues as Low, Medium, High, or Critical based on impact scope, data risk, and functionality impact. Applies to code-logic bugs, security vulnerabilities, performance issues, and any other bug type. Use during research and verification phases.
---

# Research Quality Measurement: Bug Severity Levels

This framework defines bug **severity** by assessing impact, regardless of bug type. It categorizes any issues discovered during analysis into four distinct levels based on three universal criteria: impact scope, data risk, and functionality implications. Apply this framework to any bug type (code-logic, security, performance, etc.).

---

## Severity Levels

### Low Severity

**Definition**: Issues with limited scope and low immediate impact. Users can continue working with workarounds available.

**Characteristics**:
- **Impact Scope**: Isolated to edge cases or specific user scenarios; affects a small subset of users or functionality
- **Data Risk**: No risk of data loss, corruption, or unauthorized access
- **Functionality**: Non-critical features affected; core functionality remains intact; users have clear workarounds

**Examples**: Cosmetic UI glitches, rarely-triggered edge cases, performance in non-critical paths, missing validation in uncommon workflows, incorrect behavior in edge conditions

---

### Medium Severity

**Definition**: Issues with moderate impact affecting some users or features. Needs fixing in a planned maintenance cycle.

**Characteristics**:
- **Impact Scope**: Affects a meaningful portion of users or multiple related features; reproducible and consistent
- **Data Risk**: Low risk of data loss; potential minor data inconsistencies that can be recovered or mitigated
- **Functionality**: Secondary or non-core features significantly impacted; workarounds are possible but cumbersome; users may experience degraded experience

**Examples**: Missing field validation, incorrect state transitions, weak comparison operators, feature degradation, incorrect calculations in secondary workflows, performance issues in standard use

---

### High Severity

**Definition**: Issues with widespread impact on core functionality or at-risk data. Requires immediate remediation.

**Characteristics**:
- **Impact Scope**: Affects a large portion of users or core functionality; reproducible in standard workflows
- **Data Risk**: Moderate risk of data loss or corruption; potential for unauthorized data access or exposure
- **Functionality**: Core features broken or severely compromised; no viable workarounds; users cannot complete critical tasks

**Examples**: Unvalidated state transitions, missing validation in core workflows, data corruption in main workflows, critical business logic failures, bypass of essential checks, significant performance degradation affecting usability

---

### Critical Severity

**Definition**: System-wide failures, security breaches, or data-at-risk scenarios. Requires emergency response and immediate deployment.

**Characteristics**:
- **Impact Scope**: Affects all or nearly all users; system-wide impact; reproducible consistently
- **Data Risk**: High risk of data loss, corruption, or breach; sensitive data exposure; compliance/legal implications
- **Functionality**: Core system functions are non-operational; complete feature failure; no recovery path for users

**Examples**: Complete system outage, widespread data corruption, total loss of data integrity, core system functions non-operational, incorrect data flow affecting all users, logic errors causing cascading failures throughout the system

---

## Using This Framework

When researching bugs in source code:

1. **Identify the bug** — reproduction steps, affected code path
2. **Assess impact scope** — How many users or features does this touch?
3. **Assess data risk** — Can data be lost, corrupted, or exposed?
4. **Assess functionality** — Does this break core workflows or edge cases?
5. **Classify severity** — Match the bug to the level above that best fits all three criteria

A bug belongs to a severity level when it meets **most** of the characteristics for that level across the three criteria. If in doubt between two levels, consider the **data risk** and **impact scope** first (they carry more weight than functionality).
