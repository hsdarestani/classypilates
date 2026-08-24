# Classy Production Deployment Status

- Workflow status: **success**
- Commit: `82caea99312630f26b55af0c09e7cbacc289597e`
- Checked at: `2026-08-24T19:38:45Z`
- Local API health: `{"ok":true,"service":"classy-production"}`

## Remote containers
```
NAME                  IMAGE                                                                     COMMAND                  SERVICE   CREATED       STATUS                 PORTS
classypilates-api-1   sha256:35eee0a258af1daaaef4a1f9a3aaa5cc3153d6e165fd38c07847311c825ded78   "uvicorn main:app --…"   api       2 hours ago   Up 2 hours             127.0.0.1:8787->8000/tcp
classypilates-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        8 hours ago   Up 8 hours (healthy)   5432/tcp
```
