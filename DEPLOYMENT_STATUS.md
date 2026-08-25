# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `e519e19abf2a728f4ca4b74a7419d88ce7efded8`
- Checked at: `2026-08-25T07:20:37Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       22 seconds ago   Up 20 seconds           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        20 hours ago     Up 20 hours (healthy)   5432/tcp
```
