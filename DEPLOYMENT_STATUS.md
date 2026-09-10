# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `b9264cf58c5d665e955a4a4c100d2157e42e1b8c`
- Checked at: `2026-09-10T08:34:06Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:eb0f0d005f64f0cdd602be01b8f6a9de34f8b543b87875f2219e93357226ea22   "uvicorn runtime_app…"   api       30 minutes ago   Up 30 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
