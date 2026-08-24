# Classy Pilates Production

Production domain: `classy.smarbiz.sbs`

## Architecture
- Public website: static files from `public/`
- Production API: FastAPI (`server/main.py`)
- Database: PostgreSQL 16
- Deployment: Docker Compose + host Nginx/Caddy reverse proxy
- Staff portal: `/staff.html`
- Admin alias: `/admin.html`
- Coach alias: `/coach.html`

## First setup
On a new database, open `/staff.html`. The page shows a one-time **Ersten Admin erstellen** form. As soon as the first administrator is created, bootstrap closes permanently and the normal Team Login is shown.

## Roles / permissions
The Administrator system role has full access. The Coach system role starts with dashboard, booking view, class view/create, own-class editing, and schedule upload. Admins can create additional roles and assign/remove them per user.

Available permission keys:
- `dashboard.view`
- `finance.view`
- `bookings.view`, `bookings.manage`
- `classes.view`, `classes.create`, `classes.edit`, `classes.delete`, `classes.edit_own`
- `coaches.view`, `coaches.manage`
- `roles.manage`, `users.manage`
- `schedules.upload`
- `marketing.view`

## Schedule upload
CSV and XLSX files can be imported from the staff portal. Recommended columns: `Datum`, `Uhrzeit`, `Studio`, `Kurs`, `Coach`, `Anzahl der Plätze`. PDF is accepted and stored for manual processing.

## Premium module
E-Mail Marketing is intentionally visible but locked in the staff portal as the next premium module.

## Payment status
Payment-provider credentials are not hardcoded. Bookings can already be stored centrally, including selected spot and requested payment method. Until the real provider account is connected, payments remain `pending` and are not counted as paid revenue.

## Deployment
The GitHub Actions workflow `.github/workflows/deploy-production.yml` deploys `main` to `/opt/classypilates` using repository secrets `HOST` and `PASS`, preserves the server `.env`, starts PostgreSQL/API containers and configures the domain reverse proxy without taking over ports 80/443 inside Docker.

Deployment trigger: production control center release.
