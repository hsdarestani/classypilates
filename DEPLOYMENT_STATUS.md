# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `df25f3c4ad69e88162fd64f1ab01393579fa764d`
- Checked at: `2026-09-22T21:35:40Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                PORTS
classypilates-api-1   sha256:0793d2b1a7693fe29826699f3da2d7d6bec9d0d3c0472113b6301cd637d71339   "uvicorn runtime_app…"   api       2 minutes ago   Up 2 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        8 days ago      Up 8 days (healthy)   5432/tcp
```
