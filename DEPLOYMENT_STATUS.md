# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `451edf2cd318691c88aebdffcf289b1b5ae60a28`
- Checked at: `2026-08-24T12:35:54Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED          STATUS                    PORTS
classypilates-api-1   sha256:be05844fb7e9a9d6023ac4536df365e8a759b2ab964858bb49aea490b43fd5d3   "uvicorn main:app --…"   api       13 minutes ago   Up 13 minutes             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        56 minutes ago   Up 56 minutes (healthy)   5432/tcp
```
