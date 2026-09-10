# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `c454233b8ded4c2255bafb44ca1c946e3464ee1f`
- Checked at: `2026-09-10T08:12:58Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:eb0f0d005f64f0cdd602be01b8f6a9de34f8b543b87875f2219e93357226ea22   "uvicorn runtime_app…"   api       9 minutes ago   Up 9 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
