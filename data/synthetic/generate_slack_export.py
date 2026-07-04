"""Generate the AcmeTech synthetic Slack export.

All conversations are hand-authored below; this script only handles the
mechanical parts — timestamps, thread linkage, and Slack's export layout
(users.json, channels.json, one JSON file per channel per day).

Run:  python data/synthetic/generate_slack_export.py
"""

import json
import os
import random
from datetime import datetime, timedelta, timezone

random.seed(42)

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "slack_export")

# ── People ────────────────────────────────────────────────────────────────

USERS = [
    ("U01", "sarah.chen", "Sarah Chen", "CTO"),
    ("U02", "marcus.webb", "Marcus Webb", "Engineering Lead"),
    ("U03", "priya.sharma", "Priya Sharma", "Senior Backend Engineer"),
    ("U04", "jake.morrison", "Jake Morrison", "Senior Frontend Engineer"),
    ("U05", "elena.petrov", "Elena Petrov", "DevOps Engineer"),
    ("U06", "tom.oconnell", "Tom O'Connell", "Support Lead"),
    ("U07", "aisha.diallo", "Aisha Diallo", "Support Engineer"),
    ("U08", "dan.kim", "Dan Kim", "Product Manager"),
    ("U09", "lucy.tran", "Lucy Tran", "Backend Engineer"),
    ("U10", "raj.patel", "Raj Patel", "Site Reliability Engineer"),
    ("U11", "emma.wright", "Emma Wright", "Account Manager"),
    ("U12", "chris.novak", "Chris Novak", "Junior Engineer"),
]

CHANNELS = [
    ("C01", "engineering"),
    ("C02", "support"),
    ("C03", "incidents"),
    ("C04", "onboarding"),
    ("C05", "product"),
    ("C06", "random"),
]


def M(u, t):
    return {"kind": "msg", "user": u, "text": t}


def T(*msgs):
    return {"kind": "thread", "msgs": [{"user": u, "text": t} for u, t in msgs]}


# ── Authored conversations ────────────────────────────────────────────────

ENGINEERING = [
    T(  # deployment process debate — 10 msgs (NEWER than the Confluence runbook)
        ("U02", "Heads up team — we changed the deploy process last sprint. The Confluence deployment runbook is out of date, don't follow it blindly. New flow: staging -> smoke tests -> canary at 5% -> full prod."),
        ("U12", "wait, the runbook says deploy straight to prod after staging? that's what i did for my first deploy :grimacing:"),
        ("U02", "Yeah that page is from November, we added the canary stage after the January outage. I'll update it... eventually :sweat_smile:"),
        ("U05", "When deploying to prod, always run the smoke tests first. `make smoke` against staging. If any of the 14 checks fail, the deploy stops there. No exceptions."),
        ("U03", "and the canary bakes for 30 minutes minimum now, not 10. we changed that after ACME-201"),
        ("U12", "got it. is the canary automatic or do I have to promote manually?"),
        ("U05", "Automatic promote if metrics stay clean for 30 min. Manual rollback button is in the deploy dashboard, top right. Anyone on the team can hit it, don't wait for permission."),
        ("U01", "+1 to that. Rolling back is always cheaper than debugging in prod. Nobody has ever been criticized here for rolling back too eagerly."),
        ("U09", "should we add this to the runbook? the doc drift is getting bad, i almost followed the old flow last week too"),
        ("U02", "yes, it's on my list. tracking in ACME-247 if someone wants to grab it before me"),
    ),
    T(  # canary thresholds — 8 msgs
        ("U05", "Reminder since it came up twice this week: If the canary shows >2% error rate, rollback immediately. Don't sit there watching it hoping it recovers."),
        ("U10", "2% feels tight for services with low traffic tho. checkout-service gets like 50 req/min at night, one flaky request skews the whole number"),
        ("U05", "fair — the threshold is 2% sustained over 5 minutes, not instantaneous. the deploy bot already computes it that way"),
        ("U10", "ah ok that's more reasonable. is latency part of the auto-rollback too?"),
        ("U05", "p99 > 800ms sustained 5 min also triggers it. error rate and latency are the only two auto signals, everything else is human judgement"),
        ("U03", "worth saying: rollback first, investigate after. we lost 40 min on the June 9th incident because someone was debugging a live canary"),
        ("U10", ":point_up: this. war room first, blame later. actually no blame at all lol"),
        ("U05", "blameless or nothing :handshake:"),
    ),
    T(  # code review standards — 8 msgs
        ("U02", "Code review refresher because I keep seeing single-approval merges: Don't merge without 2 approvals unless it's a hotfix. Hotfixes need 1 approval + a follow-up review ticket filed within 24h."),
        ("U04", "does a rubber-stamp 'lgtm' count as an approval? asking for a friend :eyes:"),
        ("U02", "if the diff is >100 lines and the review took 45 seconds, no. reviewers should at least run the code or trace the logic"),
        ("U09", "what about docs-only changes? feels heavy to need 2 approvals to fix a typo in the README"),
        ("U02", "docs-only and test-only changes: 1 approval is fine. the 2-approval rule is for anything that ships to prod"),
        ("U12", "how do i mark something as a hotfix? just the label?"),
        ("U03", "add the `hotfix` label AND prefix the PR title with [HOTFIX]. the merge bot checks the label, humans read the title"),
        ("U04", "also please stop force-pushing over review comments, it nukes the thread context. append commits, squash at merge"),
    ),
    T(  # staging flakiness — 6 msgs
        ("U09", "staging is doing the thing again where the auth service returns 503 for ~2 min after every deploy. anyone else?"),
        ("U05", "known issue, it's the connection pool warming up. see ACME-238. workaround: the smoke tests retry for 3 minutes before failing"),
        ("U09", "ahh ok. it made me think my change broke auth, lost an hour to that :melting_face:"),
        ("U05", "yeah it bites everyone once. real fix is lazy pool init, it's in the backlog"),
        ("U12", "adding this to the onboarding doc so the next new person doesn't get got"),
        ("U02", "good instinct chris :raised_hands:"),
    ),
    T(  # smoke tests in CI — 6 msgs
        ("U03", "proposal: run the smoke suite on every PR, not just pre-deploy. it's 90 seconds, would catch integration breaks way earlier"),
        ("U05", "90s x 40 PRs a day is real CI money but honestly the June 9 incident would've been caught by exactly this"),
        ("U02", "let's do it on PRs that touch api/ or services/, skip for frontend-only diffs"),
        ("U04", "frontend can break the contract too... but ok as a start"),
        ("U03", "done, shipped in ACME-252. path-filtered smoke on PRs is live"),
        ("U02", "nice turnaround :fire:"),
    ),
    T(  # feature flags — 5 msgs
        ("U04", "can we PLEASE agree on one feature flag system, we have env vars, the yaml file, and launchdarkly and nobody knows which wins"),
        ("U02", "precedence is launchdarkly > yaml > env, documented in... hm, actually i don't think it's documented anywhere except this message now"),
        ("U04", "cool cool cool so slack is our source of truth :upside_down_face:"),
        ("U01", "this is exactly the kind of tribal knowledge that keeps biting us. someone write it down please, ACME-260 filed"),
        ("U09", "took it, will put a page in Confluence under Engineering"),
    ),
    T(  # db migration practice — 7 msgs
        ("U03", "migration rule reminder after friday's near-miss: never drop a column in the same release that stops using it. two-release rule — release N stops reading, release N+1 drops."),
        ("U12", "why two releases? if nothing reads it isn't it safe?"),
        ("U03", "rollback safety. if release N has a bug and we roll back to N-1, N-1 still reads that column. if you already dropped it, rollback is now impossible"),
        ("U12", "ohhhh. that's really good to know, this should be in the migration checklist"),
        ("U09", "it's in the code review guidelines on Confluence but buried in the appendix. i'll bump it to the top"),
        ("U05", "also always run migrations against the staging snapshot first, `make migrate-staging`. takes 5 min, saves careers :sweat_smile:"),
        ("U03", "lol accurate. friday's migration locked the users table for 90 seconds on staging — imagine that on prod"),
    ),
    # standalone messages — 30
    M("U05", "deploy train leaves at 3pm today, get your PRs merged by 2:30 or catch tomorrow's"),
    M("U09", "merged the retry-logic fix for the webhook dispatcher, see ACME-231"),
    M("U04", "new eslint config landed, run `npm run lint:fix` before your next commit or CI will yell at you"),
    M("U03", "psa: the api rate limiter now returns Retry-After headers, clients should honor them (see the API Rate Limiting Policy page in Confluence)"),
    M("U12", "my first PR is up! ACME-263, be gentle :sweat_smile:"),
    M("U02", "reviewed, two small comments. solid first PR chris"),
    M("U05", "prod deploy done, canary was clean, 0.3% err rate, promoted at 3:42pm"),
    M("U10", "grafana dashboards for the new checkout service are live, link pinned to this channel"),
    M("U09", "anyone know why the nightly build takes 25 min now? it was 12 last month"),
    M("U05", "test parallelism regressed when we bumped the runner image, fix incoming in ACME-244"),
    M("U04", "storybook is broken on main, reverting the theme PR until i figure it out"),
    M("U03", "reminder: secrets NEVER go in the yaml config, that file is in git. use the vault, always"),
    M("U01", "great sprint everyone, 14 tickets closed and zero prod incidents this week :tada:"),
    M("U02", "code freeze starts thursday 5pm for the v2.4 release cut"),
    M("U09", "the flaky test in test_billing.py is quarantined, tracked in ACME-249, don't just re-run CI to get past it"),
    M("U05", "kubernetes upgrade to 1.31 on staging this weekend, expect ~10 min of api blips saturday morning"),
    M("U10", "on-call handoff notes are in the usual doc, quiet week, one paging alert (false positive, tuned it)"),
    M("U04", "TIL our bundle is 40% moment.js. removing it, ACME-255"),
    M("U03", "if you touch the billing service read the escalation matrix on Confluence first, billing bugs page people at 3am"),
    M("U12", "whats the difference between `make deploy` and `make ship`? asking before i break something"),
    M("U05", "`make ship` = deploy + migrations + cache flush. `make deploy` is code only. 99% of the time you want ship"),
    M("U09", "postgres 16 upgrade on staging went clean, prod scheduled for next tuesday 6am"),
    M("U02", "quarterly dependency-update rotation falls on lucy this month, list is in ACME-258"),
    M("U04", "please stop naming test users 'test' 'test2' 'testtest' in staging, i beg :pray:"),
    M("U10", "reminder that the deploy dashboard has a big red ROLLBACK button now. it works. i tested it. use it"),
    M("U03", "webhook signature verification is now mandatory on all inbound integrations, migration guide going up on Confluence today"),
    M("U05", "ci was down 20 min this morning (github actions outage, not us), all green again"),
    M("U09", "who owns the cron that prunes old s3 exports? it's been failing silently since june 20th"),
    M("U05", "that's mine, fixed — the IAM role rotated. added an alert so it can't fail silently again"),
    M("U01", "engineering all-hands moved to friday 11am this week only"),
]

SUPPORT = [
    T(  # refund policy — 8 msgs (NEWER than Confluence's 15-day page)
        ("U07", "customer asking for a refund on an annual plan they bought 22 days ago — the old policy doc says 15 days so i told them no. they escalated. help?"),
        ("U06", "That doc is stale — we changed it in May. Refund window is 30 days, no exceptions. The Confluence refund policy page still says 15 days, I keep meaning to fix it."),
        ("U07", "ooh ok good, so this customer is actually within window. approving the refund now"),
        ("U06", "yep. 30 days from charge date, applies to monthly AND annual plans. the 15-day number is dead, if you see it in any doc flag it to me"),
        ("U11", "confirming from the account side — legal signed off on 30 days in the May policy review. it's in the updated terms too"),
        ("U07", "should i just edit the Confluence page myself?"),
        ("U06", "yes please, and drop a note in here when it's done so everyone knows"),
        ("U07", "will do :saluting_face:"),
    ),
    T(  # enterprise refunds — 7 msgs
        ("U07", "got a $12k refund request from Northwind (enterprise). do i just... process it? that number scares me"),
        ("U06", "No — for enterprise clients, loop in the account manager before processing any refund over $5000. That's Emma for Northwind."),
        ("U11", "yep loop me in. half the time a big refund request is really a renewal negotiation in disguise, we can often fix the underlying issue instead"),
        ("U07", "makes sense. what's the threshold for non-enterprise?"),
        ("U06", "self-serve plans: anything under $1000 you process directly, $1000-5000 needs my sign-off, over $5000 goes to finance"),
        ("U11", "and for Northwind specifically — talked to their admin, they were double-charged by a billing bug (ACME-266). refund the duplicate, keep the sub"),
        ("U07", "done, refunded the dupe charge and noted it on the account. crisis averted :relieved:"),
    ),
    T(  # stripe failure path — 6 msgs
        ("U07", "stripe is throwing 'charge_already_refunded' on a refund that definitely didn't reach the customer. ideas?"),
        ("U06", "classic stripe edge case. If Stripe refund fails, create a manual credit note in billing — Billing > Credits > New, reference the original charge id in the memo."),
        ("U07", "found it. does the credit note auto-apply to their next invoice?"),
        ("U06", "yes, oldest credit first. also file a ticket with the charge id so eng can check for the double-refund bug, it's happened before (ACME-266 again lol)"),
        ("U09", "seeing this thread — yes please keep filing those, we think it's a race in the webhook handler. every data point helps"),
        ("U07", "filed as ACME-271 with both charge ids"),
    ),
    T(  # SLA breaches — 7 msgs
        ("U06", "SLA refresher since we onboarded 3 new enterprise accounts: enterprise gets 1h first-response on P1s, 4h on P2s. the clock starts when the ticket lands, not when we see it"),
        ("U07", "what happens if we breach?"),
        ("U06", "we owe service credits — 5% of monthly fee per breach, caps at 20%. more importantly, 2 breaches in a quarter triggers an exec review with the account"),
        ("U11", "and I have to sit in that review, so please page me BEFORE a breach not after :melting_face:"),
        ("U06", "right — if a P1 is 40 min old and untouched, escalate to me and Emma immediately. the escalation matrix on Confluence has the full chain"),
        ("U07", "does the SLA clock pause overnight?"),
        ("U06", "for standard accounts yes, for enterprise no — that's why we have the follow-the-sun rotation with the contractor team"),
    ),
    T(  # escalation to eng — 6 msgs
        ("U07", "when do i escalate a support ticket to engineering vs just filing a bug?"),
        ("U06", "rule of thumb: data loss, security, or billing errors = escalate immediately (page if outside hours). everything else = file the bug, eng triages next standup"),
        ("U07", "and escalate how, the #incidents channel?"),
        ("U06", "yes, post in #incidents with the ticket link + customer impact + what you've verified. don't just say 'X is broken', say what you tested"),
        ("U10", "from the eng side: the single most useful thing support gives us is a request id from the error page. train customers to screenshot it"),
        ("U07", "adding that to our macros :ok_hand:"),
    ),
    # standalone — 26
    M("U06", "weekly support stats: 214 tickets, 92% within SLA, csat 4.6. good week team"),
    M("U07", "customer found a typo in the invoice pdf ('recieved') — filed ACME-268, not urgent but embarrassing lol"),
    M("U06", "new refund macro is live in zendesk, use 'refund-30d' — it cites the current policy so customers stop quoting the old page at us"),
    M("U07", "psa the 'export my data' feature confuses people, they expect a download but it emails a link. filed a UX suggestion as ACME-273"),
    M("U11", "Northwind renewal signed for 2 more years :tada: thanks for the save on that refund thread"),
    M("U06", "reminder: never share a customer's data with another user on the same account without owner-role confirmation. we almost got burned on this yesterday"),
    M("U07", "the status page auto-updates from the monitoring system now?? this cuts our 'is it down' tickets in half"),
    M("U10", "yep, shipped that last sprint — status.acmetech.dev subscribes to the same alerts we get paged on"),
    M("U06", "if a customer mentions GDPR or deletion requests, use the privacy macro and cc legal@ — do not improvise answers on this, ever"),
    M("U07", "how do i see a customer's rate limit usage? they claim they're being throttled at half the documented limit"),
    M("U09", "admin panel > account > api usage. also check if they're on the legacy plan, those have the old lower limits (see the rate limiting page on Confluence)"),
    M("U07", "that was it, legacy plan. thanks lucy!"),
    M("U06", "holiday coverage doc for early july is posted, check your slots and swap in the thread if needed"),
    M("U07", "customer praised aisha's incident comms by name in a csat comment :heart: sharing because we only ever share complaints"),
    M("U06", "escalation drill next wednesday 2pm — we simulate a P1, practice the paging chain. new folks it's worth joining"),
    M("U11", "heads up: Globex is evaluating us against a competitor, if you see tickets from their domain give them white-glove treatment this month"),
    M("U07", "the 'password reset email not arriving' spike is real, ~15 tickets today. escalated in #incidents"),
    M("U06", "zendesk maintenance sunday 2-4am UTC, tickets queue but nothing is lost"),
    M("U07", "TIL you can merge duplicate tickets in zendesk with cmd+shift+m. 3 years using this tool"),
    M("U06", "new starter guide for support is updated with the 30-day refund policy and the enterprise thresholds"),
    M("U07", "customer on the free plan asking for phone support... politely pointed at the plans page :sweat_smile:"),
    M("U06", "q2 postmortem review with eng is thursday, bring the top 5 recurring ticket themes"),
    M("U07", "top themes drafted: password resets, rate limit confusion, invoice pdf issues, export UX, webhook retries. sound right?"),
    M("U06", "matches my read. webhook retries being top-5 is new, flag that thursday"),
    M("U11", "quarterly business reviews for enterprise accounts start next week, i'll need 15 min of support-history prep per account"),
    M("U06", "on it, i'll pull the reports monday"),
]

INCIDENTS = [
    T(  # the June 9 P0 — database connection pool (matches Jira ACME-201) — 12 msgs
        ("U10", ":rotating_light: P0 — api error rate at 40% and climbing. all endpoints affected. war room is here, i'm first responder"),
        ("U05", "here. db connections are maxed — pool shows 100/100 in use, everything else is queueing"),
        ("U10", "Page the on-call immediately for any P0 — done, priya is paged and joining. sarah FYI"),
        ("U03", "here. checking for a connection leak... the new webhook dispatcher from yesterday's deploy isn't releasing connections on the error path"),
        ("U01", "customer comms: tom, post the status page update. 'degraded performance, investigating' for now"),
        ("U06", "status page updated, enterprise accounts notified per the SLA process"),
        ("U03", "confirmed — every failed webhook delivery leaks one connection. with the retry storm we exhaust the pool in ~20 min. rolling back yesterday's deploy now"),
        ("U05", "rollback deployed. pool usage dropping... 80... 45... 12. error rate back under 0.5%"),
        ("U10", "declaring recovery at 14:52 UTC. total impact 38 minutes. keeping the war room open another 30 min for stragglers"),
        ("U01", "good response everyone. Postmortem must be filed within 48 hours — raj you're first responder so you own the doc, ACME-201 is the tracking ticket"),
        ("U10", "on it. draft will be up tomorrow morning, review at thursday standup"),
        ("U03", "the code fix (release connections in the error path + retry backoff) is ACME-235, i'll have it up for review today"),
    ),
    T(  # P1 latency — 8 msgs
        ("U10", "P1 — checkout p99 latency jumped from 300ms to 2.1s in the last 20 min. not a full outage, page went to me only"),
        ("U09", "looking. the slow query log is full of the orders-by-customer lookup... did an index get dropped?"),
        ("U05", "last night's migration rebuilt that table. index recreation might still be running... yep, `CREATE INDEX CONCURRENTLY` is at 60%"),
        ("U09", "so it self-heals when the index finishes? eta?"),
        ("U05", "~25 min at current rate. mitigation option: pin the query to the read replica which still has the old index"),
        ("U10", "do the replica pin, 25 min of 2s checkouts costs real money"),
        ("U05", "pinned. p99 back to 340ms. unpinning after the index completes"),
        ("U10", "recovered 16:44 UTC. this one gets a lightweight postmortem — one pager, no meeting. filing as ACME-241"),
    ),
    T(  # postmortem process — 6 msgs
        ("U12", "noob question: what actually goes in a postmortem here? my last company just yelled at people in a meeting"),
        ("U10", "lol. blameless here. First responder opens the war room in Slack, owns the timeline, and writes the doc. format: timeline, root cause, customer impact, what went well, action items with owners"),
        ("U12", "who reviews it?"),
        ("U10", "thursday standup reviews all open postmortems. action items become jira tickets with the `postmortem` label — those are prioritized above feature work by policy"),
        ("U01", "the important cultural bit: we postmortem the SYSTEM not the person. the june 9 outage was a missing code path, not priya's fault, and the doc reflects that"),
        ("U12", "honestly refreshing. ok filing this thread under 'reasons i joined' :smile:"),
    ),
    # standalone — 14
    M("U10", "reminder: P0 = full outage or data loss, P1 = major degradation with workaround, P2 = partial/minor. when in doubt page anyway, false pages are free"),
    M("U05", "monitoring gap found during ACME-201 review: we had no alert on db pool saturation. added, fires at 80%"),
    M("U10", "postmortem for the june 9 outage (ACME-201) is filed and reviewed. 4 action items, all ticketed. good process everyone"),
    M("U06", "password-reset email delays confirmed as a sendgrid issue on their side, their status page acknowledges. downgrading to P2, monitoring"),
    M("U10", "sendgrid recovered, reset emails flowing. backlog drained by 18:20"),
    M("U03", "ACME-235 (the pool leak fix) is merged and deployed. canary was clean. that closes the last june 9 action item"),
    M("U10", "on-call schedule for july is up — new joiners shadow first rotation, you page WITH someone before you page alone"),
    M("U05", "chaos drill friday: we kill the read replica in staging and verify failover. observers welcome"),
    M("U10", "drill result: failover worked but took 4 min vs the 90s target. tuning ticket is ACME-259"),
    M("U01", "quarterly incident review: 2 P0s, 5 P1s, MTTR down 35% from q1. the canary process is paying for itself"),
    M("U12", "shadowed my first page with raj last night. false alarm but i now know where the runbooks live :sweat_smile:"),
    M("U10", "that's the way to learn it. next one you drive, i watch"),
    M("U06", "reminder from support-land: when an incident hits enterprise accounts, i need impact + eta in customer-safe language within 30 min for the SLA comms"),
    M("U10", "fair — added a 'customer comms' checkbox to the war room checklist so it can't be forgotten"),
]

ONBOARDING = [
    T(  # chris's setup — 8 msgs
        ("U02", "welcome @chris.novak! :wave: your onboarding buddy is priya (same team, backend). Assign a buddy from the same team — that's the rule, so backend folks get backend buddies"),
        ("U12", "thanks! laptop's set up, what access should i have on day 1?"),
        ("U03", "New engineers get access to staging on day 1, prod after their first merged PR. that's the standing policy — staging creds come from the vault, i'll walk you through it at 2"),
        ("U12", "cool. github org invite hasn't arrived yet btw"),
        ("U02", "sent, check again. also request jira + confluence via the #it-requests form, takes ~an hour"),
        ("U12", "in. the New Hire Onboarding Checklist page on Confluence says to request VPN access but the link 404s?"),
        ("U05", "that page predates the VPN migration — we're on tailscale now, invite sent to your email. flagging the page for an update"),
        ("U12", "tailscale connected. day 1 basically done, thanks all :raised_hands:"),
    ),
    T(  # access policy debate — 6 msgs
        ("U09", "should new hires really wait for a merged PR to get prod READ access? debugging without prod logs is rough"),
        ("U02", "the policy is about prod WRITE. read-only log access via grafana is fine from day 1, that's not gated"),
        ("U03", "clarifying because this confuses everyone: prod ssh/db = after first merged PR. dashboards/logs/traces = day 1. deploy rights = after your first shadowed deploy"),
        ("U09", "can we put THAT table in the onboarding checklist? clearer than what's there now"),
        ("U02", "yes — and while we're at it the checklist still lists the old VPN. it needs a real pass, ACME-269"),
        ("U12", "as the most recent victim of that page i volunteer to rewrite it :sweat_smile:"),
    ),
    # standalone — 16
    M("U02", "onboarding buddy roster updated for q3 — check the sheet if you're up"),
    M("U12", "first PR merged!! (ACME-263) does this mean i get prod access now :eyes:"),
    M("U03", "it does! prod read creds granted, deploy rights after you shadow one deploy train. welcome to the club"),
    M("U02", "new-hire tip that isn't written anywhere: the weekly demo friday 4pm is optional to present but mandatory to attend your first month. best way to learn the product"),
    M("U05", "reminder to new folks: NEVER install packages globally on the dev boxes, everything goes through the devcontainer. saves you from 'works on my machine'"),
    M("U12", "the devcontainer setup took 8 min flat, whoever built that thank you"),
    M("U05", ":saluting_face:"),
    M("U02", "next new hire starts july 14 (backend, senior). lucy you're up as buddy per the roster"),
    M("U09", "on it. i'll pre-request their accounts this week so day 1 isn't spent waiting on IT"),
    M("U06", "support onboarding differs from eng btw — new support folks shadow tickets for a week before touching the queue. doc is linked from the main checklist"),
    M("U02", "30/60/90 check-in template is updated, managers grab it from the People space"),
    M("U12", "wrote up my week-1 confusions as a doc appendix: staging 503s, the VPN 404, which make target to use. future hires should suffer less"),
    M("U02", "this is gold, merged into the checklist. this is exactly what the buddy system is for"),
    M("U03", "PSA the security training link expires after 7 days — new hires do it in week 1 or IT has to reissue it"),
    M("U11", "sales/CS onboarding now includes a support-ticket shadowing day too — knowing the product's rough edges helps everyone"),
    M("U02", "q2 onboarding retro: avg time-to-first-PR is 6 days, down from 11 last year. buddy system + devcontainer get the credit"),
]

PRODUCT = [
    T(  # sprint planning — 7 msgs
        ("U08", "sprint 47 planning is thursday 10am. reminder of the process: PMs bring ranked candidates, eng brings capacity, we commit as a team — nothing enters the sprint after commit without swapping something out"),
        ("U04", "can we actually enforce the no-mid-sprint-additions rule this time :upside_down_face:"),
        ("U08", "the rule IS the enforcement — anyone can say no to additions by pointing at it. escalations go through me, not directly to engineers"),
        ("U02", "capacity note: lucy is on dependency-update rotation and chris is still ramping, so plan for ~80%"),
        ("U08", "noted. carry-overs from 46: the rate-limit dashboard (ACME-254) and export-UX fix (ACME-273)"),
        ("U09", "254 is 90% done, just needs review. don't re-estimate it as fresh work"),
        ("U08", "good call, marking it as carry-over-finish. see everyone thursday"),
    ),
    T(  # rate limiting debate — 8 msgs
        ("U08", "customer feedback theme: our API rate limits confuse people. 3 of the top-10 support themes are rate-limit related. proposal: per-endpoint limits with a live usage dashboard"),
        ("U03", "per-endpoint is fairer but way more surface area. today it's one global bucket per key (documented on the Confluence rate limiting page)"),
        ("U09", "the legacy plans make it worse — old accounts have half the limits and no visibility. that's most of the confused tickets honestly"),
        ("U08", "so maybe phase 1 is just the dashboard (visibility) and legacy-plan migration, phase 2 is per-endpoint?"),
        ("U03", "+1, dashboard is a week of work, per-endpoint limiter is a quarter. don't boil the ocean"),
        ("U06", "support strongly endorses the dashboard, we'd deflect a ticket a day minimum"),
        ("U08", "phase 1 it is — writing the spec today, tickets under ACME-254 epic"),
        ("U04", "i'll take the dashboard UI, been wanting an excuse to touch the usage charts"),
    ),
    # standalone — 15
    M("U08", "roadmap review with sarah went well — q3 themes are reliability, api ergonomics, and the enterprise admin console"),
    M("U08", "user interviews this week: 5 customers on the export flow. jake want to sit in on a couple?"),
    M("U04", "yes, send me the wednesday ones"),
    M("U08", "interview takeaway: nobody understands that exports email a link. everyone expected a direct download. validates ACME-273"),
    M("U08", "feature flag cleanup day is real — we have 41 flags, 12 are permanently on. eng time approved for pruning next sprint"),
    M("U01", "product principle reminder: we're a dev tools company, the api IS the product. dashboard polish never outranks api reliability in prioritization"),
    M("U08", "v2.4 release notes drafted, review by wednesday if you shipped something in it"),
    M("U08", "competitor launched per-endpoint rate limits today fwiw. our phased plan still holds, visibility first"),
    M("U04", "the admin console mockups are in figma, comments welcome until friday"),
    M("U08", "sprint 46 retro: velocity 34 pts, 2 carry-overs, main drag was review latency on big PRs. marcus taking that to eng"),
    M("U02", "review latency point taken — proposing a 24h SLA on first review pass, discussing at eng weekly"),
    M("U08", "customer advisory board is confirmed for july 22, agenda draft in the product space"),
    M("U08", "pricing page A/B results: variant B (usage calculator) converts 18% better. shipping it"),
    M("U08", "reminder PRDs get a tech review BEFORE they're committed to the roadmap — eng finding out at sprint planning is too late"),
    M("U08", "the changelog RSS feed people keep asking for ships this week, tiny ticket, big goodwill"),
]

RANDOM = [
    M("U04", "the good coffee is back in the office kitchen, i repeat, the good coffee is back :coffee:"),
    M("U09", "lunch train to the taco place at 12:30, reply here"),
    M("U12", "in"),
    M("U07", "in :taco:"),
    M("U05", "someone left a mechanical keyboard in conf room B. it's loud. it's beautiful. whose is it"),
    M("U10", "mine, sorry, rescuing it now lol"),
    M("U08", "friday demo snacks poll: pizza vs bao. vote with emoji"),
    M("U04", ":pizza:"),
    M("U09", ":dumpling:"),
    M("U12", "the office plant i was told to water is plastic. i watered it for 3 weeks"),
    M("U06", "chris this is the funniest thing that has happened all quarter"),
    M("U11", "wordle in 2 today :sunglasses:"),
    M("U03", "nobody believes you emma"),
    M("U11", "screenshot or it didn't happen, fine, incoming"),
    M("U05", "psa the standing desk in the corner is haunted, it goes up on its own at 3pm every day"),
    M("U10", "that's the scheduled 'stand up' reminder mode lmao, there's a button"),
    M("U04", "new keyboard day :eyes: :keyboard:"),
    M("U09", "weekend hike photos in the thread, the trail was unreal"),
    M("U08", "monday motivation: we crossed 1000 paying customers over the weekend :chart_with_upwards_trend: :tada:"),
    M("U01", "1000!! incredible milestone team. celebration friday, details tomorrow"),
]

CONTENT = {
    "engineering": ENGINEERING,
    "support": SUPPORT,
    "incidents": INCIDENTS,
    "onboarding": ONBOARDING,
    "product": PRODUCT,
    "random": RANDOM,
}

EXPECTED = {
    "engineering": 80,
    "support": 60,
    "incidents": 40,
    "onboarding": 30,
    "product": 30,
    "random": 20,
}


def count_msgs(items):
    return sum(len(i["msgs"]) if i["kind"] == "thread" else 1 for i in items)


def build():
    os.makedirs(OUT, exist_ok=True)

    users_json = [
        {
            "id": uid,
            "team_id": "T0ACME",
            "name": handle,
            "real_name": real,
            "profile": {"title": title, "real_name": real, "display_name": handle},
            "is_bot": False,
            "deleted": False,
        }
        for uid, handle, real, title in USERS
    ]
    with open(os.path.join(OUT, "users.json"), "w") as f:
        json.dump(users_json, f, indent=1)

    channels_json = [
        {
            "id": cid,
            "name": name,
            "created": 1735689600,
            "creator": "U01",
            "is_archived": False,
            "is_general": name == "random",
            "members": [u[0] for u in USERS],
            "topic": {"value": "", "creator": "", "last_set": 0},
            "purpose": {"value": f"AcmeTech {name} discussions", "creator": "U01", "last_set": 0},
        }
        for cid, name in CHANNELS
    ]
    with open(os.path.join(OUT, "channels.json"), "w") as f:
        json.dump(channels_json, f, indent=1)

    total = 0
    for channel, items in CONTENT.items():
        n = count_msgs(items)
        assert n == EXPECTED[channel], f"#{channel}: {n} != {EXPECTED[channel]}"
        total += n

        # Timestamps: spread items across June 2–30, 2026 (newer than the
        # Confluence pages, so recency-based conflict resolution is testable).
        cursor = datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc)
        messages = []
        for item in items:
            cursor += timedelta(minutes=random.randint(45, 320))
            if cursor.hour >= 19:  # roll to next morning
                cursor = (cursor + timedelta(days=1)).replace(
                    hour=9, minute=random.randint(0, 45)
                )
            if item["kind"] == "msg":
                ts = f"{cursor.timestamp():.6f}"
                messages.append(
                    {"type": "message", "user": item["user"], "text": item["text"], "ts": ts}
                )
            else:
                parent_ts = f"{cursor.timestamp():.6f}"
                reply_cursor = cursor
                for i, m in enumerate(item["msgs"]):
                    if i == 0:
                        msg = {
                            "type": "message",
                            "user": m["user"],
                            "text": m["text"],
                            "ts": parent_ts,
                            "thread_ts": parent_ts,
                            "reply_count": len(item["msgs"]) - 1,
                        }
                    else:
                        reply_cursor += timedelta(minutes=random.randint(2, 25))
                        msg = {
                            "type": "message",
                            "user": m["user"],
                            "text": m["text"],
                            "ts": f"{reply_cursor.timestamp():.6f}",
                            "thread_ts": parent_ts,
                        }
                    messages.append(msg)
                cursor = reply_cursor

        # Split into per-day files like a real Slack export
        by_day: dict[str, list] = {}
        for msg in messages:
            day = datetime.fromtimestamp(float(msg["ts"]), tz=timezone.utc).strftime("%Y-%m-%d")
            by_day.setdefault(day, []).append(msg)

        chan_dir = os.path.join(OUT, channel)
        os.makedirs(chan_dir, exist_ok=True)
        for day, msgs in sorted(by_day.items()):
            with open(os.path.join(chan_dir, f"{day}.json"), "w") as f:
                json.dump(msgs, f, indent=1)

        print(f"#{channel}: {n} messages across {len(by_day)} day files")

    print(f"Total: {total} messages, {len(USERS)} users, {len(CHANNELS)} channels")


if __name__ == "__main__":
    build()
