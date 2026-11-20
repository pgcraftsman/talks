---
marp: true
theme: default
paginate: true
header: 'Parallel Query is Silently Stealing Your CPU'
footer: 'Scott Mead · Postgres Conference San Jose 2026'
style: |
  :root {
    --color-background:     #2d2d2d;
    --color-background-alt: #383838;
    --color-foreground:     #ececec;
    --color-highlight:      #cc785c;
    --color-dimmed:         #888888;
    --color-border:         #333333;
  }
  section {
    background-color: #2d2d2d;
    color: #ececec;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 28px;
    line-height: 1.5;
    padding: 48px 56px;
  }
  h1 {
    color: #ececec;
    font-size: 1.8em;
    font-weight: 600;
    border-bottom: 2px solid #cc785c;
    padding-bottom: 0.2em;
    margin-bottom: 0.6em;
  }
  h2 {
    color: #ececec;
    font-size: 1.3em;
    font-weight: 600;
    border-bottom: 1px solid #333333;
    padding-bottom: 0.2em;
    margin-bottom: 0.6em;
  }
  h3, h4 {
    color: #cc785c;
    font-weight: 500;
  }
  section.lead {
    background-color: #2d2d2d;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
  }
  section.lead h1 {
    font-size: 2.2em;
    border-bottom: 3px solid #cc785c;
    padding-bottom: 0.3em;
  }
  section.lead h2 {
    color: #cc785c;
    border: none;
    font-size: 1.2em;
    font-weight: 400;
    margin-top: 0.2em;
  }
  section.lead h3, section.lead h4 {
    color: #888888;
    font-weight: 400;
    font-size: 0.9em;
  }
  section.lead p {
    color: #888888;
    font-size: 0.85em;
  }
  pre {
    background-color: #383838;
    border: 1px solid #333333;
    border-left: 3px solid #cc785c;
    border-radius: 6px;
    padding: 0.8em 1em;
    font-size: 0.72em;
    line-height: 1.5;
  }
  code {
    background-color: #383838;
    border-radius: 3px;
    padding: 0.1em 0.3em;
    font-size: 0.85em;
    color: #cc785c;
  }
  pre code {
    background: none;
    padding: 0;
    color: #abb2bf;
  }
  /* atom-one-dark syntax tokens */
  .hljs                   { color: #abb2bf; }
  .hljs-comment,
  .hljs-quote             { color: #5c6370; font-style: italic; }
  .hljs-keyword,
  .hljs-selector-tag,
  .hljs-built_in          { color: #c678dd; }
  .hljs-string,
  .hljs-attr              { color: #98c379; }
  .hljs-number,
  .hljs-literal           { color: #d19a66; }
  .hljs-type,
  .hljs-class .hljs-title { color: #e5c07b; }
  .hljs-function .hljs-title,
  .hljs-title             { color: #61afef; }
  .hljs-variable,
  .hljs-template-variable { color: #e06c75; }
  .hljs-operator,
  .hljs-punctuation       { color: #abb2bf; }
  .hljs-meta              { color: #56b6c2; }
  .hljs-symbol,
  .hljs-bullet            { color: #61afef; }
  .hljs-section           { color: #e06c75; font-weight: bold; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85em;
  }
  th {
    background-color: #383838;
    color: #cc785c;
    font-weight: 600;
    padding: 0.4em 0.8em;
    border-bottom: 2px solid #cc785c;
    text-align: left;
  }
  td {
    padding: 0.4em 0.8em;
    border-bottom: 1px solid #333333;
  }
  tr:nth-child(odd) td {
    background-color: #323232;
  }
  tr:nth-child(even) td {
    background-color: #383838;
  }
  blockquote {
    border-left: 3px solid #cc785c;
    background-color: #383838;
    margin: 0.8em 0;
    padding: 0.6em 1em;
    color: #888888;
    font-style: italic;
    border-radius: 0 6px 6px 0;
  }
  blockquote p { margin: 0; }
  ul, ol { padding-left: 1.4em; }
  li { margin: 0.3em 0; }
  li::marker { color: #cc785c; }
  strong { color: #ececec; font-weight: 700; }
  em { color: #cc785c; font-style: italic; }
  header { color: #888888; font-size: 0.55em; top: 16px; }
  footer { color: #888888; font-size: 0.55em; bottom: 16px; }
  section::after { color: #888888; font-size: 0.55em; }
  small { color: #888888; font-size: 0.65em; }
  hr { border: none; border-top: 1px solid #333333; margin: 1em 0; }
---

<!-- _class: lead -->

# Parallel Query is Silently Stealing Your CPU

### Scott Mead
#### Principal Engineer · Postgres Engines · AWS

**Postgres Conference San Jose 2026**

---

<!-- _class: lead -->

# The Premise

Parallel query is a great feature.
It is also a great way to set your database on fire.

---

## Refresher: how Postgres goes parallel

- Planner sees a query that *might* benefit from parallelism
- Estimates cost with `parallel_setup_cost` + `parallel_tuple_cost`
- If parallel plan wins, executor spawns **N background workers\***
- Workers feed tuples back to the leader via shared memory
- Leader merges, returns result

Sounds great. What could go wrong?

<div style="position:absolute;bottom:24px;right:56px;font-size:1em;color:#888888">* leader is also a worker</div>

---

## Know your defaults

```
max_parallel_workers_per_gather  = 2
max_parallel_workers             = 8
max_worker_processes             = 8
parallel_setup_cost              = 1000
parallel_tuple_cost              = 0.1
min_parallel_table_scan_size     = 8MB
min_parallel_index_scan_size     = 512kB
```

These are active on your cluster right now — whether you knew it or not.

---

<!-- _class: lead -->

# Failure Mode #1
## The "Free Lunch" Myth

---

## The win that isn't

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT event_type, count(*)
FROM events
WHERE created_at >= now() - interval '180 days'
GROUP BY event_type;
```

| Metric | Serial | Parallel (2 workers) |
|---|---|---|
| Wall-clock time | 3 min | **1 min** ✅ |
| Total CPU time | 3 min | **~3 min** ➡ |
| Buffer reads | 6.4M | 6.4M |

Wall-clock dropped. **CPU per query is the same.**
But you're now running 3 processes instead of 1.

---

## Why this matters in production

- Your dashboard latency: down 3×. Looks great.
- Now run **200 concurrent connections** doing the same thing.
- Serial: **200 processes** competing for CPU simultaneously.
- Parallel: **600 processes** competing for CPU simultaneously.
- Same total CPU. Triple the concurrency. Triple the context switching.
- You don't have 600 processes worth of headroom. Welcome to your context-switch nightmare.

> Parallelism is a tradeoff between *latency* and *throughput*.
> The default behavior assumes you only care about latency.

---

<!-- _class: lead -->

# Failure Mode #2
## The Cost of Getting Started

---

## Every connection is a process

Postgres does not use threads. Every client connection is a `fork()`:

- New OS process spawned
- Memory allocated and initialized
- Shared memory attached
- Authentication handshake completed
- Session state established

**All of this before a single row is touched.**

On a well-tuned system with a connection pool, this cost is paid once
and amortized. Without one, it's paid on every request.

---

## Every parallel query pays again

On top of the client connection cost, every parallel query launches
background workers — each one its own `fork()`:

- New OS process spawned
- Dynamic shared memory segment created
- IPC message queues initialized
- Worker registered with postmaster
- Worker connects to DSM and begins execution

`parallel_setup_cost = 1000` is the planner's *model* of this cost.
The actual CPU burn is real and paid at execution time regardless.

---

## Your connection pooler can't fix this

PgBouncer, pgpool, RDS Proxy — they all operate at the **client connection** level.

```
Client → [PgBouncer] → Backend process
                            ↓
                       parallel worker 1  ← fork()
                       parallel worker 2  ← fork()
```

The pooler eliminated the client `fork()`.
It has no visibility into — and no control over —
the workers spawned inside the backend.

**Two separate taxes. The pooler only waives one.**

---

## The compounding problem

A query with **5ms execution time** on a large table might spend:

```
client connection setup:     ~2ms
parallel worker launch (×2):  ~3ms
                             ------
actual query execution:        5ms
                             ------
total wall-clock:             10ms   ← not 5ms
```

Half the wall-clock time is setup, not work.

Now multiply by 500 concurrent requests.
Workers launching, forking, tearing down — constantly.
Your CPU is busy before any data moves.

---

## Detection

```sql
-- Connection churn — new connections being created constantly?
SELECT count(*), state, backend_start::date
FROM pg_stat_activity
GROUP BY state, backend_start::date
ORDER BY backend_start::date DESC;

-- Worker overhead — how many workers active right now?
SELECT count(*) FILTER (WHERE backend_type = 'parallel worker') AS workers,
       count(*) FILTER (WHERE backend_type = 'client backend')  AS clients
FROM pg_stat_activity;
```

If `workers` is a significant fraction of `clients`, you're paying
the parallel setup tax on most of your queries.

---

<!-- _class: lead -->

# Failure Mode #3
## Your Best Customer Gets the Worst Plan

---

## The setup

```sql
SELECT * FROM events WHERE customer_id = 42;
```

100K customers. Events table grows over time.
Each customer accumulates events at roughly the same rate.

At **any normal event count per customer**, the planner
correctly chooses an index scan. Fast. Predictable.

Until it isn't.

---

## The crossover

On a **50GB events table** (250M rows), at **547,000 events** for a single customer:

```
Index Scan cost       = 547,000 × 4.0
                      = 2,188,000

Parallel Seq Scan cost = 1,000
                       + (6,400,000 / 3)
                       + (0.1 × 547,000)
                       = 1,000 + 2,133,333 + 54,700
                       = 2,189,033
```

**Dead even.** One more event tips the balance.
Below **~547K events**: index scan ✅
Above **~547K events**: parallel seq scan

<div style="position:absolute;bottom:24px;right:56px;font-size:1em;color:#888888">* serial seq scan at this table size: 6,400,000 — never competitive</div>

---

## Index cost: the full picture

The crossover slide uses `matching_rows × random_page_cost` — a reasonable
approximation for a low-correlation index. The planner's actual formula:

```
Index Scan cost
  = (index pages × random_page_cost)          -- B-tree traversal
  + (heap pages × effective_page_cost)         -- correlation-adjusted
  + (rows × cpu_index_tuple_cost)              -- 0.005 default
  + (rows × cpu_tuple_cost)                    -- 0.01  default
```

**Correlation** is the key variable. If `customer_id` rows are inserted in
order (e.g. monotonically increasing IDs), heap pages may be nearly sequential
— effective cost approaches `seq_page_cost`. If events are scattered across
the heap, it approaches `random_page_cost`.

---

## Index cost: correlation matters

At 547K rows, **full correlation** (best case for index scan):

```
heap pages fetched  ≈ 547,000 × 1.0   =   547,000   (sequential-like)
index pages         ≈ 1,500   × 4.0   =     6,000
cpu costs           ≈ 547,000 × 0.015 =     8,205
                                       ----------
Total (correlated)                     ≈   561,205   ← index wins easily
```

At 547K rows, **zero correlation** (worst case — events scattered across heap):

```
heap pages fetched  ≈ 547,000 × 4.0   = 2,188,000   (fully random)
index pages         ≈ 1,500   × 4.0   =     6,000
cpu costs           ≈ 547,000 × 0.015 =     8,205
                                       ----------
Total (uncorrelated)                   ≈ 2,202,205   ← dead even with parallel
```

For an events table with scattered inserts per customer, correlation is low.
The approximation holds. On a perfectly ordered table, the crossover
threshold would be much higher — or might never be reached.

---

## Why this is silent

- 99,999 customers get index scans — fast, cheap, invisible
- 1 customer crosses **547K events** — parallel seq scan kicks in
- The query still returns correct results
- Nothing in the slow query log
- `pg_stat_statements` average looks fine — diluted by 99,999 fast queries
- **Your most active customer gets the worst plan**

---

## The plan before and after

**Under 547K events — Index Scan:**
```
Index Scan on events  (cost=0.00..10,000 rows=500,000)
  Index Cond: (customer_id = 42)
```

**Over 547K events — silent flip:**
```
Gather  (cost=1000.00..2134583.00 rows=547000)
  Workers Planned: 2
  Workers Launched: 2
  ->  Parallel Seq Scan on events
        Filter: (customer_id = 42)
```

Same query. Same index. Different plan.
Latency goes from **milliseconds to seconds**.
Nobody changed anything.

---

## What your customer experiences

```
Browser                 App Server            Postgres
  |                         |                    |
  |--- GET /dashboard ----→ |                    |
  |                         |--- SELECT events --→|
  |                         |                    | [fork worker 1]
  |                         |                    | [fork worker 2]
  |                         |                    |   ... scanning ...
  |                         |                    |   ... scanning ...
  |      (~13 seconds)      |                    |   ... scanning ...
  |                         |                    |   ... scanning ...
  |                         |                    | [workers return]
  |                         |←-- 547K rows ------||
  |←-- page renders ------  |                    |
```

Your most active customer hits their dashboard.
The page spinner runs for **13 seconds**.
Index scan was milliseconds. Nothing changed except event count.

They didn't do anything wrong.
You didn't deploy anything.
The database is working exactly as designed.

---

## This is the default behavior

You haven't misconfigured anything.
Nobody lowered any cost parameters.
This is a **stock Postgres install**:

```
parallel_setup_cost  = 1000   -- sounds expensive
parallel_tuple_cost  = 0.1    -- doesn't sound like much
min_parallel_table_scan_size = 8MB
```

The planner is doing exactly what it's designed to do.
Your data grew into a shape the defaults weren't built for.

---

<!-- _class: lead -->

# Failure Mode #4
## Worker Pool Exhaustion

---

## The math nobody does

```
max_parallel_workers_per_gather = 2   -- default
max_parallel_workers            = 8   -- default
```

- 1 query → 2 workers ✅
- 2 queries → 4 workers ✅
- 3 queries → 6 workers ✅
- 4 queries → 8 workers ✅
- **5th query** → **0 workers launched**

The 5th query already paid `parallel_setup_cost` in planning.
And now... it doesn't fall back to serial. It does something worse.

---

## It does NOT fall back to serial

When workers can't launch, Postgres does **not** re-plan.

The leader executes **the same parallel plan** — alone, in one process.

> "the leader will execute the portion of the plan below the
>  Gather node entirely by itself, almost as if the Gather node
>  were not present."
> — PostgreSQL docs, §15.2

---

## Why this is worse than "just serial"

The planner picked Parallel Seq Scan **because** it assumed 4 workers.

That math beat the Index Scan it would have picked otherwise.

```
Workers Planned: 4
Workers Launched: 0      ← the smoking gun
->  Parallel Seq Scan on events  (250M rows, single-threaded)
```

You're not running a serial plan.
You're running **a parallel plan, serially**, on a single core,
that was only chosen because parallelism was assumed.

It's worse than disabling parallelism entirely.

---

## What you actually see

```sql
SELECT pid, backend_type, wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE backend_type IN ('client backend', 'parallel worker');
```

- 8 parallel workers pegged
- 12 client backends in `IPC: ExecuteGather`
- Nothing in the slow query log
- `pg_stat_statements.mean_exec_time` looks "normal-ish"
- Your customers are timing out

---

## The pile-on

<svg width="100%" viewBox="0 0 680 340" xmlns="http://www.w3.org/2000/svg"><defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M2 2L8 5L2 8" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker></defs><rect x="40" y="36" width="52" height="28" rx="5" fill="#444441" stroke="#5F5E5A" stroke-width="0.5"/><rect x="40" y="46" width="52" height="2" rx="1" fill="#888780"/><text font-family="sans-serif" font-size="12" x="66" y="57" text-anchor="middle" dominant-baseline="central" fill="#D3D1C7">client</text><rect x="40" y="74" width="52" height="28" rx="5" fill="#444441" stroke="#5F5E5A" stroke-width="0.5"/><rect x="40" y="84" width="52" height="2" rx="1" fill="#888780"/><text font-family="sans-serif" font-size="12" x="66" y="95" text-anchor="middle" dominant-baseline="central" fill="#D3D1C7">client</text><rect x="40" y="112" width="52" height="28" rx="5" fill="#444441" stroke="#5F5E5A" stroke-width="0.5"/><rect x="40" y="122" width="52" height="2" rx="1" fill="#888780"/><text font-family="sans-serif" font-size="12" x="66" y="133" text-anchor="middle" dominant-baseline="central" fill="#D3D1C7">client</text><rect x="40" y="150" width="52" height="28" rx="5" fill="#633806" stroke="#EF9F27" stroke-width="1"/><rect x="40" y="160" width="52" height="2" rx="1" fill="#EF9F27"/><text font-family="sans-serif" font-size="12" x="66" y="171" text-anchor="middle" dominant-baseline="central" fill="#FAC775">cust 42</text><rect x="40" y="188" width="52" height="28" rx="5" fill="#501313" stroke="#E24B4A" stroke-width="0.5" stroke-dasharray="3 2"/><rect x="40" y="198" width="52" height="2" rx="1" fill="#E24B4A"/><text font-family="sans-serif" font-size="12" x="66" y="209" text-anchor="middle" dominant-baseline="central" fill="#F09595">retry</text><rect x="40" y="226" width="52" height="28" rx="5" fill="#501313" stroke="#E24B4A" stroke-width="0.5" stroke-dasharray="3 2"/><rect x="40" y="236" width="52" height="2" rx="1" fill="#E24B4A"/><text font-family="sans-serif" font-size="12" x="66" y="247" text-anchor="middle" dominant-baseline="central" fill="#F09595">retry</text><text font-family="sans-serif" font-size="12" x="66" y="278" text-anchor="middle" fill="#888780">clients</text><line x1="92" y1="50" x2="200" y2="100" stroke="#5F5E5A" stroke-width="1" marker-end="url(#arr)"/><line x1="92" y1="88" x2="200" y2="120" stroke="#5F5E5A" stroke-width="1" marker-end="url(#arr)"/><line x1="92" y1="126" x2="200" y2="140" stroke="#5F5E5A" stroke-width="1" marker-end="url(#arr)"/><line x1="92" y1="164" x2="200" y2="160" stroke="#EF9F27" stroke-width="1.5" marker-end="url(#arr)"/><line x1="92" y1="202" x2="200" y2="180" stroke="#E24B4A" stroke-width="1" stroke-dasharray="4 2" marker-end="url(#arr)"/><line x1="92" y1="240" x2="200" y2="200" stroke="#E24B4A" stroke-width="1" stroke-dasharray="4 2" marker-end="url(#arr)"/><rect x="200" y="80" width="110" height="170" rx="12" fill="#26215C" stroke="#7F77DD" stroke-width="1"/><text font-family="sans-serif" font-size="14" font-weight="600" x="255" y="100" text-anchor="middle" dominant-baseline="central" fill="#CECBF6">PgBouncer</text><text font-family="sans-serif" font-size="12" x="255" y="116" text-anchor="middle" fill="#AFA9EC">connection pool</text><text font-family="sans-serif" font-size="12" x="255" y="136" text-anchor="middle" fill="#7F77DD">80/100 free</text><rect x="215" y="148" width="16" height="10" rx="2" fill="#534AB7"/><rect x="234" y="148" width="16" height="10" rx="2" fill="#534AB7"/><rect x="253" y="148" width="16" height="10" rx="2" fill="#534AB7"/><rect x="272" y="148" width="16" height="10" rx="2" fill="#534AB7"/><rect x="291" y="148" width="16" height="10" rx="2" fill="#534AB7"/><rect x="215" y="162" width="16" height="10" rx="2" fill="#534AB7"/><rect x="234" y="162" width="16" height="10" rx="2" fill="#534AB7"/><rect x="253" y="162" width="16" height="10" rx="2" fill="#534AB7"/><rect x="272" y="162" width="16" height="10" rx="2" fill="#3C3489" opacity="0.4"/><rect x="291" y="162" width="16" height="10" rx="2" fill="#3C3489" opacity="0.4"/><text font-family="sans-serif" font-size="12" x="255" y="192" text-anchor="middle" fill="#AFA9EC">retries holding</text><text font-family="sans-serif" font-size="12" x="255" y="206" text-anchor="middle" fill="#AFA9EC">slots open</text><text font-family="sans-serif" font-size="12" x="255" y="263" text-anchor="middle" fill="#7F77DD">pool</text><line x1="310" y1="120" x2="390" y2="130" stroke="#5F5E5A" stroke-width="1" marker-end="url(#arr)"/><line x1="310" y1="145" x2="390" y2="155" stroke="#5F5E5A" stroke-width="1" marker-end="url(#arr)"/><line x1="310" y1="165" x2="390" y2="175" stroke="#5F5E5A" stroke-width="1" marker-end="url(#arr)"/><line x1="310" y1="185" x2="390" y2="195" stroke="#EF9F27" stroke-width="1.5" marker-end="url(#arr)"/><line x1="310" y1="205" x2="390" y2="215" stroke="#E24B4A" stroke-width="1" stroke-dasharray="4 2" marker-end="url(#arr)"/><line x1="310" y1="220" x2="390" y2="230" stroke="#E24B4A" stroke-width="1" stroke-dasharray="4 2" marker-end="url(#arr)"/><rect x="390" y="100" width="170" height="160" fill="#085041" stroke="#1D9E75" stroke-width="0.5"/><ellipse cx="475" cy="100" rx="85" ry="16" fill="#0F6E56" stroke="#1D9E75" stroke-width="0.5"/><ellipse cx="475" cy="260" rx="85" ry="16" fill="#085041" stroke="#1D9E75" stroke-width="0.5"/><text font-family="sans-serif" font-size="14" font-weight="600" x="475" y="124" text-anchor="middle" dominant-baseline="central" fill="#9FE1CB">Postgres</text><text font-family="sans-serif" font-size="12" x="475" y="145" text-anchor="middle" fill="#5DCAA5">worker pool  8/8</text><circle cx="425" cy="162" r="8" fill="#A32D2D" stroke="#E24B4A" stroke-width="0.5"/><circle cx="448" cy="162" r="8" fill="#A32D2D" stroke="#E24B4A" stroke-width="0.5"/><circle cx="471" cy="162" r="8" fill="#A32D2D" stroke="#E24B4A" stroke-width="0.5"/><circle cx="494" cy="162" r="8" fill="#A32D2D" stroke="#E24B4A" stroke-width="0.5"/><circle cx="425" cy="184" r="8" fill="#A32D2D" stroke="#E24B4A" stroke-width="0.5"/><circle cx="448" cy="184" r="8" fill="#A32D2D" stroke="#E24B4A" stroke-width="0.5"/><circle cx="471" cy="184" r="8" fill="#A32D2D" stroke="#E24B4A" stroke-width="0.5"/><circle cx="494" cy="184" r="8" fill="#A32D2D" stroke="#E24B4A" stroke-width="0.5"/><text font-family="sans-serif" font-size="12" x="475" y="213" text-anchor="middle" fill="#E24B4A">EXHAUSTED</text><text font-family="sans-serif" font-size="12" x="475" y="228" text-anchor="middle" fill="#F09595">new queries run</text><text font-family="sans-serif" font-size="12" x="475" y="242" text-anchor="middle" fill="#F09595">single-core</text><text font-family="sans-serif" font-size="12" x="475" y="288" text-anchor="middle" fill="#1D9E75">postgres</text><line x1="66" y1="178" x2="66" y2="296" stroke="#EF9F27" stroke-width="0.5" stroke-dasharray="3 2"/><text font-family="sans-serif" font-size="11" x="66" y="306" text-anchor="middle" fill="#EF9F27">13s query</text><text font-family="sans-serif" font-size="11" x="66" y="320" text-anchor="middle" fill="#BA7517">plan flipped</text><rect x="490" y="36" width="10" height="10" rx="2" fill="#444441" stroke="#5F5E5A" stroke-width="0.5"/><text font-family="sans-serif" font-size="11" x="506" y="45" fill="#888780">normal client</text><rect x="490" y="54" width="10" height="10" rx="2" fill="#633806" stroke="#EF9F27" stroke-width="1"/><text font-family="sans-serif" font-size="11" x="506" y="63" fill="#EF9F27">customer 42</text><rect x="490" y="72" width="10" height="10" rx="2" fill="#501313" stroke="#E24B4A" stroke-width="0.5"/><text font-family="sans-serif" font-size="11" x="506" y="81" fill="#F09595">retry</text><circle cx="495" cy="97" r="5" fill="#A32D2D" stroke="#E24B4A" stroke-width="0.5"/><text font-family="sans-serif" font-size="11" x="506" y="101" fill="#F09595">worker (exhausted)</text></svg>

One customer. One plan flip. A connection storm that takes down the service.

---

## The problem with EXPLAIN

`EXPLAIN ANALYZE` shows `Workers Planned: 2, Workers Launched: 0` —
but only **if you run it while the system is under load**.

Run it on an idle box and workers launch just fine.
The problem disappears. You find nothing.

This is not a debugging tool for worker exhaustion.
You need **cumulative counters**, not point-in-time plans.

---

## pg_stat_database + pg_stat_statements (PG 18+)


```sql
-- Cluster-level: is the pool being starved?
SELECT datname,
       parallel_workers_to_launch,
       parallel_workers_launched,
       parallel_workers_to_launch
         - parallel_workers_launched AS gap
FROM pg_stat_database
WHERE datname = current_database();

-- Query-level: which queries are losing workers?
SELECT query,
       parallel_workers_to_launch,
       parallel_workers_launched,
       parallel_workers_to_launch
         - parallel_workers_launched AS gap
FROM pg_stat_statements
WHERE parallel_workers_to_launch > 0
ORDER BY gap DESC
LIMIT 10;
```


---

<!-- _class: lead -->

# Failure Mode #5
## Parallel Append × Partitions

---

## A multiplier you didn't ask for

```sql
CREATE TABLE events_part (...) PARTITION BY RANGE (created_at);
-- 12 monthly partitions, growing every month
```

```sql
SELECT event_type, count(*) FROM events_part GROUP BY event_type;
```

```
Finalize GroupAggregate
  -> Gather (workers planned: 2)
    -> Parallel Append
      -> Parallel Seq Scan on events_p202504
      -> Parallel Seq Scan on events_p202505
      ... 12 partitions ...
```

2 workers shared across 12 partitions — not 2 per partition.
But the number of workers *requested* scales with partition count.

---

## And it grows over time

The number of workers requested scales roughly logarithmically with partition count.

| Partitions | Workers requested |
|---|---|
| 6 | 2 |
| 12 | 3 |
| 24 | 4 |
| 48 | 5 |

That number is capped by `max_parallel_workers_per_gather` — but as partitions grow, the planner keeps asking for more. Nobody noticed the partition count doubled. Nobody re-audited the plan. The query just got slower and hungrier.

> Parallel features compound. Audit them when your data shape changes.

<div style="position:absolute;bottom:24px;right:56px;font-size:0.6em;color:#888888">* Postgres also factors in partition size via compute_parallel_worker()</div>

---

<!-- _class: lead -->

# Detection

How do you find this in your fleet today?

---

## Find the suspects

```sql
-- Live: are workers being starved right now?
SELECT count(*) FILTER (WHERE backend_type = 'parallel worker') AS workers,
       count(*) FILTER (WHERE state = 'active')                 AS active_clients
FROM pg_stat_activity;

-- Live: who is waiting on parallel infrastructure?
SELECT pid, wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE wait_event IN ('BgWorkerShutdown', 'BgWorkerStartup', 'ExecuteGather', 'ParallelFinish');
```

If `workers` is regularly at `max_parallel_workers`, you have a problem.
Sessions on `ExecuteGather` are blocked waiting for parallel results.
Sessions on `ParallelFinish` are waiting for workers to finish and clean up.
Sessions on `BgWorkerStartup` / `BgWorkerShutdown` are in worker lifecycle overhead.

---

## Find the suspects (PG 18+)

```sql
-- Cumulative: which queries are losing workers?
SELECT query,
       parallel_workers_to_launch,
       parallel_workers_launched,
       parallel_workers_to_launch
         - parallel_workers_launched AS gap
FROM pg_stat_statements
WHERE parallel_workers_to_launch > 0
ORDER BY gap DESC
LIMIT 10;

-- Cumulative: is the pool being starved cluster-wide?
SELECT datname,
       parallel_workers_to_launch,
       parallel_workers_launched,
       parallel_workers_to_launch
         - parallel_workers_launched AS gap
FROM pg_stat_database
WHERE datname = current_database();
```

A persistent gap means queries are silently running parallel plans on a single core.

---

<!-- _class: lead -->

# Taking Back Control

---

## The philosophy

Parallel query has its place.

If a query, data model, and data distribution are designed correctly,
it can provide tangible benefits.

The trick is ensuring **you** are in control of the parallelism
in use at any given time — **globally, across the cluster**.

The problem with every partial fix is the same:
you can't bound total worker count across concurrent sessions.

---

## Step 1: Disable globally

```sql
-- postgresql.conf / ALTER SYSTEM
ALTER SYSTEM SET max_parallel_workers_per_gather = 0;
SELECT pg_reload_conf();
```

This is not the nuclear option. **This is the baseline.**

Parallel query is now off for all workloads, all users, all tables.
Nothing happens without your explicit permission.

---

## Step 2: Enable intentionally

**Per-query, using session variables:**
```sql
SET max_parallel_workers_per_gather = 4;
SELECT count(*) FROM events WHERE created_at > now() - interval '1 year';
RESET max_parallel_workers_per_gather;
```

**Per-query, using pg_hint_plan:**
```sql
/*+ Parallel(events 4 hard) */
SELECT count(*) FROM events WHERE created_at > now() - interval '1 year';
```

`hard` means use exactly 4 workers — not "up to 4".
You asked for it. You got it. Nothing surprises you.

<small>pg_hint_plan docs: https://pg-hint-plan.readthedocs.io/en/latest/hint_details.html</small>

---

## Step 3: Enable per-user or per-database

Only if you can **guarantee a max concurrency count**.

```sql
-- Analytical user gets parallelism, OLTP users don't
ALTER ROLE analyst SET max_parallel_workers_per_gather = 4;

-- Or scope to a specific database
ALTER DATABASE analytics SET max_parallel_workers_per_gather = 4;
```

If 10 analyst sessions can run concurrently and each gets 4 workers,
you need `max_parallel_workers ≥ 40`. Know your math before you enable.

---

## Why per-table is not enough

```sql
ALTER TABLE events SET (parallel_workers = 4);
```

This caps workers *per query on this table*.
It does not cap *total workers across all concurrent sessions*.

10 sessions hit `events` simultaneously → up to 40 workers.
You have no cluster-level guarantee.

And when that 11th session arrives and the worker pool is exhausted?
Your analyst gets no error. No warning. No slow query log entry.
They get a parallel plan running on a single CPU —
**untraceable, silent, and slower than if parallelism had never been enabled.**

In a mixed workload system, per-table settings trade
one instability for another.

---

<!-- _class: lead -->

# Takeaways

---

## What to do Monday morning

1. **Disable parallel query globally.** Make it your baseline, not your last resort.
2. **Re-enable intentionally** — per-query via session GUCs or `pg_hint_plan`.
3. **Per-user or per-database** only when you can bound concurrency.
4. **Add a worker-count panel** to your monitoring — `pg_stat_activity`.
5. **Watch for `Workers Launched: 0`** — the silent parallel plan with no workers.

> Parallelism is not opt-in by default.
> Make it opt-in by design.

---

<!-- _class: lead -->

# Questions?

**Scott Mead** · meads@amazon.com