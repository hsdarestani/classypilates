# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `a2e6533b1a2014daf615e8b84ed7a90a8a4aab16`
- Checked at: `2026-09-14T22:38:43Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED             STATUS                       PORTS
classypilates-api-1   sha256:8bdf87cc5aad60dfef677459bca9baea7fd32a6098bdf41a5090b06b71df43b4   "uvicorn runtime_app…"   api       About an hour ago   Up About an hour             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        About an hour ago   Up About an hour (healthy)   5432/tcp
```
