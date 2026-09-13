# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `0ea4913eacca13ee5284496e84b0dbbc8861d97e`
- Checked at: `2026-09-13T11:19:33Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:97acff7d0d066c60ddf49d9832c201ed7d434736da8355b32e3625984d83973e   "uvicorn runtime_app…"   api       9 minutes ago   Up 9 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
