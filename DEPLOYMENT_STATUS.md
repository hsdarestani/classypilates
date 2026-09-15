# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `96d47d7be6a43bd23706d046d31682e3e19c3b37`
- Checked at: `2026-09-15T18:49:58Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED        STATUS                  PORTS
classypilates-api-1   sha256:af782fe46107acd3a76025e3aeb582e5bee31fd1a596265e1d159d7fd63495f1   "uvicorn runtime_app…"   api       2 hours ago    Up 2 hours              127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        21 hours ago   Up 21 hours (healthy)   5432/tcp
```
