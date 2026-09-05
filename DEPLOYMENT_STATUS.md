# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `3c7de7f579d624cad3a1bb2e512ad5ee5b004806`
- Checked at: `2026-09-05T11:10:46Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED              STATUS                 PORTS
classypilates-api-1   sha256:d159bb999ade194232f070999a5445976b7fd8c38f68c306e82ddc0040cb73fa   "uvicorn runtime_app…"   api       About a minute ago   Up About a minute      127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        12 days ago          Up 12 days (healthy)   5432/tcp
```
