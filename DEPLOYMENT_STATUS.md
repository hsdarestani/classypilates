# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `3ef59c1b307f0d6b2d1ed106008988f225da14d9`
- Checked at: `2026-09-15T13:39:55Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                  PORTS
classypilates-api-1   sha256:758ddc46f8f4f7cf682fc0102b97f974c11af25ffda21ed57c925f570ef87208   "uvicorn runtime_app…"   api       3 minutes ago   Up 3 minutes            127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        16 hours ago    Up 16 hours (healthy)   5432/tcp
```
