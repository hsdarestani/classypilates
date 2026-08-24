# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `51641895eeb0260757d94160b193481251c86ce1`
- Checked at: `2026-08-24T20:09:02Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   classypilates-api    "uvicorn main:app --…"   api       22 seconds ago   Up 20 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine   "docker-entrypoint.s…"   db        8 hours ago      Up 8 hours (healthy)   5432/tcp
```
