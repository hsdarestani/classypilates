# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `7118bb800b40fddfb6c21a7ab12e62120fabb9b1`
- Checked at: `2026-08-24T15:29:25Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:58d6f950c1a30d4ec9d96008b4dc9d9022fc860cda47eceffbb73b8ddb381687   "uvicorn main:app --…"   api       14 minutes ago   Up 6 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        4 hours ago      Up 4 hours (healthy)   5432/tcp
```
