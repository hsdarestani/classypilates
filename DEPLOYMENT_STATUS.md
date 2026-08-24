# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `a39224b38e94b993fc1947d8a96e58af4d0f19ec`
- Checked at: `2026-08-24T11:50:34Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                    PORTS
classypilates-api-1   sha256:a5af378562bf373668974c4a4437d130e1ca0ad8af15df3b3fef0feadd013117   "uvicorn main:app --…"   api       10 minutes ago   Up 10 minutes             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        10 minutes ago   Up 10 minutes (healthy)   5432/tcp
```
