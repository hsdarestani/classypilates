# Classy Pilates — website & booking prototype

Premium redesign and booking UX for Classy Pilates Frankfurt.

## What is implemented

- Responsive premium website using Classy Pilates' existing visual assets and content direction
- Barry's-inspired schedule UX, adapted to Classy Pilates instead of copied
- Six bookable studio spaces:
  - Bahnhofsviertel · 1. OG
  - Bahnhofsviertel · Ladies / 2. OG
  - Sachsenhausen
  - Bornheim
  - Mid
  - Oval
- 7-day schedule with studio, class and time filters
- Reformer, Powerformer, Mat Pilates and Barre
- Availability states, sold-out state and waitlist flow
- Returning-client and first-class booking modes
- Booking confirmation UI and “My bookings” prototype
- Current Classy class-pack pricing (1 / 5 / 10 / 20 classes)
- Mobile-first booking flow

> The current repository is a front-end prototype. The schedule is generated demo data in `public/app.js`. Do not use it for real customer bookings until the production booking API is connected.

## Cloudflare Pages

Use these settings:

- Production branch: `main`
- Framework preset: `None`
- Build command: leave empty
- Build output directory: `public`

## Production booking architecture

The owner’s biggest concern is booking disruption. The production system should be designed so that the public website is never the single point of failure.

### Recommended stack

- **Frontend:** Cloudflare Pages
- **Booking API:** separate API service (Django/FastAPI/Node) behind Cloudflare
- **Database:** managed PostgreSQL with automated backups + point-in-time recovery
- **Cache/read model:** Cloudflare/KV or Redis for fast schedule reads
- **Payments:** Stripe with idempotency keys
- **Email:** transactional provider with retry queue
- **Monitoring:** uptime + API latency + failed-booking alerts

### Reliability requirements

1. **Seat locking** — when a customer starts checkout, the seat is held for a short TTL so two people cannot purchase the last place.
2. **Atomic booking transaction** — capacity check and booking insertion happen in one database transaction.
3. **Idempotency** — repeated taps, slow mobile networks or payment retries cannot create duplicate bookings or duplicate charges.
4. **Waitlist queue** — cancellations promote the next eligible client safely; the seat is temporarily reserved before notification expires.
5. **Read-only fallback** — if the booking API has an incident, the website can still show the last known schedule with a clear status instead of becoming blank.
6. **Health checks and alerts** — booking API, database and payment webhooks monitored separately.
7. **Webhook retry + reconciliation** — payments are reconciled even when a webhook arrives late or is delivered more than once.
8. **Audit trail** — every booking, cancellation, manual admin change and payment state change is logged.
9. **Backups** — automated database backups and tested restore procedure.
10. **Controlled rollout** — run the new booking system in parallel with the current provider before full cutover.

## Migration plan with near-zero booking risk

1. Build production backend and admin while the current booking system remains live.
2. Import locations, classes, coaches, client accounts, passes/credits and future bookings.
3. Run schedule synchronization and automated parity checks for at least several days.
4. Let staff test bookings/cancellations in a private production environment.
5. Soft-launch the new schedule to a limited percentage of traffic.
6. Keep the old provider available as an operational fallback during the transition.
7. Switch fully only after booking, payment, cancellation, waitlist and notification metrics are stable.

This staged migration is the important part: the client should not be asked to trust a “big-bang” replacement on day one.
