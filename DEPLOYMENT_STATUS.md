# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `71cfb08da068103d1c8816f968c435414f7f8066`
- Checked at: `2026-09-22T16:55:40Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED              STATUS                PORTS
classypilates-api-1   sha256:94bec9793c2055f3634da2b21e16637a8a2883b41e71444a96f6033d33c4d27e   "uvicorn runtime_app…"   api       About a minute ago   Up About a minute     127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        7 days ago           Up 7 days (healthy)   5432/tcp
```
