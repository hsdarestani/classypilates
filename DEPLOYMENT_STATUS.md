# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `e5d158b3ddd897651aa0481aebfa364b2cc1ae04`
- Checked at: `2026-09-15T09:39:15Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Up 58 seconds           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        12 hours ago         Up 12 hours (healthy)   5432/tcp
```
