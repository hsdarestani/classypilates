# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `650ebb83bc09e51a361481b45b6f4e414607e9c8`
- Checked at: `2026-09-13T11:09:30Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:1924ceddb0ab91c3b8e02176dcc75a9e063cc31872085ceb804d65935be4877f   "uvicorn runtime_app…"   api       2 minutes ago   Up 2 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
