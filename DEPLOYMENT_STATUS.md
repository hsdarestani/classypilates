# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `fbaff8f3694d16a94c27df18ece56298555432a3`
- Checked at: `2026-08-24T15:34:25Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       20 seconds ago   Up 19 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        4 hours ago      Up 4 hours (healthy)   5432/tcp
```
