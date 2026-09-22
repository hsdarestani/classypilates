# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `eeabfa6abc73f539a1ef6050521e859d5f58e43c`
- Checked at: `2026-09-22T19:41:28Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       46 seconds ago   Up 43 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago       Up 7 days (healthy)   5432/tcp
```
