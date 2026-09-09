# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `5a6930086e8b87a89ea6be86a3528872ecfec53e`
- Checked at: `2026-09-09T20:12:49Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:58e5682de37ab99f6d1f9b9fcf2b0e27fc6fb4f82d4dbc93cb487cd9a2964ca9   "uvicorn runtime_app…"   api       22 minutes ago   Up 22 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
