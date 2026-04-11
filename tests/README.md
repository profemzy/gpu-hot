# GPU Hot — tests

All tests are run from the **repository root** with:

```bash
./run_tests.sh
```

This builds and runs the unit-test Docker image (`docker compose -f tests/docker-compose.unittest.yml`), which executes **pytest** (backend) and **Vitest** (frontend) inside the container.

---

## What's tested

- **Backend** (pytest): Python logic in `tests/unit/`
- **Frontend** (Vitest + jsdom): Static JS (charts, UI, WebSocket helpers) in `tests/frontend/`

---

## Load testing (mock cluster)

A mock GPU cluster for manual load testing. Edit `docker-compose.test.yml` to choose a preset (LIGHT / MEDIUM / HEAVY), then:

```bash
cd tests
docker compose -f docker-compose.test.yml up --build
```

Open http://localhost:1312 to see the dashboard with simulated GPU nodes.
