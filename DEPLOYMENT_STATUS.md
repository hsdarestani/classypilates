# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `184b9f1ba318579ae49ea28e851f8b0b27ee5183`
- Checked at: `2026-08-24T18:24:22Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                 PORTS
classypilates-api-1   sha256:35eee0a258af1daaaef4a1f9a3aaa5cc3153d6e165fd38c07847311c825ded78   "uvicorn main:app --…"   api       20 minutes ago   Up 20 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        7 hours ago      Up 7 hours (healthy)   5432/tcp
```
