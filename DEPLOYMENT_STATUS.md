# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `d0e4ae8202646785bb1475447a8b6aeff8a36331`
- Checked at: `2026-09-09T20:20:15Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:c8ba8dd7db369c8f4ff7ecd13286db8ce23f7a5317599834291a1431267731e4   "uvicorn runtime_app…"   api       7 minutes ago   Up 6 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
