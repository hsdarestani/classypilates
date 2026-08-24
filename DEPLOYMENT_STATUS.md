# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `ef509640c16a27458cf56fcb46a9c0de02b7d7b5`
- Checked at: `2026-08-24T12:28:44Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                    PORTS
classypilates-api-1   sha256:be05844fb7e9a9d6023ac4536df365e8a759b2ab964858bb49aea490b43fd5d3   "uvicorn main:app --…"   api       6 minutes ago    Up 6 minutes              127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        49 minutes ago   Up 49 minutes (healthy)   5432/tcp
```
