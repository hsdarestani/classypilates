# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `10a48fb362f56bbf31471d8920b95bb18c11be81`
- Checked at: `2026-09-07T23:04:35Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:3b6355f6f07b8ddc790ef281ac6319ed4a0287e0473a6f5e97529289a72d333b   "uvicorn runtime_app…"   api       6 minutes ago   Up 6 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
