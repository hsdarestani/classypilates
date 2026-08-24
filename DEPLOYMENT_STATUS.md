# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `aa93a69cebe5c6ccddd6309ae6e931df34d29e92`
- Checked at: `2026-08-24T15:03:04Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       13 seconds ago   Up 12 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        3 hours ago      Up 3 hours (healthy)   5432/tcp
```
