# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `8f2d1d4e8c1d4bed671f7b42f57278fc6a36deb4`
- Checked at: `2026-08-28T11:46:28Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED       STATUS                PORTS
classypilates-api-1   sha256:268d51cca2a1aed37517f617307c33cf627bd99d697ce82056b8975d5236fd30   "uvicorn runtime_app…"   api       4 hours ago   Up 4 hours            127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        4 days ago    Up 4 days (healthy)   5432/tcp
```
