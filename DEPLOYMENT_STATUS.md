# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `7ffa36d926810a256da587014f78fc08b44ae886`
- Checked at: `2026-09-15T13:23:50Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       40 seconds ago   Up 37 seconds           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        16 hours ago     Up 16 hours (healthy)   5432/tcp
```
