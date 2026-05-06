---
name: immortal-skill
description: Implement resilient, long-lived code patterns that remain maintainable and robust over time. Use when the user wants to write durable Swift/SwiftUI code, introduce battle-tested architectural patterns, or refactor fragile code to be more resilient.
---

# Immortal Skill

Guide the user in writing resilient, maintainable code that stands the test of time — avoiding common pitfalls that lead to fragile or short-lived implementations.

## Principles

1. **Prefer composition over inheritance** — favour small, focused types that combine cleanly.
2. **Make illegal states unrepresentable** — encode invariants in the type system so the compiler enforces correctness.
3. **Explicit over implicit** — avoid hidden side effects; every action should be traceable.
4. **Single source of truth** — one authoritative location for each piece of state.
5. **Fail fast and loudly in debug, gracefully in production** — use `assert`/`precondition` during development; handle errors at boundaries in release builds.

## Workflow

Make a todo list for all the tasks in this workflow and work on them one after another.

### 1. Understand the target code

Read the file(s) the user wants to improve. Identify:
- Fragile patterns (force unwraps, implicit coupling, deep inheritance chains)
- Hidden state or side effects
- Duplicated logic that could become a single source of truth

### 2. Design the resilient alternative

Propose a concrete alternative using one or more of these patterns:

**Value types for data**
```swift
struct User: Equatable {
    let id: UUID
    var name: String
}
```

**Enums for finite states**
```swift
enum LoadState<T> {
    case idle
    case loading
    case loaded(T)
    case failed(Error)
}
```

**Protocol-based dependencies (for testability)**
```swift
protocol DataStore {
    func fetch(id: UUID) async throws -> User
}
```

**Result / async-throws at boundaries**
```swift
func loadUser(id: UUID) async throws -> User {
    try await store.fetch(id: id)
}
```

### 3. Apply the changes

Edit only what needs changing. Do not refactor surrounding code that is out of scope.

### 4. Validate

Run the project's test suite (if available):
```bash
xcodebuild test -scheme <scheme> -destination 'platform=iOS Simulator,name=iPhone 16'
```

If no tests exist, confirm the project still builds:
```bash
xcodebuild build -scheme <scheme> -destination 'platform=iOS Simulator,name=iPhone 16'
```

### 5. Commit

Create a focused commit describing what fragility was addressed and why.

## Wrap up

Summarise:
- What patterns were introduced and why they are more resilient
- Any trade-offs the user should be aware of
- Suggested next steps (e.g., adding tests to lock in the new behaviour)
