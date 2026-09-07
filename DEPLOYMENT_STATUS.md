# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `9002829a3d1d939f82d2893675b39ba1d5ef6680`
- Checked at: `2026-09-07T20:07:39Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:abe15a724eaf2a8f02e1a4179f877171e6e5c8fc2c38097ec57a97e813d4cee0   "uvicorn runtime_app…"   api       15 minutes ago   Up 15 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
