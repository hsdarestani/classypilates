# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `07f9a3229f9cc7d17dc3a1d5bac2d98935f4f4e3`
- Checked at: `2026-09-13T18:38:13Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       24 seconds ago   Up 23 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
