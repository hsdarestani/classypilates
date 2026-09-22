# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `a777491a8ec4ea17a363ce3cef1484ef62bab8b1`
- Checked at: `2026-09-22T20:16:54Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       37 seconds ago   Up 31 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago       Up 7 days (healthy)   5432/tcp
```
