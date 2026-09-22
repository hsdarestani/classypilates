# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `9dcd63e98354216b991b413cd32c3c25fd8051bb`
- Checked at: `2026-09-22T20:43:21Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       34 seconds ago   Up 30 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago       Up 7 days (healthy)   5432/tcp
```
