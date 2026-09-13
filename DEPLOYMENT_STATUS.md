# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `769323f824e15f45592bd78e47d95804de1f07de`
- Checked at: `2026-09-13T14:00:23Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED       STATUS                 PORTS
classypilates-api-1   sha256:dc51a3f0a6e985811f6aaa89d430f692c9cb83a9948b61f468be5e3324ce2066   "uvicorn runtime_app…"   api       3 hours ago   Up 3 hours             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago   Up 2 weeks (healthy)   5432/tcp
```
