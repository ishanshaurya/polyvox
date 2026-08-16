# PolyVox web

Vite + React shell for the product UI.

## Run (API must be up)

```bash
# terminal 1
cd apps/api && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# terminal 2
cd apps/web && npm install && npm run dev
```

Open http://127.0.0.1:5173

Upload designs to `design/` before investing in full visual polish.
