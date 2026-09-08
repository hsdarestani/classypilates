# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `b29e6dfd06b2d5823a32bb9f4d5657c85bc210ba`
- Checked at: `2026-09-08T08:21:59Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:47e692b676e93f566bc0aca595c6037dae416cd79598821c7e40a3d14fa56085   "uvicorn runtime_app…"   api       3 minutes ago   Up 3 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
