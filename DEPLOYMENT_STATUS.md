# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `6a947de021d7d90bc60baed64a733978c1790abb`
- Checked at: `2026-09-15T07:38:16Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED        STATUS                  PORTS
classypilates-api-1   sha256:40f50c9a5e8a42f28e09cf07e6c36f26052236c4d9dcc09dc0d1d12c51db13a1   "uvicorn runtime_app…"   api       9 hours ago    Up 9 hours              127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        10 hours ago   Up 10 hours (healthy)   5432/tcp
```
