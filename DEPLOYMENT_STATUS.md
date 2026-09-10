# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `2f67cbf515fcc0eb086b23d370528f7957091b53`
- Checked at: `2026-09-10T08:37:10Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:f3d98be15445281d5e41cc3c68fdcb2bf6503441273dc0202ea4022a9a81559e   "uvicorn runtime_app…"   api       56 seconds ago   Up 54 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
