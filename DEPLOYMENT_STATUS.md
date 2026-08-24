# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `b9b76590c8309d337ed7a52e29cf192770e708f1`
- Checked at: `2026-08-24T12:42:53Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED             STATUS                       PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       17 seconds ago      Up 16 seconds                127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        About an hour ago   Up About an hour (healthy)   5432/tcp
```
