# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `320d2e17b4c12846f89f6f405239286335db91c2`
- Checked at: `2026-08-25T08:43:53Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED             STATUS                  PORTS
classypilates-api-1   sha256:0003c85fc255406accf38182dcf7e87e2d3c717392cd888155d5c12931956352   "uvicorn main:app --…"   api       About an hour ago   Up About an hour        127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        21 hours ago        Up 21 hours (healthy)   5432/tcp
```
