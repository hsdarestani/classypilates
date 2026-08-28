# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `c0758590553bd56c41cbe55ffb19fe141d0f2419`
- Checked at: `2026-08-28T11:17:28Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED       STATUS                PORTS
classypilates-api-1   sha256:268d51cca2a1aed37517f617307c33cf627bd99d697ce82056b8975d5236fd30   "uvicorn runtime_app…"   api       3 hours ago   Up 3 hours            127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        4 days ago    Up 4 days (healthy)   5432/tcp
```
