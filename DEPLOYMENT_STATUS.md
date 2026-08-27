# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `f134432694eae7032413c2fbc1bdeec4f0da3c46`
- Checked at: `2026-08-27T18:59:44Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED      STATUS                PORTS
classypilates-api-1   sha256:0003c85fc255406accf38182dcf7e87e2d3c717392cd888155d5c12931956352   "uvicorn main:app --…"   api       2 days ago   Up 2 days             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        3 days ago   Up 3 days (healthy)   5432/tcp
```
