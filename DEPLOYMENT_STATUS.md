# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `e82e2654ef162ed88925fba7c05f167bb9d5a41a`
- Checked at: `2026-08-24T12:51:24Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED             STATUS                       PORTS
classypilates-api-1   sha256:981a2f3c9f73bc1898d832f6ffca41b8b8be69dc7453c4d9ccdc7e063daeeca5   "uvicorn main:app --…"   api       8 minutes ago       Up 8 minutes                 127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        About an hour ago   Up About an hour (healthy)   5432/tcp
```
