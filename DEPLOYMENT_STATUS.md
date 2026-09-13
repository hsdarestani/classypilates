# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `2dfe8882c42417c14b438ba34966d4ee0cf19ee2`
- Checked at: `2026-09-13T11:06:41Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED       STATUS                 PORTS
classypilates-api-1   sha256:5f26488f7505784ddc8d8d114426245ed8e69a787745656c0991283fb677a048   "uvicorn runtime_app…"   api       3 days ago    Up 3 days              127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago   Up 2 weeks (healthy)   5432/tcp
```
