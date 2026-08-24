# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `eb57c4d4ed8c85ea370b093fe3607cbced07b8f4`
- Checked at: `2026-08-24T18:31:12Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:35eee0a258af1daaaef4a1f9a3aaa5cc3153d6e165fd38c07847311c825ded78   "uvicorn main:app --…"   api       27 minutes ago   Up 27 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        7 hours ago      Up 7 hours (healthy)   5432/tcp
```
