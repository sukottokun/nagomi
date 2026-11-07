---
name: wooenterprise-ai-project-management
description: "WooEnterprise AI-project Management. Does the PM's job on a Woo Enterprise build without a PM, inside the customer's own scoping sheet (a 'Project Plan' table), using Critical Chain. Five jobs: (1) build the plan from the scoping sheet plus the standard Woo milestone template, (2) estimate time left with 50/50 estimates and one shared buffer, (3) work out the order of the work and the critical chain from Depends on and who does each task, (4) summarize where the project stands and what's at risk, (5) sweep updates from the deal P2, the Slack channel named on it, Scott's email, calls, and edits people make in the sheet, then email Scott the digest. Triggers on: 'build a project plan for [company]', 'project status', 'PM check', 'how's the buffer', 'what's at risk on [company]', 'what order should we do this in', 'sweep updates for [company]', 'update the project plan after my call with [company]', 'what are the remaining steps for [company]'."
---

# WooEnterprise AI-project Management

The goal is to do a PM's job without a PM: keep the estimate honest, work out the order, say where the project stands and what's at risk, and gather everyone's updates so nobody has to chase them.

The plan lives in the customer's scoping sheet as a `Project Plan` table, next to the scoping, integration and flow tabs it's built from. Google Sheets is shareable with the agency and the customer, and it replaces Asana and Linear for the build. Everyone can update their own rows there, or just say it in the project Slack channel or email. The sheet's `How to use` tab explains the method to everyone; keep it in sync with this file.

Edit sheets in place with `gws` (never create a copy). Load `my-writing-style` for any prose. Keep notes lean: no vacations, scheduling chatter, or detail that doesn't change the work.

## Never override a person's edit

People edit the sheet for a reason. If someone changed or cleared a cell, or deleted a row, since the last snapshot, don't overwrite it and don't add back what was there, even if Slack, email or the schedule says otherwise. Warn Scott in the digest and let him decide. The same goes for values the script computes: a computed chain that disagrees with the Chain column is a suggestion, not a write.

## Philosophy: Critical Chain

Based on Eliyahu Goldratt's *Critical Chain*.

- **Padded estimates get used up anyway.** People start late (student syndrome), work expands to fill the time (Parkinson's law), and juggling several tasks slows all of them. Finishing early is rarely reported; finishing late always passes on.
- **Estimate at 50/50:** how long a task takes if things go reasonably well. No padding.
- **One shared buffer.** The safety cut from each task goes into a single project buffer before launch, sized at about half the padding removed. Add a feeding buffer only where a long side path joins the chain.
- **The critical chain** is the longest path of dependent work, counting who does it (the agency developer is usually the constraint). Chain owners work one task at a time and hand off as soon as it's done.
- **Track the buffer, not due dates.** Owners update Days left, never percent complete. Green: under a third of the buffer used. Yellow: under two thirds. Red: act now.

## The plan format

The sheet has two views in one Sheets Table, so sorting and filtering keep every row together:

- **Team columns (A-G):** Milestone · Task · Owner · Done when · Status · Days left · Notes. This is all the agency and the customer need to read and update.
- **Two narrow blank spacer columns (H-I).**
- **PM columns (J-L), grouped so they collapse:** Depends on · Done on · Chain. The PM (Claude) maintains these; the team can ignore them.

New fields go in the PM group unless the team needs to act on them. The script finds columns by header name, so the order can change.

- **Owner:** exactly one person per row.
- **Done when:** an end state anyone (or an agent) can check, e.g. "Checkout tax matches Avalara for a test address." Never "work on X."
- **Status:** Not Started / In Progress / Blocked / Done.
- **Chain:** Y on critical-chain tasks, including the Project buffer row.
- **Days left:** remaining 50/50 working days. The buffer row holds the buffer size.
- **Done on:** the date a task was finished.
- **Depends on:** the tasks that must finish first, by name, separated by `;` (task names can contain commas). A unique start of the name is enough. Only real hand-offs, not "nice to have first."
- **Notes:** open questions and blockers only.

Standard milestones (every Woo build): Kickoff & Hosting · Theme & Design · Product Setup · Store Setup · Integrations · Testing · Launch · Post-Launch. Starter tasks, chain flags and default estimates are in `template.tsv`.

`projects.json` holds each project: `"Company": {"sheet": "<id>", "p2": "<post URL>", "launch": "YYYY-MM-DD", "buffer": <days>, "email": ["customer.com", "agency.com"], "off": ["YYYY-MM-DD", ...]}`. `off` lists non-working dates (holiday breaks) so they don't count as buffer. The deal P2 (`gtm-discover-p2-notes`) is the source for everything else about the project, including the Slack channel in its top block.

## Job 1: Build a plan

1. Find the customer's scoping sheet (see `admin-customer-drive-folder`) and read its Technical Scoping, Integration Map and flow sections.
2. New scoping sheets copied from the Store Scoping Template (`1kGSJqRqNpkGpAplTp5HlOMrRoAZB83noWhvlzbX_cIw`) already have a `Project Plan` table with the starter tasks and the How to use section; fill that in. For older sheets without it, copy the tab over from the template (`sheets.copyTo`) and add the How to use section. `template.tsv` mirrors the template's starter tasks. Replace the Integrations placeholder with one row per real system on the Integration Map (skip anything Woo-internal). Add Store Setup rows for scoped B2B features. Merge tasks the user pastes from Asana, Linear, or call notes; collapse duplicates to one row and one owner.
3. Propose 50/50 estimates (Job 2) and Depends on (Job 3).
4. Set Status only from evidence. Show the user the plan, then write it into the `Project Plan` table.
5. Add the project to `projects.json` (find the deal P2 by company name and use its URL for `p2`), then run `check_plan.py <Company> --save` so the first sweep has a snapshot to compare against.

## Job 2: Estimate time left

Propose Days left at 50/50 for every open task that has none; check_plan lists them under "No estimate". Size the buffer at about half the padding cut, and set the launch date as today + chain + buffer in working days. When an owner's update changes Days left, re-run the check; don't re-estimate a task someone else set.

## Job 3: Order the work

`check_plan.py` schedules the open work: a task starts once everything in its Depends on is done, each owner does one task at a time, and the task with the longest path left behind it goes first. The critical chain is the longest path through that schedule, so it counts both the hand-offs and the owner's queue. With no Depends on entries, the chain is just the busiest owner's queue, which is usually the agency developer.

1. Propose Depends on for open tasks: real hand-offs only (connector installed before it's configured; pricing synced before quotes; everything feeding UAT; UAT before cutover; cutover before DNS). Show them as a list and write them only after Scott approves.
2. Run the check and report the chain in order, with dates, and each owner's next two tasks.
3. Where the computed chain disagrees with the Chain column, report it. Scott decides whether to change the column.

## Job 4: Summarize status and risk

Run `python3 ~/Code/nagomi/check_plan.py [Company] --changes` for the numbers, then write the summary on top. Keep it under 120 words:

- **Where it stands:** buffer color, % used, the projected chain finish against launch, and what got done since the last check.
- **At risk (top 3):** blocked chain tasks; chain tasks waiting on an open decision in Notes; an owner with more than two tasks in progress (the switching cost lands on the chain); open tasks with no estimate or owner; a side path long enough to overtake the chain (e.g. punchout feeding UAT).
- **Ask:** the one or two decisions or nudges that would protect the buffer most, each with who to ask.

Then the script's output as-is, below the summary.

## Job 5: Sweep updates

Run for one project, or every project in `projects.json`. Since the last sweep (the `--changes` timestamp; default 7 days):

1. **Sheet edits:** `check_plan.py <Company> --changes` lists every cell people changed and every row added or removed. Those are protected (see "Never override a person's edit") and go in the digest as "Changed in the sheet".
2. **The deal P2:** fetch the post (`p2` in projects.json) via context-a8c `wpcom` -> `content-authoring` -> `posts.get`, never WebFetch. Read Timeline lines dated since the last sweep, the current Next Steps, and new comments. Take the Slack channel from the top block's `Slack Channel` link (the channel ID is the end of the archive URL). If it says TBD or is missing, say so in the digest and skip step 3.
3. **Slack:** read that channel with `slack_read_channel`, and its threads with `slack_read_thread`.
4. **Email:** Gmail `search_threads` for `from:(<domains>) OR to:(<domains>) after:<date>` using the project's `email` domains, plus the company name.
5. **Calls:** any call with the customer or agency not already on the P2 Timeline, via `admin-call-sourcing`.
6. **Map each update to a row:** Status, Days left, Done on, Notes. A clear statement from the owner ("pricing sync is done", "two more days on quotes") is a write. Anything fuzzy, or from someone other than the owner, is a question for Scott. New work, owner changes, Done when changes and new dependencies are always questions.
7. **Write** the clear updates in one `values batchUpdate`, skipping any cell or row that changed in step 1. If a skipped update conflicts with a person's edit, list both under "Needs your call".
8. Run `check_plan.py <Company> --save`, then email Scott the Job 4 summary, a "Written" list (cell, before -> after, source), "Needs your call", and the script output. Use `gws gmail +send` or the Gmail connector.

## Channel post

After a sweep, draft a post for the project Slack channel and show it to Scott. Post only after he approves; the channel includes the customer and the agency. Format:

```
🤖😰 **The AI Project Manager Update for <date>**
<two emoji for the customer's business> **<Company> build**
<one 🟡 per buffer day used, one ⚫ per day left> Launch target <date>. We've used <n> of <buffer> buffer days.
⛓️ Critical Path: <chain milestones, joined with →>.

*Watching*
• <top 2-3 risks, one line each>

*Asks*
• <@owner>: <one specific ask each, with who it unblocks>

[Project Plan](<sheet link>) · update your Status and Days left there, or just reply here
```

Use real Slack mentions (`<@USERID>`). Customer and agency people read it, so don't single anyone out for multitasking or slipping; say it about the work ("a lot of Store Setup is in progress at once").

## Daily run

For the daily sweep, Scott runs `sh ~/Code/nagomi/install-daily.sh` once from his own shell. It installs a launchd job that runs Job 5 headless with `claude -p` at 7:30am on weekdays and emails the digest. `install-daily.sh --digest-only` installs the old script-only email instead (no Slack or email sweep).

## Later

- Post the channel update without approval, once Scott trusts the format.
- Verify Done when against the site (Pressable via context-a8c `team51`, or WP-CLI) before marking a task Done.
- Estimate from history: compare Days left at start vs. actual across finished projects.
