# Classy Pilates — Website, Booking & Webshop

Premium Classy Pilates website with a Barry's-inspired booking flow, central booking API, six-location operations panel and a modern multi-payment webshop.

## Included now

- Premium responsive website for six Frankfurt studio spaces
- 7-day schedule with studio, class and time filters
- Reformer, Powerformer, Mat Pilates and Barre
- Availability, sold-out and waitlist states
- Returning-client and first-class flows
- Central D1-ready booking API with capacity protection and duplicate-booking protection
- Central cancellation flow that automatically releases capacity
- Network-first frontend: central API when configured, safe browser fallback while infrastructure is not connected
- “Meine Buchungen” lookup by email
- Optional transactional booking/cancellation emails via Resend
- Protected booking operations panel at `/admin.html`
- Webshop at `/shop.html`
- Class packs: 1 / 5 / 10 / 20 classes
- Cart, customer data, billing data, checkout and order references
- Stripe Checkout adapter with automatic payment methods
- Apple Pay and Google Pay through Stripe when eligible/configured
- Card payments, Link, Klarna and SEPA through Stripe account payment-method settings
- Separate PayPal checkout + secure server-side capture
- Stripe webhook verification and automatic credit fulfillment
- D1 order, order item and credit ledger model
- Idempotency-ready order references and provider request keys

## Cloudflare Pages

Current Pages settings:

- Production branch: `main`
- Framework preset: `None`
- Build command: leave empty
- Build output directory: `public`

Cloudflare Pages Functions are under `functions/` and are deployed with the Pages project.

## D1 setup

Create a D1 database and bind it to the Pages project as:

- Binding name: `DB`

Apply `cloudflare/schema.sql` to the database. It creates locations, classes, customers, bookings, waitlist, products, orders, order items, credit ledger and capacity-protection triggers.

The booking-capacity trigger makes the final capacity check at database level, so two concurrent requests cannot simply overbook the same class through the normal booking endpoint.

## Environment variables / secrets

Set these in Cloudflare Pages → Settings → Variables and Secrets when connecting the providers:

### Booking admin

- `ADMIN_TOKEN` — strong private token used by `/admin.html`

### Stripe

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

Stripe webhook endpoint:

`/api/webhooks/stripe`

Recommended Stripe account payment methods for Germany:

- Cards
- Apple Pay
- Google Pay
- Link
- Klarna
- SEPA Direct Debit

Actual availability is determined by Stripe, browser/device eligibility, currency, customer and the merchant's enabled payment methods.

### PayPal

- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `PAYPAL_ENV` = `sandbox` or `live`

PayPal orders are approved on PayPal and captured server-side at `/api/checkout/paypal-return` before credits are fulfilled.

### Transactional email

- `RESEND_API_KEY`
- `MAIL_FROM` — for example `Classy Pilates <booking@classypilates.de>` after the sending domain is verified

Email failure never rolls a successful booking back; booking state remains the source of truth.

## Booking API

- `GET /api/schedule`
- `GET /api/bookings?email=...`
- `POST /api/bookings`
- `DELETE /api/bookings`
- `POST /api/waitlist`
- `DELETE /api/waitlist`
- `GET/POST/DELETE /api/admin/classes`

Until D1 is bound and real classes are entered/imported, the existing generated schedule remains visible as a safe presentation fallback. Once central schedule data exists, `public/booking-api.js` automatically switches the customer flow to the central API.

## Webshop payment flow

1. Customer chooses a Class Pack.
2. Cart calculates the total from the fixed product catalog.
3. Customer enters contact/billing details.
4. Customer chooses payment method.
5. Stripe methods redirect to Stripe Checkout; PayPal redirects to PayPal approval.
6. Server-side webhook/capture verifies the payment.
7. Order changes to `paid`.
8. Purchased credits are written to `credit_ledger` exactly after confirmed payment.

The frontend never handles raw card numbers.

If payment credentials are not connected yet, the webshop does not fake a successful charge. It stores a prepared local order and clearly states that no debit occurred. This lets the complete UX be tested before live provider credentials are supplied.

## Reliability / migration approach

The client does not need to trust a big-bang replacement. Keep the existing provider live while importing the real schedule, clients, credits and future bookings. Run both systems in parallel, compare capacity/bookings, let staff use `/admin.html`, then switch customer traffic only after booking, cancellation, payment and notification metrics are stable.
