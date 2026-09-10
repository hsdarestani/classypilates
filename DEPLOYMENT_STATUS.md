# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `c9573d152cd40c299a235573bb3b2e2cd9048151`
- Checked at: `2026-09-10T07:58:39Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:213970cc8c4a600b8105af35575d8d93dd022a304556cc15764e6ce6a11a8128   "uvicorn runtime_app…"   api       8 minutes ago   Up 8 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
