# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `30e374b2890d4fddbd228dbb06d5d1a08c7a31e9`
- Checked at: `2026-09-07T23:13:24Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:a4289e5d08c57ff4432336335beeba92b290577cbf30ff31cddec77d5fea4f6c   "uvicorn runtime_app…"   api       4 minutes ago   Up 4 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
