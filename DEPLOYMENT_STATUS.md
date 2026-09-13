# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `fee0086398cccab01f2505c4a8ca193a3649a206`
- Checked at: `2026-09-13T11:20:24Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:4031314d5c29b58e3649e66b26244810121e28ed23c4280351c3b9d388351fde   "uvicorn runtime_app…"   api       28 seconds ago   Up 27 seconds          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
