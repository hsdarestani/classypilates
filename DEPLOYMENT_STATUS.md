# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `e0f27f2462af052af5dae7b4c1fed5267b0a0c34`
- Checked at: `2026-09-15T11:06:05Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       58 seconds ago   Up 45 seconds           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        14 hours ago     Up 14 hours (healthy)   5432/tcp
```
