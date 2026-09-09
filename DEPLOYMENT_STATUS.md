# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `1953c5fa2b6b552bd7bc129814d1efa8898187a9`
- Checked at: `2026-09-09T19:49:44Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED              STATUS                 PORTS
classypilates-api-1   sha256:af4ba218fd0a67fd23523132841ee90a19af2fadffee371a837af96398729ad3   "uvicorn runtime_app…"   api       About a minute ago   Up About a minute      127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago          Up 2 weeks (healthy)   5432/tcp
```
