# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `183e6ba94164e95886a32cdf16e1c7fdccbf74d3`
- Checked at: `2026-08-24T11:51:09Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                    PORTS
classypilates-api-1   sha256:a5af378562bf373668974c4a4437d130e1ca0ad8af15df3b3fef0feadd013117   "uvicorn main:app --…"   api       11 minutes ago   Up 11 minutes             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        11 minutes ago   Up 11 minutes (healthy)   5432/tcp
```
