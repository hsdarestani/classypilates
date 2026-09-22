# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `74477b087067b7ed0c4f0de9dcf23478a84f9cae`
- Checked at: `2026-09-22T17:00:58Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                PORTS
classypilates-api-1   sha256:4d164303e778a10c35001078f170d07285c318d818252a8c91893459f7237ecb   "uvicorn runtime_app…"   api       4 minutes ago   Up 4 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        7 days ago      Up 7 days (healthy)   5432/tcp
```
