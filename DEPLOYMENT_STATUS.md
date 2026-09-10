# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `9694722a21e066ba760e2a5dc7d9f1cf0d2ea6c9`
- Checked at: `2026-09-10T08:00:11Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED              STATUS                 PORTS
classypilates-api-1   sha256:e8932816c575668f4318b45e8cd13422b1c82544dfe1216665b750e553381da0   "uvicorn runtime_app…"   api       About a minute ago   Up About a minute      127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago          Up 2 weeks (healthy)   5432/tcp
```
