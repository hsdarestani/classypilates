# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `3aba5686feb3d3a7265201a3f5a185976c93e7fb`
- Checked at: `2026-09-22T17:04:20Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                PORTS
classypilates-api-1   sha256:4d164303e778a10c35001078f170d07285c318d818252a8c91893459f7237ecb   "uvicorn runtime_app…"   api       8 minutes ago   Up 8 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        7 days ago      Up 7 days (healthy)   5432/tcp
```
