# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `13d6b5d70c19c9650ccb6b40e9198305fc001d5d`
- Checked at: `2026-09-10T08:35:55Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED              STATUS                 PORTS
classypilates-api-1   sha256:42d5676a8eb361675575f2339887d645b65eea5bc5adf58115ca2e36b92983f4   "uvicorn runtime_app…"   api       About a minute ago   Up About a minute      127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        2 weeks ago          Up 2 weeks (healthy)   5432/tcp
```
