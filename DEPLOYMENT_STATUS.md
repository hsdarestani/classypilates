# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `ca4d3156e1416aed2ba89341f1dfacabc3f6e7fa`
- Checked at: `2026-09-22T20:11:16Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Up 59 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago           Up 7 days (healthy)   5432/tcp
```
