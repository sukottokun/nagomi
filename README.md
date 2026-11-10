# Nagomi (和み)

Nagomi (和み) is the AI project manager for WooEnterprise store builds. The goal is a harmonious store build and launch, using AI, open communication and trust.

Nagomi does a PM's job on a build that doesn't have one. It keeps the estimate honest, works out the order of the work, says where the project stands and what's at risk, and gathers everyone's updates so nobody has to chase them. It's a Claude Code plugin: a skill (`skills/wooenterprise-ai-project-management/SKILL.md`), a small script (`check_plan.py`) that reads the plan and does the math, and `/nagomi:` commands for each job.

The plan lives in the customer's scoping sheet as a `Project Plan` tab, next to the Technical Scoping, Integration Map and Data Flow tabs it's built from. The agency and the customer can both edit it, and it replaces Asana and Linear for the build. Anyone can update their own rows there, or just say it in the project Slack channel or by email.

## How we plan: Critical Chain

Nagomi is based on Eliyahu Goldratt's *Critical Chain*.

- **Why:** padded estimates get used up anyway. People start late, work expands to fill the time, and juggling several tasks slows all of them. Finishing early is rarely reported; finishing late always passes on to the next task.
- **Estimates:** estimate each task at 50/50, meaning how long it takes if things go reasonably well. No padding.
- **Buffer:** the safety cut from each task goes into one project buffer before launch, sized at about half the padding removed. The team shares it instead of hiding it in each task.
- **Chain:** the critical chain is the longest path of dependent work, counting who does it (usually the agency developer). Nagomi works it out from Depends on and each owner's queue and suggests Chain = Y; a person decides. Chain owners work one task at a time and hand off as soon as it's done.
- **Tracking:** we track the buffer, not due dates. Owners update Days left, not percent complete. Green means less than a third of the buffer is used, yellow less than two thirds, and red means act now.

## The Project Plan tab

Team columns (what the agency and customer read and update): Milestone · Task · Owner (one person) · Done when (an end state anyone can check) · Status · Days left · Notes (open questions and blockers only).

PM columns, to the right and collapsible (Nagomi maintains these): Depends on · Done on · Chain.

Status is Not Started, In Progress, Blocked or Done. Depends on lists the tasks that must finish first, separated by `;`. The standard milestones are Kickoff & Hosting, Theme & Design, Product Setup, Store Setup, Integrations, Testing, Launch and Post-Launch, with starter tasks in `template.tsv`.

## What Nagomi does

- Proposes 50/50 estimates and the order of the work (Depends on), and works out the chain.
- Picks up updates from the deal P2, the project Slack channel, email and calls, and fills in Status, Days left and Done on.
- Never overwrites a change a person made in the sheet. It flags the change and lets you decide.
- Sends a status summary: where the build stands, buffer used, what's at risk, and each owner's next tasks.
- Drafts a channel update for the project Slack channel. It posts only after you approve it.
- Later: checks Done when against the site before a task is marked Done.

The team's part is to keep Status and Days left current in the sheet, or say it in the project Slack channel, and to put blockers and open questions in Notes.

## Bringing on a new client

Each of these has to be in place before Nagomi can run a project.

1. **The deal P2 exists.** Create it with `gtm-discover-p2-notes` on woocustomersuccess.wordpress.com. Nagomi reads its Timeline, Next Steps and comments on every sweep.
2. **The project Slack channel is on the P2.** Put the channel link in the `Slack Channel` field of the P2's top block. If it says TBD or is missing, the sweep skips Slack and says so in the digest. You need to be in the channel so the Slack connector can read it, and the customer and agency should be in it too.
3. **The scoping sheet is a copy of the Store Scoping Template** (`1kGSJqRqNpkGpAplTp5HlOMrRoAZB83noWhvlzbX_cIw`), saved in the customer's Drive folder (see `admin-customer-drive-folder`). Copies already have the `Project Plan` and `How to use` tabs. For an older sheet without them, ask Nagomi to build a plan and it copies the tab over.
4. **The Integration Map is filled in.** Nagomi adds one Integrations row per real system on it, so do it before building the plan.
5. **The sheet is shared** with edit access for the agency and the customer's project owner.
6. **Build the plan.** In Claude Code, say "build a project plan for <Company>". Nagomi fills in the starter tasks, proposes owners, estimates and Depends on, and shows you the plan before it writes anything. Approve the Depends on list, then let it write.
7. **Add the project to `~/.nagomi/projects.json`** (Nagomi does this as part of step 6). Copy the shape from `projects.example.json`:
   - `sheet`: the scoping sheet ID
   - `p2`: the deal P2 URL
   - `launch`: the launch date
   - `buffer`: buffer size in working days
   - `email`: the customer's and agency's email domains, used to find project email
   - `off`: non-working dates, such as a holiday break, so they don't count against the buffer
8. **Save the first snapshot:** `python3 check_plan.py <Company> --save`. The next sweep compares against it to find edits people made in the sheet.
9. **Tell the team how to use it.** Point them at the sheet's `How to use` tab and tell them to update Status and Days left there, or just say it in the channel.

## Running it

Use the commands, or just ask in plain words:

- `/nagomi:estimate <Company>`: a dry-run estimate with a confidence rating, before any plan is written
- `/nagomi:plan <Company>`: build the Project Plan in the scoping sheet
- `/nagomi:order <Company>`: the order of the work and the critical chain
- `/nagomi:status [Company]`: where it stands and what's at risk
- `/nagomi:sweep [Company]`: pick up updates from the P2, Slack, email, calls and sheet edits

Or run the script directly (it lives in the installed skill's folder):

```
python3 check_plan.py                        # digest for every project
python3 check_plan.py ExampleCo --changes    # one project, plus sheet edits since the last --save
python3 check_plan.py --save                 # save a snapshot
python3 check_plan.py --email you@x.com      # also email the digest
```

For the daily sweep, run `sh install-daily.sh you@example.com` once from your own shell. It installs a launchd job that runs the sweep headless with `claude -p` at 7:30am on weekdays and emails you the digest. `install-daily.sh --digest-only you@example.com` installs a script-only email with no Slack or email sweep; re-run it after a plugin update.

## Install

```
/plugin marketplace add sukottokun/nagomi
/plugin install nagomi@nagomi
```

Your projects and snapshots live in `~/.nagomi/` (`projects.json` and `state/`), outside the plugin, so updates never touch them. Set `NAGOMI_HOME` to keep them somewhere else.

## Setup

- The `gws` CLI, signed in (`gws auth login`), for the sheet and the digest email
- Connectors for Slack, Gmail, Zoom and context-a8c (for the P2)
- Skills from gtm-skills: `admin-call-sourcing`, `admin-customer-drive-folder`, `gtm-discover-p2-notes`, `my-writing-style`
