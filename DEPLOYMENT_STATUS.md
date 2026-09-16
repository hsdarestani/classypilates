# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `f89ef0f6d4b85741958ddae659bb5a92588df8e7`
- Checked at: `2026-09-16T16:05:39Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED              STATUS                  PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       About a minute ago   Up About a minute       127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        43 hours ago         Up 43 hours (healthy)   5432/tcp
```
