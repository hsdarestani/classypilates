# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `ce50863ff3e0c2dd6d73fe144a19b47eb8e7cace`
- Checked at: `2026-09-22T17:32:55Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                PORTS
classypilates-api-1   sha256:78930d6f03a4012028e0c07aa32fea98c8182f157115406f9878ae6c179939d0   "uvicorn runtime_app…"   api       6 minutes ago   Up 6 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        7 days ago      Up 7 days (healthy)   5432/tcp
```
