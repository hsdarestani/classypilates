# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `901be1b0c5eab96db697aa7c1c58016e5f34ab26`
- Checked at: `2026-08-28T07:37:11Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED        STATUS                PORTS
classypilates-api-1   sha256:cbf572534a30b9e12b27f273ec72fb2a106c454b94a0ec3d5ff527f5d29cad6a   "uvicorn runtime_app…"   api       12 hours ago   Up 12 hours           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        3 days ago     Up 3 days (healthy)   5432/tcp
```
