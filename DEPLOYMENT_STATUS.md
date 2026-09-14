# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `d7e55a537df4b38bee64eb5ec25a7abd916b320a`
- Checked at: `2026-09-14T18:23:03Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED       STATUS                 PORTS
classypilates-api-1   sha256:33a08624d62405ca7848df3aae6468a844759922d19caa8896db9d32790e4be8   "uvicorn runtime_app…"   api       4 hours ago   Up 4 hours             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        3 weeks ago   Up 3 weeks (healthy)   5432/tcp
```
