// Intentionally inert.
//
// Legacy versions replayed browser-local bookings to /api/bookings when the page
// came back online. Production booking state is now authoritative in the backend
// and Mindbody; replaying localStorage can create duplicate or stale requests.
// Keep this file as a no-op so an old cached HTML include cannot re-enable that
// behavior.
