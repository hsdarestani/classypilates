# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `4b89bd27885efd378640fe78526e5493577bd691`
- Checked at: `2026-09-22T17:19:08Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                PORTS
classypilates-api-1   sha256:c31a8c0d7171f4a437ba82227a449ee033d098d56ed29abeed1d057ba8edb835   "uvicorn runtime_app…"   api       55 seconds ago   Up 48 seconds         127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        7 days ago       Up 7 days (healthy)   5432/tcp
```
