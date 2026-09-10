# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `705b31baa35895fc6addbe984df2e8c2c1208511`
- Checked at: `2026-09-10T08:03:07Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:a5859588e6749034e80f61f53a86f60b0727d34d65568bf20bfdd0703e182da5   "uvicorn runtime_app…"   api       2 minutes ago   Up 2 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
