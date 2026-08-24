# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `d87db55b42050143606489bde4dc968d3ded066e`
- Checked at: `2026-08-24T12:25:51Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                    PORTS
classypilates-api-1   sha256:be05844fb7e9a9d6023ac4536df365e8a759b2ab964858bb49aea490b43fd5d3   "uvicorn main:app --…"   api       3 minutes ago    Up 3 minutes              127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        46 minutes ago   Up 46 minutes (healthy)   5432/tcp
```
