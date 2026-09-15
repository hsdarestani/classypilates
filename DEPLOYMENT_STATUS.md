# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `2bd5e0f1ffe89ec7437c22276ae3ef38cac6cc14`
- Checked at: `2026-09-15T10:07:40Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       57 seconds ago   Up 54 seconds           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        13 hours ago     Up 13 hours (healthy)   5432/tcp
```
