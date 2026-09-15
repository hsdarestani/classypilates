# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `bfc0918a7f830896eeb436cdade47ae4be6020ff`
- Checked at: `2026-09-15T08:17:04Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                  PORTS
classypilates-api-1   sha256:6c486e5574a6cc2c451b498aa202bc4831f871d2293fae2ae7a74cf2187be2ef   "uvicorn runtime_app…"   api       38 minutes ago   Up 38 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        11 hours ago     Up 11 hours (healthy)   5432/tcp
```
