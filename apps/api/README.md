# PolyVox API

White-glove product API scaffold. See `docs/HOSTING.md` and `docs/ARCHITECTURE.md`.

## Run

```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs

## Endpoints (v0)

- `GET /health`
- `POST /v1/projects` — create engagement + local workspace
- `GET /v1/projects`
- `GET /v1/projects/{id}`
- `POST /v1/projects/{id}/mark/{status}` — created|ingested|running|ready|purged

Project workspaces are created under `POLYVOX_DATA_ROOT` (default `./.polyvox_data`).
