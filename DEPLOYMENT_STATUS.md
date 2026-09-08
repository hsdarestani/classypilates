# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `4621506db798a428e58711b4564d82e82d7b39a5`
- Checked at: `2026-09-08T09:07:22Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:6895c56bc643e49976454848f829710ae94f872f6498a35ea11240f2c1c7535d   "uvicorn runtime_app…"   api       27 minutes ago   Up 27 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
