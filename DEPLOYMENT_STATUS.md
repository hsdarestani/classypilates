# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `fbc07b3c06fe8761324f8f7ff9cf17f3b6aeeae5`
- Checked at: `2026-08-28T07:56:46Z`
- Local API health: `curl: (7) Failed to connect to 127.0.0.1 port 8787 after 0 ms: Could not connect to server`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                          PORTS
classypilates-api-1   sha256:7b6ad4fac8fb792262c4b348c0d8d06b35e9650c0d092b67ab0fac1d7f6d624f   "uvicorn runtime_app…"   api       3 minutes ago   Restarting (1) 47 seconds ago   
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        3 days ago      Up 3 days (healthy)             5432/tcp
```
