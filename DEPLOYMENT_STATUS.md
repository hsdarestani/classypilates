# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `fdd762290d8f0c1cf115fc786fa41414e31c9b12`
- Checked at: `2026-09-07T19:01:37Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn runtime_app…"   api       23 seconds ago   Up 21 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
