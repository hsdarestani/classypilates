# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `53c1d49f89825a346a54065642e26a2563c227b9`
- Checked at: `2026-09-22T20:21:49Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       28 seconds ago   Up 24 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago       Up 7 days (healthy)   5432/tcp
```
