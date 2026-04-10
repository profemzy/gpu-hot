# GPU Hot — tests

This folder holds **unit tests** (Python + browser-style JS), **load-test / mock-cluster** tooling, and Docker definitions for both.

---

## Unit tests

Backend logic is covered with **pytest** (`tests/unit/`). Frontend **static JS** (charts, UI, WebSocket helpers, `app.js`) is covered with **Vitest** + **jsdom** (`tests/frontend/`).

| File | Role |
|------|------|
| `pytest.ini` | Pytest config (`testpaths = unit`, asyncio mode) |
| `package.json` | Vitest + jsdom; scripts: `npm test`, `npm run test:watch` |
| `vitest.config.js` | Vitest root = this directory; `frontend/setup.js` loads `static/js` under vm |
| `Dockerfile.unittest` | Image: Python deps + Node, runs pytest then Vitest |
| `docker-compose.unittest.yml` | Build/run the unittest image (context: repo root) |

From the **repository root**, the usual entry point is:

```bash
./run_tests.sh
```

That builds and runs `docker compose -f tests/docker-compose.unittest.yml` (same as a manual `docker compose … build` / `run`).

### Unit tests without Docker

Requires Python with `pytest`, `pytest-asyncio`, `httpx` (see `requirements.txt` + extras used in `Dockerfile.unittest`), and Node 18+.

```bash
# Backend
python -m pytest -c tests/pytest.ini

# Frontend (from repo root)
npm install --prefix tests
npm test --prefix tests
```

To show **Vitest** `console.*` output from app code (hidden by default), run:

```bash
VITEST_SILENT=0 npm test --prefix tests
```

---

## Load testing (mock cluster)

Simple load testing for multi-node GPU monitoring with realistic async patterns.

### Quick start

```bash
cd tests
docker compose -f docker-compose.test.yml up
```

Open http://localhost:1312 to see the dashboard.

### Architecture

- **FastAPI + AsyncIO**: async Python for mock nodes
- **Native WebSockets**: direct WebSocket protocol
- **Concurrent mock nodes**: multiple nodes in parallel
- **Realistic GPU patterns**: training-style utilization, warmup, validation

### Load test presets

Edit `docker-compose.test.yml` and uncomment the preset you want.

**LIGHT (3 nodes, 14 GPUs)** — development / quick runs:

```yaml
- NODES=2,4,8
- NODE_URLS=http://mock-cluster:13120,http://mock-cluster:13121,http://mock-cluster:13122
```

**MEDIUM (8 nodes, 64 GPUs)** — default-style medium cluster:

```yaml
- NODES=8,8,8,8,8,8,8,8
- NODE_URLS=http://mock-cluster:13120,...,http://mock-cluster:13127
```

**HEAVY (20 nodes, 160 GPUs)** — stress / large cluster:

```yaml
- NODES=8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8
- NODE_URLS=http://mock-cluster:13120,...,http://mock-cluster:13139
```

### What’s simulated

- Realistic GPU patterns (epochs, warmup, validation)
- Idle + busy GPUs (~40% utilization typical of many clusters)
- Stable memory, clock P-states, data-loading dips, temperature correlation

### Load-test files

| File | Role |
|------|------|
| `test_cluster.py` | Mock GPU node (FastAPI + AsyncIO) |
| `docker-compose.test.yml` | Stack + presets |
| `Dockerfile.test` | Image for mock nodes |

### Rebuild after changes

```bash
docker compose -f docker-compose.test.yml down
docker compose -f docker-compose.test.yml up --build
```

(Run these from the `tests/` directory, or pass `-f tests/docker-compose.test.yml` from the repo root.)
