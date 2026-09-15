# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `eaa426c28e3b795f8070b200a5f3df6f156b22af`
- Checked at: `2026-09-15T13:21:40Z`
- Local API health: `curl: (7) Failed to connect to 127.0.0.1 port 8787 after 0 ms: Connection refused`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                         PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Restarting (1) 2 seconds ago   
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        16 hours ago         Up 16 hours (healthy)          5432/tcp
```
