# Classy Production Deployment Status

- Workflow status: **failure**
- Commit: `a8c2ba020ae99eb244e6bfffa6f4cc258ff241f7`
- Checked at: `2026-09-22T17:26:27Z`
- Local API health: `curl: (7) Failed to connect to 127.0.0.1 port 8787 after 0 ms: Connection refused`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED         STATUS                PORTS
classypilates-api-1   sha256:c31a8c0d7171f4a437ba82227a449ee033d098d56ed29abeed1d057ba8edb835   "uvicorn runtime_app…"   api       8 minutes ago   Up 7 minutes          127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        7 days ago      Up 7 days (healthy)   5432/tcp
```
