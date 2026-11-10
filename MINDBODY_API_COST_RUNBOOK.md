# Mindbody API cost optimization — rollout checklist

Baseline: Mindbody's Nov 9, 2026 report for site 5742686 measured 37,066 API calls in 13 days (2,851/day). Its estimate after changes is 134–250/day, not a verified post-deploy result. Review also saw GetClasses 24,427, GetClassVisits 10,350, UserToken/Issue 1,119, GetStaff 715 over those 13 days.

## Code changes

- Bulk schedule polling remains opt-in **off** by default. If explicitly enabled, the default schedule interval is 8 hours (3 runs/day), instead of 3 minutes.
- Existing signed/de-duplicated Webhook queue handles class, booking, cancellation, waitlist, and attendance-status updates; status-only updates now reconcile the correct class roster.
- Active rosters follow Webhooks. The *opt-in* roster background worker checks completed classes daily using locally known class IDs, and future rosters weekly, rather than polling every active class hourly.
- Staff directory cached for 24 hours per process, with refresh on a new scheduled staff ID or after an authenticated staff create/update.
- Staff tokens cached for one hour per process with a one-time recovery on HTTP 401/invalid token.
- Outbound API calls can be inspected at authenticated `GET /api/staff/mindbody/api-usage`. Counts are local process observations over hourly rolling buckets, not a billable partner-account total.

## Safe deployment and verification

1. Confirm PR checks pass; deploy only through the existing production workflow. This PR does **not** enable background bulk sync or perform provider writes.
2. Verify the Webhook subscription is **Active**, signature checks and durable event queue are functioning. Test create, cancel, sign-in, late cancel, waitlist and class update events.
3. Test live availability against Mindbody and confirm no overselling, no phantom classes, no lost bookings, no stale cancellations, and no unexpected paid/unpaid changes. Do not test with real paid customer orders.
4. Compare authenticated server usage metrics against Mindbody **Activity by Studio** and billing reports for the same 7 full days. The portal aggregates may include other apps/servers/API keys that this process cannot observe. Investigate unexplained differences before claiming success.
5. Evaluate daily totals and each endpoint: `class/classes`, `class/classvisits`, `usertoken/issue`, `staff/staff`. The target of **134–250 calls/day** is a Mindbody estimate, not an enforced upper bound or SLA.
6. If metrics show excess requests, identify caller/service/worker and check for an external kiosk, check-in screen, old deployment, or a second API integration. Do not remove strict pre-booking availability verification to artificially reduce counts.

## Rollback

Revert this PR or set the optional worker toggles off. Confirm local cache, Webhook receipt, and strict pre-booking checks continue. Keep payment and Wellpass settlement investigation independent of API optimization.

## Known limits

- In-memory counters reset when process restarts and do not combine multiple workers.
- Mindbody delivery is not guaranteed to be exactly once or perfectly ordered. Queue, deduplication and occasional reconciliation remain essential.
- Another open PR (#63) also contains the attendance-status webhook fix along with finance changes; coordinate merge order/rebase to avoid conflicts.
