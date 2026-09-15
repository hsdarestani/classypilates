# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `f6395f4f5642fac1f5d8805c265f63efa13772e0`
- Checked at: `2026-09-15T13:36:20Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                  PORTS
classypilates-api-1   sha256:89290b88d655a1e87d5eab0d18a14f1518fb43a4c1ca6c329a50399763c4cc80   "uvicorn runtime_app…"   api       4 minutes ago   Up 4 minutes            127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        16 hours ago    Up 16 hours (healthy)   5432/tcp
```
