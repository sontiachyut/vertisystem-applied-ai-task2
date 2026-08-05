# Vertisystem Applied AI Task 2

This repository contains Task 2 of the take-home:

- a FastAPI microservice
- a shared running sum
- correctness across multiple service nodes

The service exposes:

- `POST /abacus/number` with `{"number": N}`
- `GET /abacus/sum`
- `DELETE /abacus/sum`

## Reviewer Quick Start

If you only want the shortest path to verify the submission:

1. Create and activate a Python `3.12` virtual environment.
2. Install the project with dev dependencies.
3. Run the tests.
4. If you want the multi-node demo, start PostgreSQL and run two nodes.

macOS / Linux:

```bash
cd /path/to/vertisystem-applied-ai-task2
python3.12 -m venv .venv312
source .venv312/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest tests
```

Windows PowerShell:

```powershell
cd C:\path\to\vertisystem-applied-ai-task2
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest tests
```

## Requirements

- Python `3.12+`
- `docker compose` only if you want the PostgreSQL-backed two-node demo
- compatible with macOS, Linux, and Windows

## Windows Notes

The code is ordinary Python and is intended to run on Windows as well.

The main differences on Windows are:

1. use `py -3.12` instead of `python3.12`
2. activate the virtual environment with `.\.venv312\Scripts\Activate.ps1`
3. set environment variables with `$env:NAME="value"` in PowerShell

If PowerShell blocks activation, run this once in that terminal and then try again:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## Design Boundary

This service is deliberately simple and consistency-first.

V1 uses:

- stateless FastAPI service nodes
- a shared authoritative database
- one authoritative `abacus_state` row
- atomic increment and reset operations
- strict integer validation
- no node-local in-memory authoritative sum

That means:

- every node reads and writes the same backing state
- a write accepted on Node A is visible from Node B after commit
- the JSON response stays intentionally small: `{"sum": N}`

## API

### `POST /abacus/number`

Request:

```json
{"number": 7}
```

Success response:

```json
{"sum": 18}
```

### `GET /abacus/sum`

Success response:

```json
{"sum": 18}
```

### `DELETE /abacus/sum`

Success response:

```json
{"sum": 0}
```

## Project Layout

```text
applied_ai_abacus/
features/
  task2_abacus.feature
tests/
task2_spec.md
docker-compose.task2.yml
```

## Fastest Verification Path

Run the automated tests:

```bash
python -m pytest tests
```

The test suite covers:

- endpoint behavior
- strict validation
- overflow rejection
- reset behavior
- shared-state visibility across two nodes
- concurrent update correctness

Note:

- the automated tests use temporary SQLite databases for fast local verification
- the live two-node demo target is PostgreSQL, matching `task2_spec.md`

## Two-Node Local Demo

This is the simplest reviewer flow:

1. start PostgreSQL
2. start Node A on port `8001`
3. start Node B on port `8002`
4. send a write to one node
5. confirm the other node sees the same sum
6. reset on one node and confirm the reset is visible from the other

Start PostgreSQL:

```bash
docker compose -f docker-compose.task2.yml up -d
```

Start Node A in one terminal.

macOS / Linux:

```bash
cd /path/to/vertisystem-applied-ai-task2
source .venv312/bin/activate
python -m applied_ai_abacus.main --port 8001
```

Windows PowerShell:

```powershell
cd C:\path\to\vertisystem-applied-ai-task2
.\.venv312\Scripts\Activate.ps1
python -m applied_ai_abacus.main --port 8001
```

Start Node B in another terminal.

macOS / Linux:

```bash
cd /path/to/vertisystem-applied-ai-task2
source .venv312/bin/activate
python -m applied_ai_abacus.main --port 8002
```

Windows PowerShell:

```powershell
cd C:\path\to\vertisystem-applied-ai-task2
.\.venv312\Scripts\Activate.ps1
python -m applied_ai_abacus.main --port 8002
```

Default database URL:

```text
postgresql+psycopg://abacus:abacus@127.0.0.1:5432/abacus
```

Optional override:

macOS / Linux:

```bash
export ABACUS_DATABASE_URL='postgresql+psycopg://abacus:abacus@127.0.0.1:5432/abacus'
```

Windows PowerShell:

```powershell
$env:ABACUS_DATABASE_URL='postgresql+psycopg://abacus:abacus@127.0.0.1:5432/abacus'
```

## Manual Demo Commands

macOS / Linux examples:

Initial read from Node A:

```bash
curl -s http://127.0.0.1:8001/abacus/sum
```

Write through Node A:

```bash
curl -s -X POST http://127.0.0.1:8001/abacus/number \
  -H 'Content-Type: application/json' \
  -d '{"number": 5}'
```

Read through Node B:

```bash
curl -s http://127.0.0.1:8002/abacus/sum
```

Reset through Node B:

```bash
curl -s -X DELETE http://127.0.0.1:8002/abacus/sum
```

Read through Node A again:

```bash
curl -s http://127.0.0.1:8001/abacus/sum
```

Windows PowerShell examples:

Initial read from Node A:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8001/abacus/sum
```

Write through Node A:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/abacus/number -ContentType "application/json" -Body '{"number":5}'
```

Read through Node B:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8002/abacus/sum
```

Reset through Node B:

```powershell
Invoke-RestMethod -Method Delete -Uri http://127.0.0.1:8002/abacus/sum
```

Read through Node A again:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8001/abacus/sum
```

Expected result:

- a write to Node A is visible from Node B
- a reset on Node B is visible from Node A

## Concurrent Smoke Check

macOS / Linux:

```bash
for i in $(seq 1 50); do
  curl -s -X POST http://127.0.0.1:8001/abacus/number -H 'Content-Type: application/json' -d '{"number":1}' >/dev/null &
  curl -s -X POST http://127.0.0.1:8002/abacus/number -H 'Content-Type: application/json' -d '{"number":1}' >/dev/null &
done
wait
curl -s http://127.0.0.1:8001/abacus/sum
```

Windows PowerShell:

```powershell
1..50 | ForEach-Object {
    Start-Job { Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/abacus/number -ContentType "application/json" -Body '{"number":1}' } | Out-Null
    Start-Job { Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8002/abacus/number -ContentType "application/json" -Body '{"number":1}' } | Out-Null
}
Get-Job | Wait-Job | Out-Null
Get-Job | Remove-Job
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8001/abacus/sum
```

Expected result:

- final sum is `{"sum":100}`

## Screenshots

These are real screenshots from a live local Task 2 run.

- [Tests and Docker setup](screenshots/task2/task2-tests-and-docker-setup.png)
- [Node B live service log](screenshots/task2/task2-node-b-live.png)
- [Cross-node API checks](screenshots/task2/task2-cross-node-checks.png)
- [Concurrent smoke check](screenshots/task2/task2-concurrency-smoke-check.png)

Tests and Docker setup:

![Task 2 tests and Docker setup](screenshots/task2/task2-tests-and-docker-setup.png)

Node B live service log:

![Task 2 Node B live service log](screenshots/task2/task2-node-b-live.png)

Cross-node API checks:

![Task 2 cross-node API checks](screenshots/task2/task2-cross-node-checks.png)

Concurrent smoke check:

![Task 2 concurrent smoke check](screenshots/task2/task2-concurrency-smoke-check.png)

## Files to Review

- `task2_spec.md`
- `features/task2_abacus.feature`
- `applied_ai_abacus/`
- `tests/`

## Known Notes

- automated tests use SQLite for speed and local repeatability
- the live multi-node demo target is PostgreSQL
- the service aims for strong consistency through a single authoritative database, not eventual consistency through node-local caches
