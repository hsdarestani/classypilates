# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `5b0baccf112e01eada96d6700da6eefbad8d9742`
- Checked at: `2026-09-14T21:29:22Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                   PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       44 seconds ago   Up 40 seconds            127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        4 minutes ago    Up 3 minutes (healthy)   5432/tcp
```
