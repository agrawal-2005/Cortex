"""Generate the AcmeTech synthetic GitHub export.

Produces github_export.json: 30 pull requests + 10 issues for the
fictional acmetech/platform repo. Same people, same Jira tickets, and
the same processes as the Slack/Jira/Confluence exports, so all four
sources cross-reference each other. PRs deliberately repeat the same
workflows (deployment, code review, hotfix handling, Dependabot
handling) so Cortex can extract them as repeatable skills.

Item shape matches what the GitHub REST /issues endpoint returns (and
what backend/ingestion/github_json_ingester.py expects): PRs carry a
"pull_request" key, comments carry {"user": {"login"}, "body",
"created_at"}.

Usage: python data/synthetic/generate_github_export.py
"""

import json
from pathlib import Path

REPO = "acmetech/platform"

# Recurring process blurbs — repeated across items on purpose so the
# clusterer groups them and the extractor sees the same workflow many times.
DEPLOY_PROCESS = (
    "Our deployment process: merge to main -> CI runs -> auto-deploy to "
    "staging -> manual promote to prod with `make deploy ENV=prod`. "
    "Smoke tests run first, then 5% canary, 30-min bake, then full rollout "
    "(ACME-247). Watch the error dashboard for 10 minutes after. "
    "Rollback: `make deploy ENV=prod VERSION=<previous>`. No Friday deploys."
)
REVIEW_PROCESS = (
    "Always squash-merge. Never merge without 2 approvals unless it's a "
    "hotfix with the 'hotfix'/'urgent' label. Never force-push over review "
    "comments — append commits, squash at merge. First review pass within "
    "24 hours. Keep PRs under ~400 lines."
)
HOTFIX_PROCESS = (
    "For hotfixes: create branch from main, fix, get 1 approval, merge "
    "with the [HOTFIX] prefix and the 'hotfix' + 'urgent' labels, deploy "
    "immediately (skip the 30-min canary bake), then backport and file the "
    "follow-up review ticket within 24 hours."
)


def pr(number, title, body, author, created, merged=None, labels=None,
       comments=None, state=None):
    item = {
        "number": number,
        "title": title,
        "body": body,
        "state": state or ("merged" if merged else "open"),
        "user": {"login": author},
        "created_at": created,
        "labels": labels or [],
        "comments": comments or [],
        "html_url": f"https://github.com/{REPO}/pull/{number}",
        "pull_request": {"merged_at": merged},
    }
    return item


def issue(number, title, body, author, created, labels=None, comments=None,
          state="open"):
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "user": {"login": author},
        "created_at": created,
        "labels": labels or [],
        "comments": comments or [],
        "html_url": f"https://github.com/{REPO}/issues/{number}",
    }


def c(author, body, created):
    return {"user": {"login": author}, "body": body, "created_at": created}


ITEMS = [
    # ══════════════════════ FEATURE PRs (10) ══════════════════════
    pr(
        101,
        "feat(api): return Retry-After header from the rate limiter",
        "Implements ACME-204.\n\n"
        "When a client exceeds its rate limit we now return "
        "`Retry-After: <seconds>` alongside the 429, computed from the token "
        "bucket refill time. Enterprise plans also get "
        "`X-RateLimit-Remaining` on every response.\n\n"
        "Testing: added `test_rate_limiter_retry_after.py`; verified on "
        "staging with `curl -i https://staging.acmetech.io/api/v1/orders` "
        "in a loop until 429.",
        "priya.sharma", "2026-06-03T10:15:00Z", merged="2026-06-04T16:20:00Z",
        labels=["feature", "api"],
        comments=[
            c("marcus.webb",
              "Approach looks right. One thing: clamp Retry-After to 3600 so "
              "a misconfigured bucket can't tell clients to wait a week.",
              "2026-06-03T14:02:00Z"),
            c("lucy.tran",
              "Second approval. " + REVIEW_PROCESS,
              "2026-06-04T09:30:00Z"),
            c("priya.sharma",
              "Squash-merged. Deploying per the runbook: staging is green, "
              "promoting with `make deploy ENV=prod` after the canary bake. "
              + DEPLOY_PROCESS,
              "2026-06-04T16:22:00Z"),
        ],
    ),
    pr(
        102,
        "feat(status): auto-update status page from monitoring alerts",
        "Implements ACME-209 (requested by support in #incidents).\n\n"
        "When an alert with severity P0/P1 fires in Alertmanager, we now "
        "POST to the Statuspage API (`POST /v1/pages/{page_id}/incidents`) "
        "to open an investigating incident automatically. Closes when the "
        "alert resolves. This gets us inside the 15-minute status page SLA "
        "from the Incident Response Playbook even when the on-call is heads "
        "down mitigating.",
        "raj.patel", "2026-06-05T09:00:00Z", merged="2026-06-06T11:45:00Z",
        labels=["feature", "observability"],
        comments=[
            c("elena.petrov",
              "Love it. Make sure the Statuspage token comes from vault, not "
              "env — same pattern as the pager token.",
              "2026-06-05T11:20:00Z"),
            c("marcus.webb", "2nd approval, squash away.",
              "2026-06-06T10:05:00Z"),
        ],
    ),
    pr(
        103,
        "feat(webhooks): mandatory signature verification on inbound integrations",
        "Implements ACME-217 (security ask from Sarah).\n\n"
        "All inbound webhooks must now carry `X-Acme-Signature: "
        "sha256=<hmac>` computed over the raw body with the per-integration "
        "secret. Verification: constant-time compare, reject with 401 on "
        "mismatch, 30-day dual-accept window for integrations still "
        "migrating (flag `webhooks.require_signature`).",
        "priya.sharma", "2026-06-09T13:30:00Z", merged="2026-06-11T10:10:00Z",
        labels=["feature", "security"],
        comments=[
            c("sarah.chen",
              "This closes the top finding from the pentest. Approval #1.",
              "2026-06-10T08:15:00Z"),
            c("lucy.tran",
              "Approval #2. Verified the constant-time compare uses "
              "`hmac.compare_digest`, not `==`.",
              "2026-06-10T15:40:00Z"),
        ],
    ),
    pr(
        104,
        "feat(dashboard): rate limit usage dashboard (phase 1)",
        "Implements ACME-254 (Dan's epic, phase 1 = visibility only).\n\n"
        "New admin panel page showing per-account rate limit consumption, "
        "with a callout for legacy plan accounts whose configured limit "
        "differs from the plan default (the ACME-228 class of confusion).",
        "jake.morrison", "2026-06-10T11:00:00Z", merged="2026-06-12T14:30:00Z",
        labels=["feature", "frontend"],
        comments=[
            c("dan.kim",
              "Screenshot matches the spec, ship it. (Not an approval — PM "
              "approvals don't count toward the 2, per the review "
              "guidelines.)",
              "2026-06-11T09:10:00Z"),
            c("chris.novak", "Approval #1. Traced the query, looks right.",
              "2026-06-11T13:25:00Z"),
            c("marcus.webb", "Approval #2. Squash-merge when CI is green.",
              "2026-06-12T10:00:00Z"),
        ],
    ),
    pr(
        105,
        "feat(errors): show request id in the error page footer",
        "Implements ACME-263. My first PR here!\n\n"
        "Error pages now render `request_id` in the footer so support can "
        "paste it straight into the log search. Format matches what "
        "`X-Request-Id` returns on API responses.",
        "chris.novak", "2026-06-11T15:00:00Z", merged="2026-06-13T09:20:00Z",
        labels=["feature", "good-first-issue"],
        comments=[
            c("raj.patel",
              "Welcome aboard! Requested one change: truncate the id to the "
              "first 8 chars visually but copy the full id on click — "
              "support pastes these into Kibana.",
              "2026-06-12T10:30:00Z"),
            c("priya.sharma",
              "Approval #2. FYI since this is your first merge: " +
              DEPLOY_PROCESS,
              "2026-06-12T16:45:00Z"),
            c("marcus.webb",
              "Merged — and per ACME-227 this unlocks your prod read "
              "access. Ask Priya to provision it.",
              "2026-06-13T09:25:00Z"),
        ],
    ),
    pr(
        106,
        "feat(exports): in-app progress + direct browser download for data export",
        "Implements ACME-273.\n\n"
        "The 'export my data' flow now shows an in-app progress indicator "
        "and triggers the download in the browser when the async job "
        "completes. The email link stays as a fallback (it still lands in "
        "junk for ~30% of Outlook enterprise seats, see ACME-234).",
        "jake.morrison", "2026-06-16T10:20:00Z", merged="2026-06-18T13:00:00Z",
        labels=["feature", "frontend", "ux"],
        comments=[
            c("tom.oconnell",
              "Support will throw a party. This is our #2 ticket driver.",
              "2026-06-16T12:00:00Z"),
            c("lucy.tran", "Approval #1 — backend polling endpoint is clean.",
              "2026-06-17T09:15:00Z"),
            c("priya.sharma", "Approval #2, squash-merge.",
              "2026-06-17T17:30:00Z"),
        ],
    ),
    pr(
        107,
        "feat(alerts): page on-call when DB pool saturation crosses 80%",
        "Implements ACME-236, action item from the June 9 P0 postmortem "
        "(ACME-201 / issue #136).\n\n"
        "New Prometheus alert `DBPoolSaturationHigh`: fires at 80% pool "
        "usage for 5 minutes, pages the on-call primary per the paging "
        "policy (P1 during business hours). At 95% it escalates to P0.",
        "elena.petrov", "2026-06-17T09:45:00Z", merged="2026-06-18T15:10:00Z",
        labels=["feature", "observability", "postmortem"],
        comments=[
            c("raj.patel",
              "This would have given us 20 minutes of warning on June 9. "
              "Approval #1.",
              "2026-06-17T11:00:00Z"),
            c("marcus.webb",
              "Approval #2. Postmortem action items get priority over "
              "feature work, glad this landed inside the week.",
              "2026-06-18T10:20:00Z"),
        ],
    ),
    pr(
        108,
        "feat(dev): devcontainer-based development environment",
        "Implements ACME-224.\n\n"
        "Adds `.devcontainer/` with the full stack (Postgres, Redis, "
        "MinIO). `make dev` brings everything up; onboarding doc updated. "
        "New joiners should be able to run the test suite on day 1 instead "
        "of day 3.",
        "elena.petrov", "2026-06-19T14:00:00Z", merged="2026-06-23T11:30:00Z",
        labels=["feature", "devex"],
        comments=[
            c("chris.novak",
              "Tested as the resident newest person: clean clone -> "
              "`make dev` -> green tests in 22 minutes. Approval #1.",
              "2026-06-20T10:10:00Z"),
            c("priya.sharma", "Approval #2.", "2026-06-22T16:00:00Z"),
        ],
    ),
    pr(
        109,
        "feat(changelog): public changelog RSS feed",
        "Implements ACME-262.\n\n"
        "Serves `/changelog.rss` generated from the changelog markdown at "
        "build time. Dan wants enterprise customers to subscribe instead of "
        "emailing support for release notes.",
        "jake.morrison", "2026-06-23T13:15:00Z", merged="2026-06-25T10:00:00Z",
        labels=["feature", "frontend"],
        comments=[
            c("dan.kim", "Validates in the W3C feed checker. Nice.",
              "2026-06-24T09:00:00Z"),
            c("chris.novak", "Approval #1.", "2026-06-24T11:30:00Z"),
            c("marcus.webb", "Approval #2. Squash-merge.",
              "2026-06-24T17:45:00Z"),
        ],
    ),
    pr(
        110,
        "feat(auth): SSO domain allowlist per enterprise account",
        "Follow-up to the Initech SSO escalation (ACME-208).\n\n"
        "Enterprise accounts can now restrict SSO logins to an allowlist of "
        "email domains. Prevents the class of failure where a contractor "
        "with a personal address gets bounced with an opaque error — we now "
        "return a clear 'domain not allowed by your administrator' message.",
        "priya.sharma", "2026-06-24T10:40:00Z", merged="2026-06-26T15:20:00Z",
        labels=["feature", "auth", "enterprise"],
        comments=[
            c("emma.wright",
              "Initech and Globex both asked for exactly this in QBRs.",
              "2026-06-24T14:00:00Z"),
            c("lucy.tran", "Approval #1.", "2026-06-25T09:50:00Z"),
            c("marcus.webb", "Approval #2. " + REVIEW_PROCESS,
              "2026-06-26T11:10:00Z"),
        ],
    ),

    # ══════════════════════ BUG FIX PRs (8) ══════════════════════
    pr(
        111,
        "fix(billing): serialize refund webhook handling to stop double refunds",
        "Fixes ACME-221.\n\n"
        "Root cause: when Stripe redelivers the same refund webhook within "
        "~200ms, both handler invocations pass the 'already refunded?' "
        "check before either writes.\n\n"
        "The fix: (1) `SELECT ... FOR UPDATE` on the charge row so "
        "concurrent handlers serialize, and (2) a unique index on "
        "`refunds.stripe_event_id` as a belt-and-braces idempotency "
        "guard — the second insert now fails cleanly with a no-op.\n\n"
        "Repro test included: fires the same webhook twice concurrently "
        "with `asyncio.gather`, asserts exactly one refund row.",
        "lucy.tran", "2026-06-04T11:30:00Z", merged="2026-06-05T16:40:00Z",
        labels=["bug", "billing", "money"],
        comments=[
            c("priya.sharma",
              "Approval #1. The unique index is the important half — locks "
              "protect us only inside one process.",
              "2026-06-05T09:20:00Z"),
            c("marcus.webb",
              "Approval #2. Money-touching fix, so: deploy to staging, run "
              "the billing smoke suite (`make smoke SUITE=billing`), then "
              "promote. " + DEPLOY_PROCESS,
              "2026-06-05T14:10:00Z"),
        ],
    ),
    pr(
        112,
        "fix(billing): correct rounding for annual plans with mid-cycle proration",
        "Fixes ACME-203.\n\n"
        "We were rounding at each proration step (float), accumulating up "
        "to $0.04 error on 12-line invoices. Fix: compute in `Decimal` with "
        "`ROUND_HALF_EVEN`, round once at the invoice total. Backfilled "
        "test cases from the three customer invoices Tom flagged.",
        "lucy.tran", "2026-06-06T10:00:00Z", merged="2026-06-09T12:30:00Z",
        labels=["bug", "billing"],
        comments=[
            c("tom.oconnell",
              "Confirmed against the Initech invoice from the ticket — "
              "matches their finance team's number to the cent now.",
              "2026-06-06T15:45:00Z"),
            c("priya.sharma", "Approval #1.", "2026-06-08T09:30:00Z"),
            c("marcus.webb", "Approval #2, squash-merge.",
              "2026-06-09T10:15:00Z"),
        ],
    ),
    pr(
        113,
        "fix(webhooks): exponential backoff with jitter for failing endpoints",
        "Fixes ACME-231.\n\n"
        "The dispatcher retried failing endpoints every 10s forever, which "
        "is what amplified the June 9 outage (ACME-201). Now: exponential "
        "backoff 30s -> 1m -> 5m -> 30m -> 2h with +/-20% jitter, and a "
        "circuit breaker that disables an endpoint after 3 days of "
        "continuous failure (customer gets an email at disable time).",
        "lucy.tran", "2026-06-10T09:15:00Z", merged="2026-06-11T17:00:00Z",
        labels=["bug", "webhooks", "postmortem"],
        comments=[
            c("raj.patel",
              "Approval #1 — this is postmortem action item #2 from "
              "ACME-201. Retry storms were half the pool exhaustion.",
              "2026-06-10T14:20:00Z"),
            c("priya.sharma", "Approval #2.", "2026-06-11T11:05:00Z"),
        ],
    ),
    pr(
        114,
        "fix(webhooks): release DB connections on the dispatcher error path",
        "Fixes ACME-235 — the actual root cause of the June 9 P0 "
        "(ACME-201).\n\n"
        "The dispatcher acquired a connection, then raised before the "
        "`release()` when the delivery POST failed. Under a retry storm "
        "that leaks the whole pool in ~20 minutes. Fix: connection "
        "acquisition moved into an `async with pool.acquire()` block so "
        "every path releases; added a leak-detection test that asserts "
        "pool.free == pool.size after 50 simulated failures.",
        "priya.sharma", "2026-06-10T13:00:00Z", merged="2026-06-10T18:30:00Z",
        labels=["bug", "webhooks", "postmortem", "urgent"],
        comments=[
            c("raj.patel",
              "Approval #1. This plus #113 closes the two root causes from "
              "the postmortem (issue #136).",
              "2026-06-10T15:35:00Z"),
            c("marcus.webb",
              "Approval #2. Deploy today please — we're one retry storm "
              "away from a repeat until this ships.",
              "2026-06-10T16:50:00Z"),
        ],
    ),
    pr(
        115,
        "fix(frontend): Safari 18 renders blank dashboard charts",
        "Fixes ACME-215.\n\n"
        "Safari 18 dropped support for the deprecated "
        "`OffscreenCanvas.convertToBlob` path our chart lib used behind a "
        "feature check that lies on Safari. Fix: pin the chart renderer to "
        "the 2D context path on WebKit, added a Playwright run on WebKit to "
        "CI so this can't regress silently.",
        "jake.morrison", "2026-06-05T14:30:00Z", merged="2026-06-06T16:15:00Z",
        labels=["bug", "frontend"],
        comments=[
            c("dan.kim",
              "Two enterprise demos hit this last week, thanks for the "
              "quick turnaround.",
              "2026-06-06T09:00:00Z"),
            c("chris.novak", "Approval #1 — repro'd on Safari 18.1, fixed.",
              "2026-06-06T11:20:00Z"),
            c("marcus.webb", "Approval #2.", "2026-06-06T14:40:00Z"),
        ],
    ),
    pr(
        116,
        "fix(billing): idempotency key on charge creation for webhook retries",
        "Fixes ACME-266.\n\n"
        "When the payment provider times out and retries the checkout "
        "confirmation webhook we created a second charge (Northwind got "
        "billed twice — see ACME-253 for the $12k refund fallout). Fix: "
        "charge creation now carries an idempotency key derived from "
        "`checkout_session_id`; the second webhook finds the existing "
        "charge and returns 200 without writing.",
        "lucy.tran", "2026-06-18T10:45:00Z", merged="2026-06-19T15:30:00Z",
        labels=["bug", "billing", "money", "enterprise"],
        comments=[
            c("emma.wright",
              "Northwind's CFO will be pleased. Their renewal literally "
              "hinged on us fixing this class of bug.",
              "2026-06-18T13:20:00Z"),
            c("priya.sharma",
              "Approval #1. Same pattern as #111 — idempotency at the "
              "write, not just a read-check.",
              "2026-06-19T09:10:00Z"),
            c("marcus.webb",
              "Approval #2. Billing smoke suite on staging before promote, "
              "as always for money paths.",
              "2026-06-19T11:55:00Z"),
        ],
    ),
    pr(
        117,
        "fix(ci): quarantine flaky test_partial_refund_rounding",
        "Fixes ACME-249.\n\n"
        "The test seeded `random` for amounts but not for the proration "
        "date, so month-length differences flipped the expected rounding "
        "in ~3% of runs. Fix: freeze the date with `freezegun`, "
        "parametrize the month-boundary cases explicitly. 500 local runs, "
        "0 failures.",
        "lucy.tran", "2026-06-20T09:30:00Z", merged="2026-06-20T14:00:00Z",
        labels=["bug", "ci", "tests"],
        comments=[
            c("elena.petrov",
              "Approval — test-only change, so 1 approval suffices per the "
              "review guidelines. Thanks for killing the retry-until-green "
              "culture before it starts.",
              "2026-06-20T11:15:00Z"),
        ],
    ),
    pr(
        118,
        "fix(invoices): correct 'recieved' typo in the invoice PDF template",
        "Fixes ACME-268. Reported by Aisha after a customer screenshotted "
        "it, which is a special kind of embarrassing.",
        "chris.novak", "2026-06-24T09:00:00Z", merged="2026-06-24T10:30:00Z",
        labels=["bug", "docs"],
        comments=[
            c("jake.morrison",
              "Approval — docs-only, 1 approval is enough. Also grepped "
              "for other instances: this was the only one.",
              "2026-06-24T09:45:00Z"),
        ],
    ),

    # ══════════════════════ DEPENDENCY PRs (7) ══════════════════════
    pr(
        121,
        "chore(deps): bump sqlalchemy from 2.0.30 to 2.0.35",
        "Bumps [sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) from "
        "2.0.30 to 2.0.35.\n\nRelease notes: bug fixes in the async "
        "session lifecycle and typing improvements. No breaking changes "
        "noted in the changelog.",
        "dependabot[bot]", "2026-06-02T06:10:00Z",
        merged="2026-06-03T10:20:00Z",
        labels=["dependencies", "python"],
        comments=[
            c("lucy.tran",
              "Patch-range bump, CI green including the billing smoke "
              "suite. Per our policy patch/minor merges once CI is green: "
              "@dependabot squash and merge",
              "2026-06-03T10:18:00Z"),
        ],
    ),
    pr(
        122,
        "chore(deps): bump fastapi from 0.111.0 to 0.111.1",
        "Bumps [fastapi](https://github.com/fastapi/fastapi) from 0.111.0 "
        "to 0.111.1.\n\nPatch release: dependency pin fix for starlette.",
        "dependabot[bot]", "2026-06-09T06:05:00Z",
        merged="2026-06-09T11:30:00Z",
        labels=["dependencies", "python"],
        comments=[
            c("priya.sharma",
              "CI green, patch bump. @dependabot squash and merge",
              "2026-06-09T11:28:00Z"),
        ],
    ),
    pr(
        123,
        "chore(deps): bump react from 18.3.1 to 19.0.0",
        "Bumps [react](https://github.com/facebook/react) from 18.3.1 to "
        "19.0.0.\n\nMajor version. Breaking changes: removed legacy "
        "context, new JSX transform required, ref-as-prop.",
        "dependabot[bot]", "2026-06-09T06:07:00Z", state="closed",
        labels=["dependencies", "javascript", "major"],
        comments=[
            c("jake.morrison",
              "Major bump — our policy is majors wait for the quarterly "
              "dependency rotation (ACME-258) where we do them as planned "
              "work with real testing, not drive-by merges.\n\n"
              "@dependabot ignore this major version",
              "2026-06-09T09:40:00Z"),
            c("dependabot[bot]",
              "OK, I won't notify you about version 19.x.x again, unless "
              "you re-open this PR.",
              "2026-06-09T09:41:00Z"),
        ],
    ),
    pr(
        124,
        "chore(deps-dev): bump pytest from 8.2.1 to 8.3.2",
        "Bumps [pytest](https://github.com/pytest-dev/pytest) from 8.2.1 "
        "to 8.3.2.\n\nMinor release: improved assertion rewriting, fixes "
        "for xdist interaction.",
        "dependabot[bot]", "2026-06-16T06:12:00Z",
        merged="2026-06-16T14:45:00Z",
        labels=["dependencies", "python", "dev"],
        comments=[
            c("lucy.tran",
              "Dev-only dep, CI green. @dependabot squash and merge",
              "2026-06-16T14:43:00Z"),
        ],
    ),
    pr(
        125,
        "chore(deps): bump stripe from 9.8.0 to 9.12.0",
        "Bumps [stripe](https://github.com/stripe/stripe-python) from "
        "9.8.0 to 9.12.0.\n\nAdds new API surface for Payment Links; no "
        "breaking changes listed.",
        "dependabot[bot]", "2026-06-16T06:14:00Z",
        merged="2026-06-18T09:20:00Z",
        labels=["dependencies", "python", "billing"],
        comments=[
            c("lucy.tran",
              "Money-touching dependency, so CI green isn't enough: "
              "deployed the branch to staging and ran the billing smoke "
              "suite (`make smoke SUITE=billing`) against the Stripe test "
              "account first. Refund + proration flows all pass.",
              "2026-06-17T15:30:00Z"),
            c("priya.sharma",
              "That's the right process for anything that touches billing. "
              "@dependabot squash and merge",
              "2026-06-18T09:18:00Z"),
        ],
    ),
    pr(
        126,
        "chore(deps): bump jsonwebtoken from 9.0.1 to 9.0.2 (security)",
        "Bumps jsonwebtoken from 9.0.1 to 9.0.2.\n\n**This update fixes a "
        "security vulnerability** (GHSA-xxxx: signature verification "
        "bypass under crafted algorithm headers).",
        "dependabot[bot]", "2026-06-23T06:03:00Z",
        merged="2026-06-23T10:15:00Z",
        labels=["dependencies", "javascript", "security"],
        comments=[
            c("priya.sharma",
              "Security patches merge same-day per policy — no waiting for "
              "the weekly deps pass. CI green. "
              "@dependabot squash and merge\n\nDeploying to prod today, "
              "not waiting for the Thursday train.",
              "2026-06-23T10:12:00Z"),
        ],
    ),
    pr(
        127,
        "chore(deps): bump moment from 2.30.1 to 2.30.2",
        "Bumps [moment](https://github.com/moment/moment) from 2.30.1 to "
        "2.30.2.",
        "dependabot[bot]", "2026-06-23T06:05:00Z", state="closed",
        labels=["dependencies", "javascript"],
        comments=[
            c("jake.morrison",
              "We're removing moment entirely this quarter (ACME-255 — "
              "it's 40% of the bundle). No point taking updates for a "
              "library on death row.\n\n@dependabot ignore this dependency",
              "2026-06-23T09:30:00Z"),
            c("dependabot[bot]",
              "OK, I won't notify you about moment again, unless you "
              "re-open this PR.",
              "2026-06-23T09:31:00Z"),
        ],
    ),

    # ══════════════════════ HOTFIX PRs (5) ══════════════════════
    pr(
        131,
        "[HOTFIX] rollback webhook dispatcher to v2026.06.08 build",
        "Mitigation for the ongoing P0 (ACME-201): API error rate 40%, DB "
        "pool at 100/100. The dispatcher shipped yesterday isn't releasing "
        "connections on its error path; rolling back to the previous "
        "artifact while we fix forward.\n\n" + HOTFIX_PROCESS,
        "priya.sharma", "2026-06-09T14:38:00Z", merged="2026-06-09T14:44:00Z",
        labels=["hotfix", "urgent", "incident"],
        comments=[
            c("raj.patel",
              "Approval — 1 is enough for a hotfix with the urgent label. "
              "Deploying immediately with "
              "`make deploy ENV=prod VERSION=2026.06.08`, skipping the "
              "canary bake per the hotfix process. War room is in "
              "#incidents.",
              "2026-06-09T14:42:00Z"),
            c("priya.sharma",
              "Deployed 14:47. Pool usage dropped 80 -> 45 -> normal. "
              "Recovery declared 14:52. Follow-up review ticket filed "
              "(ACME-235), postmortem due within 48h per the playbook — "
              "tracking in issue #136.",
              "2026-06-09T14:55:00Z"),
        ],
    ),
    pr(
        132,
        "[HOTFIX] keep previous JWKS keys valid for 24h after rotation",
        "Fixes ACME-233 (P0: auth service rejecting valid tokens after "
        "JWKS rotation).\n\n"
        "Root cause: rotation dropped the old signing key instantly, so "
        "every token issued before rotation failed verification until "
        "expiry. Fix: keep the previous key in the verification set for "
        "24h (one full token lifetime) after rotation.\n\n" + HOTFIX_PROCESS,
        "priya.sharma", "2026-06-12T08:20:00Z", merged="2026-06-12T08:55:00Z",
        labels=["hotfix", "urgent", "auth", "incident"],
        comments=[
            c("marcus.webb",
              "Approval (1 needed, hotfix). Merge and deploy now, backport "
              "to the release branch after. File the follow-up review "
              "ticket within 24h.",
              "2026-06-12T08:50:00Z"),
            c("priya.sharma",
              "Deployed 09:05, token verification error rate back to "
              "baseline. Backport PR is #139-internal; follow-up review "
              "ticket ACME-233-followup filed. Postmortem in issue #137.",
              "2026-06-12T09:20:00Z"),
        ],
    ),
    pr(
        133,
        "[HOTFIX] revert gateway config push + add schema validation",
        "Mitigation + fix for ACME-212 (P0: gateway rejecting all requests "
        "after a malformed config push).\n\n"
        "Part 1 (deployed immediately): revert to the last-known-good "
        "config from the config repo history.\n"
        "Part 2 (this PR): the gateway now validates config against a JSON "
        "schema at load and refuses to apply invalid config, keeping the "
        "previous one live. A bad push becomes a no-op with an alert "
        "instead of an outage.",
        "elena.petrov", "2026-06-13T11:05:00Z", merged="2026-06-13T11:40:00Z",
        labels=["hotfix", "urgent", "infra", "incident"],
        comments=[
            c("raj.patel",
              "Approval — hotfix rules. Config revert already live (outage "
              "was 11:02-11:09). This PR is the fix-forward so it can't "
              "happen again.",
              "2026-06-13T11:35:00Z"),
            c("elena.petrov",
              "Merged and deployed. " + HOTFIX_PROCESS,
              "2026-06-13T11:50:00Z"),
        ],
    ),
    pr(
        134,
        "[HOTFIX] per-account rate limit override for migrated enterprise plans",
        "Fixes ACME-270: Globex hard-blocked by the rate limiter after "
        "their plan migration reset them to the default tier limit.\n\n"
        "Fix: plan migrations now carry over any account-level rate limit "
        "override, and support can set overrides from the admin panel "
        "(previously required a deploy). Globex unblocked via manual "
        "override at 10:12 while this merges.",
        "priya.sharma", "2026-06-25T10:30:00Z", merged="2026-06-25T11:15:00Z",
        labels=["hotfix", "urgent", "enterprise"],
        comments=[
            c("emma.wright",
              "Globex confirms traffic is flowing. SLA credit conversation "
              "is tracked in ACME-265.",
              "2026-06-25T11:00:00Z"),
            c("marcus.webb",
              "Approval (hotfix, 1 needed). Merge, deploy, backport. "
              "Follow-up review ticket within 24h please.",
              "2026-06-25T11:10:00Z"),
        ],
    ),
    pr(
        135,
        "[HOTFIX] jittered retry + client backoff for S3 SlowDown responses",
        "Fixes ACME-245 (P1: file uploads failing with S3 503 SlowDown).\n\n"
        "We hammered a single key prefix; S3 responded with 503 SlowDown "
        "and our client failed uploads immediately. Fix: retry SlowDown "
        "with exponential backoff + jitter (max 5 attempts), and shard the "
        "upload key prefix by account hash to spread the partition load.",
        "raj.patel", "2026-06-06T13:20:00Z", merged="2026-06-06T14:05:00Z",
        labels=["hotfix", "urgent", "infra"],
        comments=[
            c("elena.petrov",
              "Approval — hotfix path: branch from main, 1 approval, "
              "deploy immediately, backport after. Upload success rate "
              "recovering on the dashboard already.",
              "2026-06-06T14:00:00Z"),
        ],
    ),

    # ══════════════════════ ISSUES (10) ══════════════════════
    issue(
        136,
        "Postmortem: June 9 P0 — DB connection pool exhaustion, full API outage",
        "Postmortem for ACME-201, filed within 48h per the Incident "
        "Response Playbook. Blameless — we postmortem the system, not the "
        "person.\n\n"
        "TIMELINE (UTC):\n"
        "- 14:14 alert fires, Raj declares P0 in #incidents, war room open\n"
        "- 14:16 on-call (Priya) paged per P0 policy\n"
        "- 14:21 pool confirmed at 100/100, all requests queueing\n"
        "- 14:28 webhook dispatcher (previous day's deploy) identified — "
        "not releasing connections on its error path\n"
        "- 14:35 rollback initiated (PR #131)\n"
        "- 14:47 rollback deployed, pool 80 -> 45 -> normal\n"
        "- 14:52 recovery declared\n\n"
        "ROOT CAUSE: connection leak on the dispatcher error path "
        "(ACME-235, fixed in #114), amplified by retry storm from failing "
        "webhook endpoints (ACME-231, fixed in #113).\n\n"
        "CUSTOMER IMPACT: 38 minutes of elevated errors, peak 40%. Globex "
        "SLA credit request tracked in ACME-265.\n\n"
        "WHAT WENT WELL: detection to war room in 2 minutes; rollback as "
        "mitigation (always acceptable per playbook) beat debugging live.\n\n"
        "ACTION ITEMS (all carry the postmortem label, prioritized above "
        "feature work):\n"
        "- [x] Fix connection leak (ACME-235 / #114) — Priya\n"
        "- [x] Retry backoff + circuit breaker (ACME-231 / #113) — Lucy\n"
        "- [x] Pool saturation alert at 80% (ACME-236 / #107) — Elena\n"
        "- [ ] Load test the dispatcher error path in CI — Raj",
        "raj.patel", "2026-06-10T16:00:00Z",
        labels=["postmortem", "incident", "p0"], state="closed",
        comments=[
            c("marcus.webb",
              "Reviewed at Thursday standup. All action items have owners; "
              "the open one is on next sprint. Closing.",
              "2026-06-12T15:00:00Z"),
        ],
    ),
    issue(
        137,
        "Postmortem: June 12 P0 — auth service rejected valid tokens after JWKS rotation",
        "Postmortem for ACME-233.\n\n"
        "TIMELINE (UTC):\n"
        "- 08:02 scheduled JWKS rotation runs\n"
        "- 08:04 token verification failures spike to 100% for "
        "pre-rotation tokens\n"
        "- 08:07 P0 declared in #incidents (Aisha, from support volume)\n"
        "- 08:20 root cause identified: old key dropped instantly\n"
        "- 08:55 hotfix #132 merged (1 approval, hotfix path)\n"
        "- 09:05 deployed, error rate baseline by 09:12\n\n"
        "ROOT CAUSE: rotation removed the previous signing key "
        "immediately instead of keeping it for one token lifetime.\n\n"
        "ACTION ITEMS:\n"
        "- [x] 24h dual-key window (#132) — Priya\n"
        "- [ ] Alert on token verification failure rate > 5% — Raj\n"
        "- [ ] Rotation runbook page in Confluence — Priya",
        "priya.sharma", "2026-06-13T14:30:00Z",
        labels=["postmortem", "incident", "p0", "auth"], state="closed",
        comments=[
            c("sarah.chen",
              "Good writeup. Note support detected this before monitoring "
              "did — that's the gap the alert action item closes.",
              "2026-06-14T09:10:00Z"),
        ],
    ),
    issue(
        138,
        "Postmortem: duplicate billing reminder emails to ~800 customers (lightweight)",
        "Lightweight postmortem for ACME-256 (P1, small blast radius — one "
        "pager, no meeting, per the playbook).\n\n"
        "WHAT HAPPENED: the nightly billing-reminder cron ran twice — the "
        "k8s node hosting the job was recycled mid-run and the job was "
        "rescheduled without an idempotency guard. ~800 customers got "
        "duplicate emails.\n\n"
        "FIX: reminder send now records `(customer_id, billing_date)` in a "
        "sent-log table with a unique constraint; the rescheduled run "
        "no-ops on conflict.\n\n"
        "PATTERN: this is the third idempotency bug this month (see #111, "
        "#116). Anything that can run twice WILL run twice — writes need "
        "idempotency keys, not just read-checks.",
        "lucy.tran", "2026-06-23T11:00:00Z",
        labels=["postmortem", "incident", "billing"], state="closed",
        comments=[
            c("marcus.webb",
              "That pattern note is the valuable part. Adding 'idempotency "
              "review' to the code review guidelines for anything touching "
              "crons, webhooks, or retries.",
              "2026-06-23T15:20:00Z"),
        ],
    ),
    issue(
        139,
        "Bug: password reset emails delayed 10-30 min or never arriving",
        "Mirrors ACME-210, filed here for the engineering fix.\n\n"
        "REPRODUCTION:\n"
        "1. Request a password reset for any account on prod\n"
        "2. Watch the email queue dashboard\n"
        "3. The reset email sits in `queue:transactional` behind bulk "
        "marketing sends\n\n"
        "EXPECTED: transactional email within 60 seconds.\n"
        "ACTUAL: 10-30 min at peak; SendGrid returns 429 on our shared IP "
        "pool and the retry requeues at the back.\n\n"
        "Support impact: ~15 tickets/week, users think signup is broken "
        "(see #support threads from June 5).",
        "aisha.diallo", "2026-06-05T16:20:00Z",
        labels=["bug", "email", "support-driven"],
        comments=[
            c("lucy.tran",
              "Fix plan: dedicated transactional queue with priority "
              "dispatch + separate SendGrid subuser so bulk sends can't "
              "starve resets. Tracked as ACME-210.",
              "2026-06-06T10:30:00Z"),
        ],
    ),
    issue(
        140,
        "Bug: admin panel shows plan-default rate limit instead of account override",
        "Mirrors ACME-228.\n\n"
        "REPRODUCTION:\n"
        "1. Pick a legacy-plan account with a custom rate limit override "
        "(e.g. any pre-2025 enterprise account)\n"
        "2. Open Admin > Account > Limits\n"
        "3. Panel shows the plan default, not the effective override\n\n"
        "IMPACT: support quotes wrong limits to customers (twice for "
        "Globex — related fallout in ACME-270 / #134).",
        "aisha.diallo", "2026-06-11T09:40:00Z",
        labels=["bug", "admin", "support-driven"], state="closed",
        comments=[
            c("jake.morrison",
              "Fixed as part of the rate limit dashboard (#104) — the "
              "panel now reads the effective limit from the same endpoint "
              "the limiter uses. Single source of truth.",
              "2026-06-12T14:35:00Z"),
        ],
    ),
    issue(
        141,
        "Bug: Storybook broken on main after theme tokens PR",
        "Mirrors ACME-240.\n\n"
        "REPRODUCTION:\n"
        "1. `git checkout main && npm run storybook`\n"
        "2. Every story throws `undefined is not an object "
        "(theme.tokens.spacing)`\n\n"
        "CAUSE: the theme tokens PR renamed `spacing` -> `space` but "
        "Storybook's decorator still injects the old shape. CI doesn't "
        "build Storybook so nothing caught it.",
        "jake.morrison", "2026-06-16T11:30:00Z",
        labels=["bug", "frontend", "ci"], state="closed",
        comments=[
            c("chris.novak",
              "Fixed the decorator and added `npm run storybook:build` to "
              "the CI path filter for frontend changes, so a broken "
              "Storybook now fails the PR instead of surprising the next "
              "person.",
              "2026-06-17T10:15:00Z"),
        ],
    ),
    issue(
        142,
        "Bug: nightly build time regression 12 min -> 25 min after runner image bump",
        "Mirrors ACME-244.\n\n"
        "REPRODUCTION: compare any nightly run before/after June 14 — the "
        "runner image bump to ubuntu-24.04 dropped the layer cache.\n\n"
        "BISECTED: the new image invalidates the Docker layer cache "
        "because the base image digest changed; every nightly rebuilds "
        "all layers from scratch.",
        "lucy.tran", "2026-06-18T15:45:00Z",
        labels=["bug", "ci"], state="closed",
        comments=[
            c("elena.petrov",
              "Fixed: pinned the base image by digest and moved dependency "
              "layers before source layers so code changes don't bust the "
              "cache. Nightly is back to 13 min.",
              "2026-06-19T12:00:00Z"),
        ],
    ),
    issue(
        143,
        "Feature request: automate the canary stage of the deployment runbook",
        "Follow-up to ACME-247 (runbook update: smoke tests, 5% canary, "
        "30-min bake, rollback).\n\n"
        "Today the canary promote is manual: deploy to staging, run smoke "
        "tests, promote 5% with `make deploy ENV=prod CANARY=5`, watch the "
        "error dashboard for the 30-min bake, then full rollout. The ask: "
        "automate the bake-watch so the pipeline auto-promotes when error "
        "rate and p99 stay inside thresholds, and auto-rolls-back "
        "otherwise (like the payments-service auto-rollback that saved us "
        "in ACME-226).",
        "marcus.webb", "2026-06-20T10:00:00Z",
        labels=["feature", "infra", "deploy"],
        comments=[
            c("elena.petrov",
              "Agreed. Thresholds proposal: error rate < 1% AND p99 < "
              "800ms over the full bake window. Manual promote stays "
              "available as an override.",
              "2026-06-20T14:30:00Z"),
            c("raj.patel",
              "+1. The June 9 outage window would have been ~10 min "
              "shorter with auto-rollback on the dispatcher deploy.",
              "2026-06-21T09:15:00Z"),
        ],
    ),
    issue(
        144,
        "Feature request: surface Retry-After in client SDKs",
        "Support-driven follow-up to #101 / ACME-204.\n\n"
        "Now that the API returns Retry-After on 429s, the client SDKs "
        "should honor it automatically instead of hammering. Enterprise "
        "customers (Globex, post ACME-270) are asking for built-in "
        "backoff so their integrations degrade gracefully.",
        "tom.oconnell", "2026-06-26T11:20:00Z",
        labels=["feature", "sdk", "support-driven"],
        comments=[
            c("dan.kim",
              "Scheduling for next sprint. Python SDK first (largest "
              "install base), then Node.",
              "2026-06-26T15:40:00Z"),
        ],
    ),
    issue(
        145,
        "Bug: data export completion emails flagged as spam for Outlook recipients",
        "Mirrors ACME-234.\n\n"
        "REPRODUCTION:\n"
        "1. Trigger 'export my data' with an @outlook.com / "
        "Microsoft-hosted recipient\n"
        "2. Export-ready email lands in junk (~30% of enterprise seats)\n\n"
        "CAUSE (working theory): missing List-Unsubscribe header + link "
        "shortener domain on the CTA button trips Microsoft's filter.\n\n"
        "The real fix is making email unnecessary for the common path — "
        "in-app download shipped in #106. This tracks the deliverability "
        "fix for the fallback email.",
        "tom.oconnell", "2026-06-17T13:00:00Z",
        labels=["bug", "email"],
        comments=[
            c("jake.morrison",
              "#106 removes most of the pain. For the email itself: drop "
              "the shortener, add List-Unsubscribe, and we're moving "
              "transactional sends to the dedicated subuser from #139 "
              "anyway.",
              "2026-06-18T09:45:00Z"),
        ],
    ),
]


def main() -> None:
    export = {
        "repo": REPO,
        "export_date": "2026-06-30",
        "items": ITEMS,
    }
    out = Path(__file__).parent / "github_export.json"
    out.write_text(json.dumps(export, indent=1) + "\n")
    prs = [i for i in ITEMS if "pull_request" in i]
    issues = [i for i in ITEMS if "pull_request" not in i]
    print(f"Wrote {out}: {len(prs)} PRs + {len(issues)} issues "
          f"= {len(ITEMS)} items")


if __name__ == "__main__":
    main()
