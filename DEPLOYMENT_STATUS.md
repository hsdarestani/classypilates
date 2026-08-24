# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `16656c30f1abcb31225e168c29dc46d5f9b31d3a`
- Checked at: `2026-08-24T16:37:48Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       24 seconds ago   Up 22 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        5 hours ago      Up 5 hours (healthy)   5432/tcp
```
