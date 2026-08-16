# PolyVox worker

Stub entrypoint for white-glove pipeline runs against a project workspace.

```bash
python apps/worker/main.py --project-workspace .polyvox_data/projects/<id> --step all
```

Will later call `packages/callqa` with per-project paths (no shared Rainbow `config.yaml` defaults).
