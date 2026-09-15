# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `8fcb41cb9b65cabea9e285de59dc92db3de402ef`
- Checked at: `2026-09-15T10:05:03Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       53 seconds ago   Up 41 seconds           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        13 hours ago     Up 13 hours (healthy)   5432/tcp
```
