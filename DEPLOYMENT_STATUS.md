# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `ed7d6ff7c0640449f885a3215c368e7472e3eab3`
- Checked at: `2026-08-24T12:11:12Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                    PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       23 seconds ago   Up 22 seconds             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        31 minutes ago   Up 31 minutes (healthy)   5432/tcp
```
