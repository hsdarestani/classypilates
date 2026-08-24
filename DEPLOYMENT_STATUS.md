# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `c106ce596f9ec96504a2dc3f398c897e43ec9637`
- Checked at: `2026-08-24T12:24:04Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED              STATUS                    PORTS
classypilates-api-1   sha256:be05844fb7e9a9d6023ac4536df365e8a759b2ab964858bb49aea490b43fd5d3   "uvicorn main:app --…"   api       About a minute ago   Up About a minute         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        44 minutes ago       Up 44 minutes (healthy)   5432/tcp
```
