# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `33147f22714894d6b936e83317ebb2698c1c793e`
- Checked at: `2026-09-22T17:43:36Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       46 seconds ago   Up 40 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago       Up 7 days (healthy)   5432/tcp
```
