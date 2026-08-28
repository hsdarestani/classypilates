# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `3b046b9b03797b66b485201091be241f5d824c48`
- Checked at: `2026-08-28T08:22:20Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   sha256:268d51cca2a1aed37517f617307c33cf627bd99d697ce82056b8975d5236fd30   "uvicorn runtime_app…"   api       23 minutes ago   Up 23 minutes         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        3 days ago       Up 3 days (healthy)   5432/tcp
```
