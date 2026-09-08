# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `546216adef93be3b5efc88b01e75c03be736e5c0`
- Checked at: `2026-09-08T09:16:02Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:0a9898bc3a63a5f2d84f501e5d879f26b91544923374f919d5c16d8bb0d80af8   "uvicorn runtime_app…"   api       8 minutes ago   Up 8 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
