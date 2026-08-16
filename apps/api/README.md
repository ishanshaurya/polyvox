# PolyVox API

White-glove product API. See `docs/HOSTING.md`, `docs/PLAN.md`.

## Run

```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs

## Endpoints (v1)

- `POST /v1/projects` — create engagement + workspace + DB row
- `GET /v1/projects`, `GET /v1/projects/{id}`
- `POST /v1/projects/{id}/cdr` — upload CDR file
- `POST /v1/projects/{id}/recordings` — upload `.mp3` or `.zip`
- `POST /v1/projects/{id}/run?step=all` — queue/run worker
- `GET /v1/projects/{id}/jobs`
- `GET /v1/projects/{id}/calls`, `GET /v1/calls/{id}`
- `GET /v1/projects/{id}/export.xlsx`
- `GET /v1/rubrics`
- `POST /v1/projects/{id}/purge-media`

SQLite DB default: `POLYVOX_DATABASE_URL=sqlite:///./.polyvox_data/polyvox.db`
