# Vertisystem Applied AI Task 2 Spec

- **Status:** v0.1
- **Date:** August 5, 2026
- **Owner:** Achyutaram Sonti
- **Type:** Living implementation spec

---

## 1. Goal

Build a Python `3.12+` FastAPI microservice that maintains a globally consistent running sum across one or more service nodes.

The system must expose:

1. `POST /abacus/number`
   - request body: `{"number": N}`
   - effect: add integer `N` to the current running sum
2. `GET /abacus/sum`
   - effect: return the current running sum
3. `DELETE /abacus/sum`
   - effect: reset the running sum to `0`

This task is not mainly about wiring three endpoints. It is a test of whether the implementation can preserve correctness when multiple application nodes are serving requests concurrently.

---

## 2. Why This Exists

This task evaluates whether the implementation can demonstrate:

1. clean API design
2. deterministic state transitions
3. correctness under concurrency
4. consistency across multiple service nodes
5. realistic local demonstration of a distributed deployment shape

The submission should show deliberate engineering tradeoffs, especially around storage and consistency, not just a minimal FastAPI hello-world.

---

## 3. In Scope

### Functional Scope

1. FastAPI service with the three required endpoints
2. Integer addition to a shared running total
3. Read access to the current total
4. Reset behavior that sets the total to `0`
5. Validation of request payloads
6. Local demonstration of at least two service nodes sharing the same authoritative state
7. Terminal-friendly startup and demo workflow

### Engineering Scope

1. Shared storage suitable for multi-node correctness
2. Explicit consistency model for reads and writes
3. Automated tests for endpoint behavior
4. Automated tests for concurrent update correctness
5. BDD-style acceptance scenarios for single-node and multi-node behavior
6. Local run instructions for one-node and two-node demos

---

## 4. Out of Scope

1. Authentication or authorization
2. Multi-tenant separation
3. Arbitrary numeric types such as floats or decimals
4. Historical reporting beyond what is required to maintain correctness
5. WAN-distributed database replication
6. Auto-scaling or container orchestration beyond a local two-node simulation
7. Exactly-once delivery across client retries

If a feature does not help demonstrate correctness, consistency, or local multi-node operation, it is out of scope for V1.

---

## 5. Product Principles

1. **Correctness over cleverness**
   - The running total must remain correct under concurrent writes.
2. **Single source of truth**
   - No node-local in-memory sum may be treated as authoritative.
3. **Consistency over stale-read optimization**
   - Reads should come from the authoritative store, not from caches or replicas.
4. **Deterministic state transitions**
   - A successful `POST` or `DELETE` must correspond to one committed state change.
5. **Demoable**
   - Two local service nodes must be easy to run and inspect from a terminal.

---

## 6. Proposed V1 Architecture

```text
Client
  ->
FastAPI Node A / Node B / Node N
  ->
Abacus Service Layer
  ->
Transactional Repository
  ->
Shared Authoritative Database
```

### 6.1 Service Nodes

Each FastAPI node:

1. is stateless
2. exposes the same HTTP API
3. talks to the same backing store
4. must produce the same observed sum as every other node after committed writes

### 6.2 Shared Storage

V1 should use a strongly consistent relational store, with PostgreSQL as the target implementation.

Rationale:

1. supports atomic updates
2. supports row-level locking and transactions
3. is easy to run locally for a two-node demo
4. is a more defensible choice for correctness than per-node memory or eventual-consistency caches

### 6.3 Data Model

V1 uses a **single-state row** as the authoritative representation.

Required shape:

1. one table named `abacus_state`
2. one authoritative row identified by `state_id = 1`
3. one `current_sum` column stored as signed `BIGINT`

Suggested schema:

```sql
CREATE TABLE IF NOT EXISTS abacus_state (
  state_id SMALLINT PRIMARY KEY CHECK (state_id = 1),
  current_sum BIGINT NOT NULL
);
```

Rationale:

1. keeps the state model simple and inspectable
2. supports atomic in-place updates
3. avoids unnecessary aggregation logic in V1
4. is sufficient for the take-home consistency requirement

### 6.4 Transaction Model

V1 uses ordinary database transactions with PostgreSQL `READ COMMITTED` isolation.

Reasoning:

1. atomic `UPDATE ... RETURNING` on a single authoritative row is sufficient for correct increments and resets
2. PostgreSQL row-level locking naturally serializes conflicting writes to the same row
3. `SERIALIZABLE` would add complexity and retry logic without improving the core single-row correctness story for V1

---

## 7. Consistency Model

The service should strive for maximum consistency for the sum API.

For V1, the target behavior is:

1. every successful `POST /abacus/number` is applied exactly once by the server for that accepted request
2. every successful `DELETE /abacus/sum` resets the total to `0`
3. successful writes have a single committed order at the database layer
4. `GET /abacus/sum` returns the latest committed total from the authoritative store
5. all nodes observe the same total once a write is committed

### 7.1 Practical Interpretation

The service aims for **single-primary strong consistency** rather than eventual consistency.

That implies:

1. no node-local caching of the sum
2. no read replicas in V1
3. no asynchronous replication path in the request-serving data flow
4. reads and writes go to the same authoritative database

### 7.2 Concurrency Rule

Concurrent `POST` and `DELETE` operations must produce a result equivalent to some serial order of committed transactions.

Example:

1. current total is `10`
2. one request adds `5`
3. one request resets the sum
4. valid final totals are only those explained by commit order:
   - `0` if reset commits last
   - `5` if reset commits first and add commits second

The system must not produce impossible intermediate corruption such as lost updates.

---

## 8. API Contracts

### 8.1 `POST /abacus/number`

Request:

```json
{
  "number": 7
}
```

Behavior:

1. validate that `number` is an integer
2. add `number` to the current total atomically
3. return a structured success response

Suggested V1 response:

```json
{
  "sum": 18
}
```

V1 response contract:

1. return only `{"sum": N}`
2. do not include node id, hostname, version, timestamps, or operation metadata in the JSON body
3. the returned `sum` reflects the committed value after the write succeeds

Status codes:

1. `200 OK` on success
2. `422 Unprocessable Entity` for invalid payload shape or type
3. `409 Conflict` if applying the number would overflow the supported `BIGINT` sum range
4. `500` class errors only for unexpected service failures

### 8.2 `GET /abacus/sum`

Behavior:

1. read the current total from the authoritative store
2. return the current sum

Suggested V1 response:

```json
{
  "sum": 18
}
```

V1 response contract:

1. return only `{"sum": N}`
2. the returned `sum` comes directly from the authoritative store
3. the service must not decorate the payload with node-specific metadata

Status codes:

1. `200 OK` on success

### 8.3 `DELETE /abacus/sum`

Behavior:

1. reset the current sum to `0` atomically
2. return the resulting sum

Suggested V1 response:

```json
{
  "sum": 0
}
```

V1 response contract:

1. return only `{"sum": 0}` after a successful reset
2. the response reflects the committed post-reset value

Status codes:

1. `200 OK` on success

---

## 9. Validation Rules

1. `number` must be present in the POST body
2. `number` must be a strict JSON integer
3. booleans are invalid, even though Python treats `bool` as a subtype of `int`
4. floats, strings, objects, and arrays are invalid for V1
5. negative integers are allowed
6. request values must fit within signed `BIGINT` range

V1 allows negative integers because the task says “adds a number N,” not “adds a positive number only.”

If a syntactically valid request would cause the stored running total to overflow signed `BIGINT`, the service must:

1. reject the operation with `409 Conflict`
2. leave the authoritative sum unchanged

---

## 10. Failure Handling

1. malformed input must not mutate state
2. failed transactions must not partially apply
3. a node crash must not leave the sum in an indeterminate state
4. transient infrastructure failures may return errors, but must not silently lose committed updates
5. if the authoritative database is unavailable, the service must fail the request rather than serve stale or node-local fallback state

---

## 11. Local Two-Node Demo Requirement

The implementation must be demonstrable locally in a terminal with at least two service nodes.

The target demo shape is:

1. one shared PostgreSQL instance
2. two FastAPI processes bound to different ports
3. requests sent to both nodes
4. both nodes returning the same total after writes
5. one terminal-friendly startup method, preferably `docker compose` for the database plus two separate app commands

Example:

```text
Node A -> localhost:8001
Node B -> localhost:8002
DB     -> localhost:5432
```

The demo should prove that:

1. a `POST` sent to Node A is visible through `GET` on Node B
2. a `DELETE` sent to Node B is visible through `GET` on Node A
3. concurrent POSTs across both nodes still produce the correct sum

---

## 12. Testing Strategy

### 12.1 Unit / Service-Level Tests

Must cover:

1. add operation updates the total correctly
2. reset operation sets the total to `0`
3. invalid payloads are rejected
4. negative-number behavior is correct and documented

### 12.2 API Tests

Must cover:

1. `POST /abacus/number`
2. `GET /abacus/sum`
3. `DELETE /abacus/sum`
4. status codes and response bodies

### 12.3 Concurrency Tests

Must cover:

1. many concurrent POSTs against one node
2. many concurrent POSTs spread across two nodes
3. final total equals the mathematical sum of accepted writes
4. reset semantics under concurrent access are deterministic and documented

### 12.4 Acceptance Tests

BDD scenarios should cover:

1. initial state
2. additive behavior
3. reset behavior
4. validation behavior
5. multi-node visibility
6. concurrent correctness

---

## 13. Initial Implementation Direction

The preferred V1 design is:

1. FastAPI app for HTTP transport
2. sync SQLAlchemy database layer with a synchronous PostgreSQL driver
3. PostgreSQL backing store
4. one authoritative `abacus_state` row initialized to `0`
5. atomic SQL update for increment
6. atomic SQL update for reset
7. strict Pydantic request/response models
8. no node-local caching

Route shape:

1. `POST /abacus/number` implemented as a synchronous route handler
2. `GET /abacus/sum` implemented as a synchronous route handler
3. `DELETE /abacus/sum` implemented as a synchronous route handler

Schema/bootstrap shape:

1. V1 will bootstrap schema automatically on startup
2. bootstrap must be idempotent across multiple nodes
3. the singleton row must be created with an upsert-style guard such as `INSERT ... ON CONFLICT DO NOTHING`
4. startup bootstrap is acceptable for the take-home and avoids requiring a separate migration step

Example implementation shape:

```sql
UPDATE abacus_state
SET current_sum = current_sum + :number
WHERE state_id = 1
RETURNING current_sum;
```

This direction is intentionally simple. The point is to maximize correctness and explainability before optimizing throughput.

---

## 14. Ambiguity Resolution Log

### 14.1 Question 1

Should V1 use sync SQLAlchemy or async SQLAlchemy?

Decision:

Use **sync SQLAlchemy** in V1.

Reasoning:

1. the target load of `10-1000` POST requests per minute does not require async complexity
2. sync transaction handling is simpler to reason about for a consistency-focused take-home
3. sync code keeps the service, tests, and two-node local demo easier to debug from the terminal
4. the core evaluation point is correctness across nodes, not maximizing single-process throughput

Implication:

1. FastAPI route handlers may remain ordinary `def` handlers in V1
2. the repository layer should use straightforward transaction boundaries
3. async I/O can be deferred unless a later requirement proves it necessary

---

### 14.2 Question 2

Should the API response include only `sum`, or should it also include metadata such as node id or operation type?

Decision:

Return only `{"sum": N}` in V1.

Reasoning:

1. it matches the task statement cleanly
2. it keeps the API contract small and easy to test
3. it avoids mixing debugging concerns into the correctness contract
4. multi-node behavior should be demonstrated through routing requests to different nodes, not by embedding node identity into core responses

### 14.3 Question 3

Should V1 expose a separate health endpoint?

Decision:

Do **not** add a separate health endpoint in V1.

Reasoning:

1. the assignment only requires the three abacus endpoints
2. adding extra endpoints increases scope without improving the consistency story
3. `GET /abacus/sum` is sufficient to verify node readiness during the demo

### 14.4 Question 4

Should V1 require a separate migration/init step, or should schema setup happen automatically?

Decision:

Use automatic, idempotent schema bootstrap on startup in V1.

Reasoning:

1. it reduces setup friction for the take-home reviewer
2. it keeps the local two-node demo reproducible from the terminal
3. PostgreSQL supports idempotent table creation and guarded singleton-row initialization
4. a full migration toolchain would add ceremony without increasing confidence for this bounded service

### 14.5 Question 5

Should `number` accept loose integer-like values such as booleans or numeric strings?

Decision:

Use strict integer validation only.

Reasoning:

1. hidden coercion weakens the API contract
2. rejecting booleans avoids a common Python/Pydantic footgun
3. explicit validation makes failure cases deterministic

### 14.6 Question 6

Should V1 use a ledger/event-log model or a single authoritative state row?

Decision:

Use a single authoritative state row in V1.

Reasoning:

1. it is the simplest structure that satisfies the required consistency guarantees
2. it minimizes implementation surface area
3. it keeps concurrent correctness explainable in an interview setting

### 14.7 Question 7

What should happen if the database is unavailable?

Decision:

Fail requests rather than falling back to in-memory state or stale cached reads.

Reasoning:

1. consistency matters more than availability for this assignment
2. any fallback local state would break the cross-node correctness model
3. explicit failure is safer and more honest than returning potentially incorrect sums

---

## 15. V1 Is Now Fully Specified

There are no intentionally unresolved V1 ambiguities remaining in this spec.

Future iterations may still extend the system, but V1 implementation should not need product-level guesswork about:

1. storage model
2. consistency model
3. validation strictness
4. response shape
5. bootstrap strategy
6. multi-node demo shape

---

## 16. Success Criteria

Task 2 is complete when:

1. the three endpoints behave correctly on one node
2. concurrent POST load does not lose updates
3. two local nodes can be run in separate terminals against the same store
4. GET returns the correct shared total regardless of which node is queried
5. DELETE resets the shared total across nodes
6. automated tests cover core API and concurrency behavior
7. the README explains how to run and demonstrate the service locally
