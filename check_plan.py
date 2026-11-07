#!/usr/bin/env python3
"""Critical-chain status check for every project's 'Project Plan' tab.

Schedules the open work from Depends on + one-task-at-a-time owners, finds the
critical chain (the longest path through that schedule), and reports buffer
health, the chain in order, each owner's next tasks, blocked work, missing
estimates or owners, and sheet edits since the last saved snapshot.

Usage:
  check_plan.py                      digest for all projects in projects.json
  check_plan.py ExampleCo               one project
  check_plan.py --changes            also list sheet edits since the last --save
  check_plan.py --save               save a snapshot for the next --changes
  check_plan.py --email me@x.com     also email the digest (via gws gmail +send)
"""
import argparse, datetime as dt, json, math, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state")
TAB = "Project Plan"
MAX_IN_PROGRESS = 2  # critical chain: one task at a time, two at most
KEYS = ("milestone", "task", "owner", "done when", "status", "chain", "days left", "done on", "depends on", "notes")
TRACKED = ("owner", "status", "days left", "done on", "depends on", "notes")


def gws(*args):
    return subprocess.run(["gws", *args], capture_output=True, text=True, check=True).stdout


def read_plan(sheet_id):
    rows = json.loads(gws("sheets", "+read", "--spreadsheet", sheet_id, "--range", f"'{TAB}'!A1:Z300")).get("values", [])
    head = [h.strip().lower() for h in rows[0]]
    head[0] = "milestone"  # first column is always the milestone, whatever its header says
    get = lambda r, k: (r[head.index(k)].strip() if k in head and head.index(k) < len(r) else "")
    tasks = [{k: get(r, k) for k in KEYS} | {"row": i + 2}
             for i, r in enumerate(rows[1:]) if len(r) > 1 and r[1].strip()]
    return tasks, head


OFF = set()  # non-working dates for the project being checked (projects.json "off")
is_workday = lambda d: d.weekday() < 5 and d.isoformat() not in OFF


def workdays(start, end):
    d, n = start, 0
    while d < end:
        d += dt.timedelta(days=1)
        n += is_workday(d)
    return n


def add_workdays(start, n):
    d, n = start, math.ceil(n)
    while n > 0:
        d += dt.timedelta(days=1)
        n -= is_workday(d)
    return d


def days(t):
    try:
        return float(t["days left"])
    except ValueError:
        return None


is_buffer = lambda t: t["task"].lower().startswith("project buffer")
is_done = lambda t: t["status"].lower() == "done"
is_post = lambda t: t["milestone"].lower().lstrip("0123456789. ").startswith("post")
is_chain_flag = lambda t: t["chain"].upper() in ("Y", "TRUE")


def resolve_deps(tasks):
    """Depends on holds task names separated by ';' (names can contain commas). A unique prefix is enough."""
    by_name = {t["task"].lower(): t for t in tasks}
    deps, bad = {}, []
    for t in tasks:
        deps[t["row"]] = []
        for d in filter(None, (s.strip().lower() for s in t["depends on"].split(";"))):
            hits = [by_name[d]] if d in by_name else [v for k, v in by_name.items() if k.startswith(d)]
            if len(hits) == 1:
                deps[t["row"]].append(hits[0]["row"])
            else:
                bad.append(f"{t['task']}: '{d}' {'matches no task' if not hits else 'is ambiguous'}")
    return deps, bad


def schedule(tasks):
    """Serial schedule: longest remaining path first, each owner one task at a time.
    Returns start/finish (working days from today), the chain in order, and any cycle."""
    work = [t for t in tasks if not is_buffer(t) and not is_post(t)]
    rows = {t["row"]: t for t in work}
    deps, bad = resolve_deps(tasks)
    deps = {r: [d for d in deps[r] if d in rows] for r in rows}
    dur = {r: 0.0 if is_done(t) else (days(t) or 0.0) for r, t in rows.items()}
    succ = {r: [s for s in rows if r in deps[s]] for r in rows}

    tail, cycle = {}, []
    def tail_of(r, seen=()):
        if r in seen:
            cycle.append(rows[r]["task"])
            return 0.0
        if r not in tail:
            tail[r] = dur[r] + max((tail_of(s, seen + (r,)) for s in succ[r]), default=0.0)
        return tail[r]
    for r in rows:
        tail_of(r)

    start, finish, prev_by_owner, owner_free, owner_last = {}, {}, {}, {}, {}
    pending = set(rows)
    while pending:
        ready = [r for r in pending if all(d in finish for d in deps[r])]
        if not ready:
            cycle.extend(rows[r]["task"] for r in pending)
            break
        # earliest possible start first (no idle gaps), then longest path left, then work already started
        earliest = lambda r: max([finish[d] for d in deps[r]] + [owner_free.get(rows[r]["owner"].lower(), 0.0) if dur[r] else 0.0])
        r = min(ready, key=lambda r: (earliest(r), -tail[r], rows[r]["status"].lower() != "in progress", r))
        pending.discard(r)
        owner = rows[r]["owner"].lower()
        es = max((finish[d] for d in deps[r]), default=0.0)
        if dur[r] and owner:
            if owner_free.get(owner, 0.0) > es:
                es, prev_by_owner[r] = owner_free[owner], owner_last[owner]
            owner_free[owner], owner_last[owner] = es + dur[r], r
        start[r], finish[r] = es, es + dur[r]

    chain = []
    if finish:
        r = max(finish, key=lambda r: (finish[r], -r))
        while r is not None and finish[r] > 0:
            chain.append(r)
            binding = [d for d in deps[r] if finish[d] == start[r] and finish[d] > 0]
            r = binding[0] if binding else prev_by_owner.get(r) if start[r] > 0 else None
        chain.reverse()
    return start, finish, chain, bad, sorted(set(cycle))


def changes(name, tasks):
    path = os.path.join(STATE, f"{name}.json")
    if not os.path.exists(path):
        return ["  (no saved snapshot yet; run with --save)"]
    old = json.load(open(path))
    new = {t["task"]: {k: t[k] for k in TRACKED} for t in tasks}
    out = [f"  + {n}" for n in new if n not in old["tasks"]] + [f"  - {n}" for n in old["tasks"] if n not in new]
    for n, cur in new.items():
        for k in TRACKED:
            was = old["tasks"].get(n, {}).get(k, cur[k])
            if was != cur[k]:
                out.append(f"  - {n}: {k} '{was}' -> '{cur[k]}'")
    return [f"  since {old['saved']}"] + (out or ["  none"])


def save(name, tasks):
    os.makedirs(STATE, exist_ok=True)
    snap = {"saved": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "tasks": {t["task"]: {k: t[k] for k in TRACKED} for t in tasks}}
    json.dump(snap, open(os.path.join(STATE, f"{name}.json"), "w"), indent=1)


def digest(name, cfg, today, a):
    OFF.clear()
    OFF.update(cfg.get("off", []))
    tasks, head = read_plan(cfg["sheet"])
    real = [t for t in tasks if not is_buffer(t)]
    open_ = [t for t in real if not is_done(t)]
    start, finish, chain, bad, cycle = schedule(tasks)
    by_row = {t["row"]: t for t in tasks}
    chain_left = max(finish.values(), default=0.0)
    on_chain = set(chain)

    lines = [f"{name}: {len(real) - len(open_)}/{len(real)} tasks done",
             f"https://docs.google.com/spreadsheets/d/{cfg['sheet']}/edit"]
    headline = f"chain {chain_left:g} days left"
    if cfg.get("launch") and cfg.get("buffer"):
        launch = dt.date.fromisoformat(cfg["launch"])
        avail = workdays(today, launch)
        used = max(0.0, (cfg["buffer"] - (avail - chain_left)) / cfg["buffer"])
        color = "GREEN" if used < 1 / 3 else "YELLOW" if used < 2 / 3 else "RED"
        headline = f"{color}, buffer {used:.0%} used"
        lines.append(f"\nBuffer: {color}. {used:.0%} of {cfg['buffer']} days used. "
                     f"Chain has {chain_left:g} days left (done {add_workdays(today, chain_left):%m/%d}); "
                     f"{avail} working days to launch {launch:%m/%d}.")

    def section(label, items, fmt=lambda t: f"{t['task']} ({t['owner'] or 'no owner'})"):
        if items:
            lines.append(f"\n{label} ({len(items)})")
            lines.extend(f"  - {fmt(t)} [row {t['row']}]" for t in items)

    when = lambda r: f"{add_workdays(today, start[r]):%m/%d}-{add_workdays(today, finish[r]):%m/%d}"
    section("Critical chain, in order", [by_row[r] for r in chain],
            lambda t: f"{t['task']} ({t['owner'] or 'no owner'}, {t['days left'] or '?'}d, {t['status'] or 'no status'}, {when(t['row'])})")
    section("Blocked on the chain", [t for t in open_ if t["row"] in on_chain and t["status"].lower() == "blocked"])
    section("Blocked off the chain", [t for t in open_ if t["row"] not in on_chain and t["status"].lower() == "blocked"])

    queues = {}
    for r in sorted((r for r in start if not is_done(by_row[r]) and by_row[r]["owner"]), key=lambda r: (start[r], r)):
        queues.setdefault(by_row[r]["owner"], []).append(by_row[r])
    if queues:
        lines.append("\nNext up by owner")
        lines.extend(f"  - {o}: " + "; ".join(f"{t['task']}{' (chain)' if t['row'] in on_chain else ''}" for t in q[:2])
                     for o, q in queues.items())

    flagged = {t["row"] for t in real if is_chain_flag(t)}
    if flagged != on_chain:
        section("Computed chain differs from the Chain column (yours to decide)",
                [by_row[r] for r in sorted(flagged ^ on_chain)],
                lambda t: f"{t['task']}: {'now on' if t['row'] in on_chain else 'no longer on'} the chain")
    section("No estimate (Days left)", [t for t in open_ if days(t) is None and not is_post(t)])
    section("No owner", [t for t in open_ if not t["owner"]])
    section("No status", [t for t in open_ if not t["status"]])
    if not any(t["depends on"] for t in tasks):
        lines.append("\nNo Depends on entries yet, so order and chain are owner queues only.")
    if bad or cycle:
        lines.append("\nDepends on problems")
        lines.extend(f"  - {b}" for b in bad)
        if cycle:
            lines.append(f"  - Cycle through: {', '.join(cycle)}")

    busy = {}
    for t in open_:
        if t["status"].lower() == "in progress" and t["owner"]:
            busy.setdefault(t["owner"], []).append(t["task"])
    over = {o: ts for o, ts in busy.items() if len(ts) > MAX_IN_PROGRESS}
    if over:
        lines.append(f"\nToo much in progress (more than {MAX_IN_PROGRESS})")
        lines.extend(f"  - {o}: {len(ts)} tasks ({', '.join(ts)})" for o, ts in over.items())

    if a.changes:
        lines.append("\nSheet changes")
        lines.extend(changes(name, tasks))
    if a.save:
        save(name, tasks)
    return f"{name}: {headline}", "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?")
    ap.add_argument("--email")
    ap.add_argument("--changes", action="store_true")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    projects = json.load(open(os.path.join(HERE, "projects.json")))
    if a.project:
        projects = {a.project: projects[a.project]}
    today = dt.date.today()
    heads, bodies = zip(*(digest(n, c, today, a) for n, c in projects.items()))
    body = "\n\n".join(bodies)
    print(body)
    if a.email:
        subject = f"WooEnterprise PM {today:%m/%d}: " + "; ".join(heads)
        r = subprocess.run(["gws", "gmail", "+send", "--to", a.email, "--subject", subject, "--body", body],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"\nEmail failed: {(r.stderr or r.stdout).strip().splitlines()[-1]}")
        print(f"\nEmailed {a.email}", file=sys.stderr)


if __name__ == "__main__":
    main()
