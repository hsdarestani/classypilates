# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `df2c3ab9bdc85ac956dc4c68ddc14c34bc748946`
- Checked at: `2026-09-15T13:44:26Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                  PORTS
classypilates-api-1   sha256:5ffda3ebaac90f95a96d078b265eee526de2185410766bde9c48747c4c78f768   "uvicorn runtime_app…"   api       2 minutes ago   Up About a minute       127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        16 hours ago    Up 16 hours (healthy)   5432/tcp
```
