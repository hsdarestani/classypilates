# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `998db977fa2f7b5acfb71c72bb3106e93c2ddf70`
- Checked at: `2026-09-15T09:58:32Z`
- Local API health: `curl: (52) Empty reply from server`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Up 4 seconds            127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        13 hours ago         Up 13 hours (healthy)   5432/tcp
```
