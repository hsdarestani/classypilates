# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `98624092058f17049e9cd55f5421bce479ae940b`
- Checked at: `2026-08-24T15:22:36Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:58d6f950c1a30d4ec9d96008b4dc9d9022fc860cda47eceffbb73b8ddb381687   "uvicorn main:app --…"   api       7 minutes ago   Up 11 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        4 hours ago     Up 4 hours (healthy)   5432/tcp
```
