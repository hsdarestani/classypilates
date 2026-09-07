# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `73c6962e8fb598e67468b81cdcdbe46951a6cfd2`
- Checked at: `2026-09-07T20:58:40Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:84581f082a99a4e579fbe8a70869ca0a1b99226a56cbf48fe82fca4f7e0f2855   "uvicorn runtime_app…"   api       32 minutes ago   Up 32 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
