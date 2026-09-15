# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `3517219daf65bdd066235f76fad0bb6312ad948a`
- Checked at: `2026-09-15T14:12:16Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       51 seconds ago   Up 40 seconds           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        17 hours ago     Up 17 hours (healthy)   5432/tcp
```
