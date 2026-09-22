# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `445caae3ac81508c05309439374b08a4e69afcd2`
- Checked at: `2026-09-22T17:51:51Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                PORTS
classypilates-api-1   sha256:46b15cefb3ba5ff17f5a7fca2dbc16b467365500e42d1f6e89e8527d0490367f   "uvicorn runtime_app…"   api       2 minutes ago   Up 2 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        7 days ago      Up 7 days (healthy)   5432/tcp
```
