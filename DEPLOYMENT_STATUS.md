# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `614ddcc5b5d16db43e361cf80b2e070bd1c32d1f`
- Checked at: `2026-08-24T16:07:06Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:7989e862e6601eb7843ac78569b4b6ceb8a682fa4867fbe940aea981b08195dc   "uvicorn main:app --…"   api       5 minutes ago   Up 5 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        4 hours ago     Up 4 hours (healthy)   5432/tcp
```
