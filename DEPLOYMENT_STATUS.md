# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `15c029a543415ef79be4b58241162fd33e1efe7c`
- Checked at: `2026-09-10T08:14:20Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:eb0f0d005f64f0cdd602be01b8f6a9de34f8b543b87875f2219e93357226ea22   "uvicorn runtime_app…"   api       10 minutes ago   Up 10 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
