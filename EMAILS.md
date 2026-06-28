# Symbology Email Planning

## Verify Email / Confirm Account  (most deliverability-critical)


 Single clear CTA button + raw URL as plaintext fallback
 Time-limited, single-use token (24h typical)
 "Didn't sign up? Ignore this" line
 Sent from primary fully-authenticated sender; keep it plain


## Order Confirmation  (a receipt — people keep these)

 What was purchased, amount charged, date
 Invoice / order number
 Last 4 of card; billing period (for subscriptions)
 Link to billing portal
 Decide the single owner: Resend or Stripe sends this — not both

note: we have a basic stripe checkout integration at the moment. Our support link takes the user to a stripe-hosted checkout page, so we probably use their email backend. However we haven't yet verified this (only having used test transactions thus far)

## Renewal Notification  (often legally required, not just courtesy)

 Renewal amount + exact charge date
 One-click path to cancel or change plan
 Send in advance (esp. annual plans — CA auto-renew law, EU, click-to-cancel rules)

note: We actually don't enroll the user in a subscription, but we would like to send a reminder email if their support window is coming to a close


## Watch Notifications (opt-in)  (highest reputation risk)

 Per-category / per-watch unsubscribe — not all-or-nothing
 Frequency options: instant / daily digest / weekly digest
 Batch by default if items update often (one email per change floods inboxes)
 List-Unsubscribe header on every send

note: watchlist feature is being implemented on a separate branch from this, we can set up the email now


## Related Emails to Scope (build soon)

 Password reset — same security pattern as verify (single-use, time-limited token)
 Payment failed / dunning — retry sequence; recovers real revenue
 Card expiring — proactive nudge before the charge fails
 Welcome — after successful verification; sets expectations
 Trial ending — if you run trials; reminder a few days out

