# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `eec593019078a520ae8ab817824f498ea54e36bf`
- Checked at: `2026-09-22T20:59:39Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED              STATUS                PORTS
classypilates-api-1   sha256:cdd387ad5a985252f3e350558fe43fd9a9161ed94505cf8bff16f7e9488b7397   "uvicorn runtime_app…"   api       About a minute ago   Up About a minute     127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        8 days ago           Up 8 days (healthy)   5432/tcp
```
