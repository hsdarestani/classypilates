# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `62abc7b84ec8acb194597286d6ca830d8ecf9265`
- Checked at: `2026-09-22T19:52:52Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED         STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       7 seconds ago   Up 3 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago      Up 7 days (healthy)   5432/tcp
```
