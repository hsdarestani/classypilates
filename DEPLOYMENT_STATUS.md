# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `958d220ed7a89634d7d5441da5cd4ca5005f3ee8`
- Checked at: `2026-09-08T09:38:02Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:0e0bb75b20943cdef968d5b39c81e5b19d40aa4d7bcd0bfd8c7b97f41cc3b80b   "uvicorn runtime_app…"   api       21 minutes ago   Up 21 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago      Up 2 weeks (healthy)   5432/tcp
```
