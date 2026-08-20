# Booking Flow V2

## Presentation flow now

1. Find Your Studio is shown before the schedule.
2. User filters/chooses a class.
3. The assigned coach is shown with a portrait.
4. User chooses a responsive studio spot / Reformer position.
5. First Class collects first name, last name, email, mobile, date of birth, password, optional emergency contact and required legal consent. Returning Client uses email/password.
6. User chooses Card, Apple Pay, Google Pay, PayPal, Klarna, SEPA or Link.
7. Presentation mode simulates payment processing and displays a successful booking confirmation, booking reference, chosen coach, studio, spot and calendar download.
8. Floating and studio-card quick actions expose Call, Book and Instagram.

## Important production handoff

`public/booking-flow.js` intentionally uses `PRESENTATION_PAYMENT=true` for the requested demo. It does not charge a payment method. Before production, switch the reservation wizard's final payment step to the existing server-side checkout/provider endpoints and use the central D1 booking/spot inventory as the source of truth.

The current interactive spot map is a presentation-ready generated floor plan. Production should persist a `spot_id` against each studio/class booking and load the real equipment/floor layout for each location.

Coach portraits are stock placeholders and should be replaced by the real Classy instructor photos before launch.
