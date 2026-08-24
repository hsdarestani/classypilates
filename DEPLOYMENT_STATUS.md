# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `19f76d1cd9a63dfb7741de41c6d56504a2a58eed`
- Checked at: `2026-08-24T13:37:28Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:981a2f3c9f73bc1898d832f6ffca41b8b8be69dc7453c4d9ccdc7e063daeeca5   "uvicorn main:app --…"   api       54 minutes ago   Up 54 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 hours ago      Up 2 hours (healthy)   5432/tcp
```
