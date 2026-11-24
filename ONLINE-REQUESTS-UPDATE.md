# Online request pause — prepared November 24, 2026

Server changes are included in application release v0.66.0. No production pause
was created and no live requests or other operational records were changed.

## Staff controls

The Dispatch Pending Requests box shows **Online Requests are active/paused**
above **Pause Online Requests**. Users with `review_requests` (administrators
included) choose 8, 12, or 24 hours. **Resume now** ends a pause early. Server
timestamps determine expiration; no running browser or scheduled job is needed.
The pause survives restart, uses revision conflict checks, and records the actor
and previous/new expiration in the existing audit log.

One additive `online_request_settings` table stores global availability. Public
GET `/api/online-requests` exposes only status, expiry, server time and revision.
POST requires a signed-in session, existing origin/CSRF checks, and permission.
`/api/save` enforces the pause under the same lock as the settings write, before
creating a job or photo. Both explicitly marked online requests and the existing
submission-only website integration account are covered. Existing requests,
appointments, and normal staff-created appointments remain available.

## Website integration already published

- Coast YFC: version 50, source `00a2ee3d86032402e29ec27febb517885946ca66`.
- Thrift Mart: version 12, source `2b18b624652d5bd55ff0ad1fb6f4b41bef39d660`.
  The website chat published this descendant of the pause change while adding
  donation information. Both edits are retained; live script matched the tested
  script. Do not overwrite it with the earlier pause-only archive.
- Binopoly: version 6, source `f7794f968662efee4c42170b8aa0a2591264a1f6`.

The Coast YFC Worker proxies read-only availability and applies a second check
before submitting. A pause racing with submission is rejected by Operations;
only the rejected pending idempotency claim is released so the same form can be
retried after reopening. Saved requests retain their successful retry response.
Uncertain saves retain their pending claim, preventing blind duplicate retries.

The three sites share a customer notice with reopening time in America/Chicago,
Okay, Check again and the store phone number. Checks run before item-donation
entry links and form submission; typed details are retained. Monetary giving,
employment, speaker and print forms are outside this pause. Older Operations
builds return 401 or 404 for the new route: the Worker reports `supported:false`
and existing online flow continues until the new server is installed. Other
availability failures show a retry notice and do not submit.

## Verification

- `test_online_requests` passed: durations, expiry at the boundary, restart,
  resume, permission denial, invalid input, stale revision, public response
  privacy, server write rejection, retained database records and staff workflow.
- `test_online_requests_ui` passed: desktop/mobile, light/dark status contrast,
  all three website notices, resume, outage, normal active navigation, direct
  form visits and preservation of entered fields. Uses isolated sample data.
- Existing `test_server`, `test_data_integrity`, `test_web_assets` passed.
- Website Node tests: eight passed, including pause/submission race, idempotency,
  no cache, CORS, old-server compatibility and outage behavior. Worker build passed.
- No physical data changes or live pause tests performed.

The v0.66.0 release checks include a populated v0.65.0 upgrade, backup and rollback
check and full release CI.
DESK/OFFICE/STORE OPS native launchers do not need changes for this server feature.
Preview PNGs are in ignored `output/preview/online-requests/`.
