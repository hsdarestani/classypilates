# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `dabdd6237d0a76afd4222b79509678b74d977e35`
- Checked at: `2026-09-13T14:08:32Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:642e3197b2295f3fa832598e0a6425db54d4105543fe99e7bf9e3f4134fe76e4   "uvicorn runtime_app…"   api       7 minutes ago   Up 7 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
