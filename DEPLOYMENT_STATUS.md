# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `10400b8eeee1b56cffd2023a75345faf5e496fab`
- Checked at: `2026-09-10T08:32:41Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:eb0f0d005f64f0cdd602be01b8f6a9de34f8b543b87875f2219e93357226ea22   "uvicorn runtime_app…"   api       29 minutes ago   Up 29 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
