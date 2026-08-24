# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `bb5a8d7e7a4124d4d8296bde56941d97a99ce606`
- Checked at: `2026-08-24T15:08:09Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       4 seconds ago   Up 1 second            127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        3 hours ago     Up 3 hours (healthy)   5432/tcp
```
