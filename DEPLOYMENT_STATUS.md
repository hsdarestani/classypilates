# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `c09a1497bf73bfeb411e25321d60c360c495311d`
- Checked at: `2026-09-15T13:31:31Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Up 51 seconds           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        16 hours ago         Up 16 hours (healthy)   5432/tcp
```
