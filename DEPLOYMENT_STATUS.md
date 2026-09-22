# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `e4d8d538b8b3a862989aab0cb13bc6222c90af14`
- Checked at: `2026-09-22T19:18:50Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Up About a minute     127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago           Up 7 days (healthy)   5432/tcp
```
