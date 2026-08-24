# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `cdfe6c84e1f35f83a1b38f7d1a8300e5b9fa4c59`
- Checked at: `2026-08-24T11:42:47Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                   PORTS
classypilates-api-1   sha256:a5af378562bf373668974c4a4437d130e1ca0ad8af15df3b3fef0feadd013117   "uvicorn main:app --…"   api       3 minutes ago   Up 3 minutes             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        3 minutes ago   Up 3 minutes (healthy)   5432/tcp
```
