# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `cff1ec6d8a689981a799965f03a2a6a8e4a4d676`
- Checked at: `2026-09-22T21:02:49Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       33 seconds ago   Up 28 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        8 days ago       Up 8 days (healthy)   5432/tcp
```
