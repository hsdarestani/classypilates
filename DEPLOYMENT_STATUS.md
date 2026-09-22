# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `1654e52bc14e1d2886c2cf2dd84fd0db62113bd8`
- Checked at: `2026-09-22T20:05:25Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED         STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       2 minutes ago   Up 2 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago      Up 7 days (healthy)   5432/tcp
```
