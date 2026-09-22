# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `09cf8775cee2b736de958503dd94e42bcce2795f`
- Checked at: `2026-09-22T20:55:52Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   sha256:f0435ee08465a4f42b7fe5139d848a4bb45375ee89167248b15e307e7e9f13af   "uvicorn runtime_app…"   api       13 minutes ago   Up 13 minutes         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        8 days ago       Up 8 days (healthy)   5432/tcp
```
