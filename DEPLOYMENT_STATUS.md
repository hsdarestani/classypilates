# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `23d7ebfbfe7224e9591c28dd7403e9da64cc20cf`
- Checked at: `2026-08-27T19:23:47Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       23 seconds ago   Up 21 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        3 days ago       Up 3 days (healthy)   5432/tcp
```
