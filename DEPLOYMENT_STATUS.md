# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `ef5a79815d5c21e6f676d16ccbf319a53e8dee55`
- Checked at: `2026-09-22T17:13:14Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED              STATUS                PORTS
classypilates-api-1   sha256:0595698a19205e65f301753a683d368349cc7165d0d2bd7f0152022bb7f43d79   "uvicorn runtime_app…"   api       About a minute ago   Up About a minute     127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        7 days ago           Up 7 days (healthy)   5432/tcp
```
