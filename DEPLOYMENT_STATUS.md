# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `11ae7652d1543e7f8cb47489d0e2be96b41024ef`
- Checked at: `2026-09-15T10:02:12Z`
- Local API health: `curl: (7) Failed to connect to 127.0.0.1 port 8787 after 0 ms: Connection refused`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Up 8 seconds            127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        13 hours ago         Up 13 hours (healthy)   5432/tcp
```
