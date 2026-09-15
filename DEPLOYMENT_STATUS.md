# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `63fb53ef0894ab794ec74916c29c08e6bcc7b9b9`
- Checked at: `2026-09-15T14:18:21Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                  PORTS
classypilates-api-1   sha256:c1eef5b909f6d3087f7e6fa7281e5793b20465ff238a519eeaa898e9d60c6592   "uvicorn runtime_app…"   api       5 minutes ago   Up 5 minutes            127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        17 hours ago    Up 17 hours (healthy)   5432/tcp
```
