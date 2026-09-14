# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `c2595dc3b748834037245c3a20dbd6b9a827c4c2`
- Checked at: `2026-09-14T14:30:43Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED        STATUS                 PORTS
classypilates-api-1   sha256:43df65ed03b6cd118a21fc5097a4b7f81c60de31f1d229d36ed28afd409cb7aa   "uvicorn runtime_app…"   api       20 hours ago   Up 20 hours            127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        3 weeks ago    Up 3 weeks (healthy)   5432/tcp
```
