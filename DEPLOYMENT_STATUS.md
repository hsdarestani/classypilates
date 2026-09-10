# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `75f5d1f108ed24d0dd1962dc60948bcdebb2babd`
- Checked at: `2026-09-10T07:50:13Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:4a4c2249670b498fb134d6dc9b3c86abce9fcf290775f73d611cf4b007e928ee   "uvicorn runtime_app…"   api       3 minutes ago   Up 3 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago     Up 2 weeks (healthy)   5432/tcp
```
