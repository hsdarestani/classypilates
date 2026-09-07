# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `df94c3521227495333880bc64f56590a807c3cfb`
- Checked at: `2026-09-07T18:59:11Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED       STATUS                 PORTS
classypilates-api-1   sha256:d159bb999ade194232f070999a5445976b7fd8c38f68c306e82ddc0040cb73fa   "uvicorn runtime_app…"   api       2 days ago    Up 2 days              127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago   Up 2 weeks (healthy)   5432/tcp
```
