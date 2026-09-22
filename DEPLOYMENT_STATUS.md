# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `aee847202792ea202c5f000bfcc460b95ebe1227`
- Checked at: `2026-09-22T19:43:42Z`
- Local API health: `curl: (56) Recv failure: Connection reset by peer`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED         STATUS                PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       7 seconds ago   Up 3 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        7 days ago      Up 7 days (healthy)   5432/tcp
```
