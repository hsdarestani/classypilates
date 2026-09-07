# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `dd0409d89aca1ac2ba8983688ecebd36f6a40b82`
- Checked at: `2026-09-07T22:57:49Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED       STATUS                 PORTS
classypilates-api-1   sha256:b6940e7b3f140bc56d068c0aafb72de07489242fee948c9d5871d6ebf329da0a   "uvicorn runtime_app…"   api       2 hours ago   Up 2 hours             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago   Up 2 weeks (healthy)   5432/tcp
```
