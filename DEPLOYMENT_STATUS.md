# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `8fd91344a0f3125c4781740e9d6ba4b99050a08d`
- Checked at: `2026-09-15T11:00:56Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Up About a minute       127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        14 hours ago         Up 14 hours (healthy)   5432/tcp
```
