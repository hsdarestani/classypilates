# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `4e5dcfc6376ff9a628ca4e521420ff0d662c2665`
- Checked at: `2026-09-07T19:51:26Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:4e477a7ae396e22f7bd52a980a7d98879253f61182155d52a0ddd7ded30ef182   "uvicorn runtime_app…"   api       49 minutes ago   Up 49 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
