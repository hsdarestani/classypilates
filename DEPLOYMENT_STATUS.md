# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `9fce163397ee37c5714a55b1cbdba7a3bcdb38dd`
- Checked at: `2026-09-09T19:48:10Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       24 seconds ago   Up 22 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
