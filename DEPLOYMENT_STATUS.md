# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `6c5087c23bf600d6160163d1f4d3f31859e19110`
- Checked at: `2026-09-15T14:09:39Z`
- Local API health: `curl: (56) Recv failure: Connection reset by peer`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                         PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Restarting (1) 4 seconds ago   
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        17 hours ago         Up 17 hours (healthy)          5432/tcp
```
