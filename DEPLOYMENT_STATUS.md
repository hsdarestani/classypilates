# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `e0f52b36bad2260b95a4c8a128c097bccf4e7ea6`
- Checked at: `2026-09-22T19:14:11Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       50 seconds ago   Up 45 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago       Up 7 days (healthy)   5432/tcp
```
