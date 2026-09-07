# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `0be05d09534fb4e855b28da9061c99d4c39f50db`
- Checked at: `2026-09-07T23:08:49Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:8444d4e4dada7c98d9ffd66d83a583a9d13feb85811bad795032c2d78952a593   "uvicorn runtime_app…"   api       3 minutes ago   Up 3 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
