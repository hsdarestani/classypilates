# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `32b35b9a47577bec03cf72a0043d7ea372e8a785`
- Checked at: `2026-08-24T19:33:30Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED             STATUS                 PORTS
classypilates-api-1   sha256:35eee0a258af1daaaef4a1f9a3aaa5cc3153d6e165fd38c07847311c825ded78   "uvicorn main:app --…"   api       About an hour ago   Up About an hour       127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        8 hours ago         Up 8 hours (healthy)   5432/tcp
```
