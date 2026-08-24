# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `3471758df7cbec0c5203753ee96f1aed5356fe71`
- Checked at: `2026-08-24T16:55:27Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                 PORTS
classypilates-api-1   sha256:2124f889a51ed13d61648e0c08d39be75cccf9063fa18c03277c52bab57e936c   "uvicorn main:app --…"   api       4 minutes ago   Up 4 minutes           127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        5 hours ago     Up 5 hours (healthy)   5432/tcp
```
