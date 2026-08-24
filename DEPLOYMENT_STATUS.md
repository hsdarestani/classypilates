# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `c6e9471fa77bcf0c1e0c61a653a295bd75b17059`
- Checked at: `2026-08-24T16:01:40Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       13 seconds ago   Up 12 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        4 hours ago      Up 4 hours (healthy)   5432/tcp
```
