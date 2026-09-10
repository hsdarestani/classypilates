# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `4d7c78b28aeb0f91d9cf39b9e601effc03ca113e`
- Checked at: `2026-09-10T08:44:47Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:c49928e05e889994348d3f0b8cfa2dbb82623fc16d010451914e243eca4614cb   "uvicorn runtime_app…"   api       6 minutes ago   Up 6 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
