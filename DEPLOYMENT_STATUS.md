# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `b7b29a6e6e9c3b15a0e97b42c3df1314ca667800`
- Checked at: `2026-09-13T17:20:41Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       23 seconds ago   Up 22 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
