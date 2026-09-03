# 14-Day Trial Welcome Sequence — Project Management Tool

## Sequence Overview

```
Sequence Name:   Trial Onboarding → First Project & Team Invite (Aha Moment)
Trigger:         User signs up for the 14-day free trial
Goal:            Activation — get the user to (1) create their first project
                 and (2) invite at least one team member. Secondary: convert
                 to paid by Day 14.
Length:          7 emails
Timing:          Immediate, Day 1, Day 3, Day 5, Day 7, Day 10, Day 14
                 (B2B — suppress sends on Sat/Sun; roll to next weekday;
                 send in recipient's local time, ~10:00 AM)
Exit Conditions: • User converts to paid → exit, hand off to New Customer series
                 • User completes BOTH aha-moment actions → switch engaged
                   branch (skip nudges, send celebration + advanced content)
                 • User unsubscribes → suppress
```

### Behavior-based branching (applies to Emails 2–6)
The Skill prefers action-triggered email over pure time-based. Use these rules:

| If user has… | Then the next email… |
|---|---|
| Created 0 projects | Leads with "create your first project" nudge |
| Created project, 0 invites | Leads with "invite a teammate" nudge |
| Done both (aha reached) | Celebrates + surfaces next-level tip (templates, automations, views) |
| Been inactive 3+ days | Routes to proactive-support tone (see Email 5) |

---

## Email 1 — Welcome + Your First Project

```
Send:     Immediately on signup
Subject:  Welcome to [Product] — let's create your first project
Preview:  Your 14-day trial is live. One quick project is all it takes to see
          what your team can do together.
```

**Body**

Hey {{first_name|there}},

Welcome to [Product]. Your 14-day trial is live — and the fastest way to see
what it can do is to set up your first real project. It takes about five
minutes.

Most teams tell us the moment it "clicks" is when they see their own work,
with their own people, moving in one place. That's what we want for you today.

Here's how to get there:

1. Click below to name your first project (use something real — a launch, a
   sprint, a client, a personal goal).
2. Add one or two tasks so the board isn't empty.
3. Hit save. That's it.

Once that's done, I'll show you the part that makes [Product] actually feel
different: inviting your team.

**CTA:** Create your first project → {{app_url}}/projects/new

If you hit a wall, just reply to this email — a real person reads every reply.

Cheers,
The [Product] Team

---

## Email 2 — Quick Win: Finish Setup in 10 Minutes

```
Send:     Day 1, ~10:00 AM local (skip if project already created)
Subject:  Your first project in 10 minutes (yes, really)
Preview:  A blank project is a stuck project. Here's the fastest path from
          "signed up" to "shipping."
```

**Body**

Hey {{first_name}},

Quick check-in: your trial's on day 1, and I noticed you haven't built your
first project yet. No pressure — but I also don't want [Product] to become
another tab you never come back to.

Here's the 10-minute path that works for most teams:

- **Pick one thing** you're already working on this week. Don't overthink it.
- **Create 3–5 tasks** underneath it — the actual steps, not vague buckets.
- **Add a due date** to the first one. That's enough to feel momentum.

That's the whole setup. No templates to configure, no workflow to map out
before you can start.

**CTA:** Open your workspace — {{app_url}}/dashboard

Prefer a walkthrough? Here's a 90-second video → {{help_url}}/first-project

Reply and say "stuck" if you want a hand — I'll point you to a human.

— The [Product] Team

> **Engaged branch** (user already created a project): swap the body for a
> short "Nice — your project's live. Next up: get someone else in it" note
> and point the CTA at the invite screen.

---

## Email 3 — Invite Your Team (the second half of "aha")

```
Send:     Day 3, ~10:00 AM local
Subject:  Projects are better with your team in them
Preview:  [Product] gets useful the moment a second person joins. Invite one
          teammate — takes 20 seconds.
```

**Body**

Hey {{first_name}},

You've got a project in [Product]. Now for the part that actually changes how
your week feels: getting someone else in there with you.

Solo, [Product] is a nice to-do list. With even one teammate, it becomes the
single source of truth — no more "wait, what's the status of that?" pings,
no more version-tracked spreadsheets, no more chasing updates in chat.

Try it today:

- Invite one person you're actively collaborating with on this project.
- Assign them a task so they land somewhere useful.
- Watch the first update come in without you asking for it.

That's the aha moment. It usually hits within an hour of the first teammate
joining.

**CTA:** Invite a teammate → {{app_url}}/projects/{{project_id}}/invite

Not sure who to invite? Start with whoever keeps asking you "where's that at?"

— The [Product] Team

---

## Email 4 — Social Proof: A Team Like Yours

```
Send:     Day 5, ~10:00 AM local
Subject:  How a 6-person team shipped their first project in a week
Preview:  They started exactly where you are. Here's what changed on day two.
```

**Body**

Hey {{first_name}},

Want to see what the next few days can look like?

A small marketing team — six people, one launch, a mess of Slack threads and
Google Docs — signed up two weeks ago. On day one their founder created a
project called "Fall launch." On day two she invited the other five.

By the end of the first week:

- The project had 40+ tasks, all owned.
- Two status meetings got canceled because the board already showed the answer.
- The launch shipped three days early.

The founder told us: *"The moment someone else accepted the invite and moved
a card, I stopped worrying about the launch and started running it."*

That's the gap between "signed up for a tool" and "running the team on it."
It closes the moment a second person joins your project.

**CTA:** Invite your first teammate → {{app_url}}/projects/{{project_id}}/invite

P.S. — If you'd rather see it than read it, here's the 2-minute case study
video: {{help_url}}/customer-story

— The [Product] Team

---

## Email 5 — Check-In & Objection Handler

```
Send:     Day 7 (midpoint), ~10:00 AM local
Subject:  "I don't have time to set up another tool"
Preview:  Fair. Here's how to get value from [Product] without a big setup —
          and how to tell us if it's not for you.
```

**Body**

Hey {{first_name}},

You're halfway through the trial, so I want to be straight with you.

The #1 thing we hear from people who don't stick with [Product] isn't "it's
missing a feature." It's *"I never got around to actually using it."* That's
on us, not you — but I'd rather say it out loud than pretend it doesn't
happen.

If you're stuck, it's almost always one of these:

- **"I don't have time to set it up."** You don't need to. Create one real
  project, invite one real person, and use it for that. That's the whole
  pilot.
- **"My team won't adopt another tool."** They won't have to adopt anything —
  they just need to accept one invite and see their name on a task. The tool
  sells itself from there.
- **"I'm not sure it fits how we work."** Reply with one sentence about how
  your team actually runs projects. I'll tell you honestly whether [Product]
  is a fit — and if it isn't, I'll say so.

**CTA:** Jump back in — {{app_url}}/dashboard

No hard sell. Just don't let the trial run out without giving the team-invite
piece a real shot — that's the part people actually stay for.

— The [Product] Team

---

## Email 6 — Advanced Tip for Teams That Are In

```
Send:     Day 10, ~10:00 AM local
Subject:  Once your team's in, try this next
Preview:  You've got a project and people in it. These three features are
          where [Product] starts saving you real hours every week.
```

**Body**

Hey {{first_name}},

If you've got a project running and at least one teammate in it — nice.
You're past the part where most trials stall. Here's where to go next.

Three things teams tell us they wish they'd found in week one:

- **Templates.** Turn any project into a reusable template. The next launch,
  sprint, or client onboarding is two clicks instead of two hours.
- **Automations.** Auto-assign, auto-move, and auto-notify when work changes
  hands. Cuts the "who's doing what?" check-ins by a lot.
- **Views.** Same project, different lens — board, timeline, calendar, table.
  PMs get the timeline; designers get the board; everyone sees what they need.

You don't need all three today. Pick the one that matches the thing you're
already doing manually and wire it up.

**CTA:** Explore templates & automations → {{app_url}}/templates

If you haven't invited a teammate yet, that's still the single highest-value
thing you can do with the trial — it's literally one click away:
{{app_url}}/projects/{{project_id}}/invite

— The [Product] Team

---

## Email 7 — Trial Ending: Convert

```
Send:     Day 14 (final day), ~9:00 AM local
Subject:  Your trial ends today — here's what you've built
Preview:  Keep your projects and your team in [Product], or walk away clean.
          Either way, here's where things stand.
```

**Body**

Hey {{first_name}},

Your 14-day trial wraps up today. Here's a quick look at what you've already
got in [Product]:

- **{{projects_count}} project(s)** created
- **{{teammates_count}} teammate(s)** invited
- **{{tasks_completed}} task(s)** completed
- **{{comments_count}} updates/comments** from your team

If that's real work you don't want to lose access to, upgrading takes about
30 seconds. Your projects, your teammates, your setup — all carry straight
over. No migration, no re-inviting people.

**Paid plans start at {{price}}/month** and include unlimited projects,
unlimited teammates, automations, and priority support.

**CTA:** Upgrade and keep your work → {{app_url}}/billing/upgrade

If [Product] isn't right for you, no hard feelings — your data stays
exportable for 30 days, and you can grab it here: {{app_url}}/settings/export.

Either way, thanks for giving it a real shot.

— The [Product] Team

> **Engaged branch** (user hit aha AND is highly active): lead with the
> usage summary, drop the "if it's not right for you" hedging, and add a
> line: *"Teams using [Product] the way you are typically upgrade in week
> three — here's what that unlocks."*
>
> **Low-engagement branch** (no project, no invites): shorten the summary,
> lead with "Want two more weeks to actually try it with your team? Reply
> and I'll extend your trial." — removes friction, gathers intent signal.

---

## Metrics Plan

| Metric | Why it matters | Benchmark |
|---|---|---|
| **Activation rate** (% who create first project within 48h) | Primary aha-moment half #1 | Industry SaaS: 20–40%; set target 35% |
| **Team-invite rate** (% who invite ≥1 teammate within 7 days) | Primary aha-moment half #2 — strongest predictor of paid conversion | Target 25%+ |
| **Open rate** (per email) | Deliverability + subject line health | 30–40% (onboarding lifecycle) |
| **Click rate** (per email) | CTA relevance | 3–6% |
| **Reply rate** (Emails 2, 5) | "Real human" support signal | 1–3% (treat as high-intent) |
| **Trial-to-paid conversion** | Business outcome | 15–25% for PM-tool trials |
| **Unsubscribe rate** | List health / relevance | Keep under 0.5% |

### What to A/B test first
1. **Email 1 subject line** — benefit-led ("create your first project") vs.
   curiosity-led ("your trial's live — here's the one thing to do first").
2. **Email 3 send day** — Day 2 vs. Day 3 (sooner after project creation
   tends to lift invite rate).
3. **Email 7 CTA** — "Upgrade and keep your work" vs. "See your plan
   options" (commitment-level framing).

### Instrumentation notes
- Tag every CTA link with `?utm_source=email&utm_campaign=trial-onboarding&utm_medium=email{N}`.
- Fire `aha_reached` event when both `project_created` AND `teammate_invited`
  are true; use it as the exit/branch trigger in the ESP.
- Suppress Emails 2 and 3 entirely if the corresponding action is already
  complete — don't nudge people who've already done the thing.
