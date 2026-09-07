# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `208ec034b1a32fbc7c1e78b4dde63ea16d891ae6`
- Checked at: `2026-09-07T23:27:32Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:23cd254df2ea8ec525db547ce2e8a9d85e0605bccc216a6bfdaa7e3705856558   "uvicorn runtime_app…"   api       13 minutes ago   Up 13 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
