# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `d08b52ecb1cdff240e50c69f7735c4315fdc8abb`
- Checked at: `2026-09-22T19:57:50Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Up About a minute     127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago           Up 7 days (healthy)   5432/tcp
```
