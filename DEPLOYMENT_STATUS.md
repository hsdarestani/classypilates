# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `00a046d783a44aa1ae8a647887b7f91a6b40046c`
- Checked at: `2026-08-24T18:03:56Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       23 seconds ago   Up 21 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        6 hours ago      Up 6 hours (healthy)   5432/tcp
```
