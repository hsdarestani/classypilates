# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `fa53fbcd5f2137453ed828ae2888c2dc3a3cd89f`
- Checked at: `2026-08-24T14:45:26Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       17 seconds ago   Up 15 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        3 hours ago      Up 3 hours (healthy)   5432/tcp
```
