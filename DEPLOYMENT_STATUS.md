# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `1d826e7d17542934ce2a74570647ea2f82d5a267`
- Checked at: `2026-09-10T08:30:57Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:eb0f0d005f64f0cdd602be01b8f6a9de34f8b543b87875f2219e93357226ea22   "uvicorn runtime_app…"   api       27 minutes ago   Up 27 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
