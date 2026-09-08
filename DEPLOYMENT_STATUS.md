# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `3ccce336395dbbe071f86686c6c074a382335958`
- Checked at: `2026-09-08T08:18:17Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED       STATUS                 PORTS
classypilates-api-1   sha256:159c70d4c7ba01a28dc32b29492001b328ef04d2db1e6ddd70a98f2b40843f25   "uvicorn runtime_app…"   api       9 hours ago   Up 9 hours             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago   Up 2 weeks (healthy)   5432/tcp
```
