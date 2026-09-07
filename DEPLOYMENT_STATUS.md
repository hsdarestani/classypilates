# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `140986ddbd4a90466f7ddedf431ce0d3f38d2b9f`
- Checked at: `2026-09-07T20:22:19Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:bc708e9fe2f68f04df1264c9b9d87fce6e391e36c731e6456ba2d02a1980c731   "uvicorn runtime_app…"   api       14 minutes ago   Up 14 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
