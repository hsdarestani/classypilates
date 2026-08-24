# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `72bc205bd11540c979c17ee8fc7eac1992252762`
- Checked at: `2026-08-24T12:22:32Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                    PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       7 seconds ago    Up 5 seconds              127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        42 minutes ago   Up 42 minutes (healthy)   5432/tcp
```
