# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `fb13652b2251ee358c41575ad49341bbcaf387b1`
- Checked at: `2026-09-22T20:29:25Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       31 seconds ago   Up 27 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago       Up 7 days (healthy)   5432/tcp
```
