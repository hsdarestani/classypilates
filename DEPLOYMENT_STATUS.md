# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `a39d3a142c60c61ad66f9eb6c9b91ba13469f8cd`
- Checked at: `2026-08-24T16:51:41Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       22 seconds ago   Up 21 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        5 hours ago      Up 5 hours (healthy)   5432/tcp
```
