# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `b365d8586a8aa38ca256784a3606f3bf9a26e108`
- Checked at: `2026-08-24T15:57:38Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       19 seconds ago   Up 18 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        4 hours ago      Up 4 hours (healthy)   5432/tcp
```
