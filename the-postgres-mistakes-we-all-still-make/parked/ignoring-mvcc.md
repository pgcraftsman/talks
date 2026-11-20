# Parked section: ignoring MVCC (was Mistake #4, the autovacuum math)

Update, 2026-11-17 evening: the idea returned to the deck as Mistake #1 in a different form, the MVCC primer's end state, the jsonb version of the table, and a year of daily logins on one row (`mvcc-bloat`, `mvcc-json`, `mvcc-year`). What stays parked is the autovacuum threshold and cost arithmetic below. Also parked here: `make_mvcc_primer_twelve_steps.py`, the primer with Susie Rivera reusing the freed space and a DELETE of Mike before the row that does not fit. It works; Scott keeps it out of mixed audiences.

Pulled from the PGDay NYC 2026 deck on 2026-11-17, the night before the talk. Scott: the section
is under-developed and will not be covered on 2026-11-18. It may return in a later iteration.

## The argument, as worked out on 2026-11-17

The mistake is not the autovacuum math. The mistake developers make is not considering how the
storage manager will process their workload. Postgres never overwrites a row; every `UPDATE` and
`DELETE` leaves a dead version behind, and the developer who pictures `UPDATE` as an overwrite never
plans for the cleanup. The autovacuum defaults assume a small table and assume none of mistakes 1,
2 and 3 happened.

In the "it's always connections" frame this section is the second thread, dead rows. A dead row is a
connection cost that comes due later: every query that reads the page it sits on holds its connection
a little longer, and vacuum, the thing that removes it, is what mistakes 1 and 2 hold back or bury.

| Mistake | connections | dead rows |
|---|---|---|
| 0 connection storms | one per request | none |
| 1 long-running transactions | held for the wait | kept alive, vacuum can't remove them |
| 2 bulk DELETE | one held for hours | millions created in one pass |
| 3 unused indexes | every write holds longer | a dead index entry per index per update |
| 4 ignoring MVCC | every query holds longer | 200 million left before the first pass |
| 5 plan flips | p99 sessions hold longer | none |
| 6 monitoring | the graph moves last | nothing counts them |

Title candidates considered: "assuming UPDATE is in place" (the mental model, most concrete),
"ignoring the storage manager" (Scott's phrasing), "nobody planned for the dead rows", "ignoring
MVCC" (chosen; the objection is that newcomers will not know what they ignored, so the first line
under the title has to explain it).

To develop before it returns: a real incident (one or two lines), a measurement that shows the
dead versions costing connection time (the laptop cannot show it at 1M rows, see
`charts/data/index-writes/latency.txt` for the same lesson on indexes), and a demo in
`demos/07_autovacuum.sql`, which already exists and stays in the repo.

## Slide, as it stood when pulled (Marp markdown)

```markdown
<!-- _class: kv -->
[//]: # (slide N · ignoring-mvcc)

# Mistake #4: ignoring MVCC

<!-- SCOTT: real incident here, one or two lines.
     The mistake is the mental model: the developer pictures UPDATE as an overwrite and never plans
     for the cleanup. Mistakes 1, 2 and 3 produce the dead versions; the defaults assume none of them happened.
     Cost-limit arithmetic, if asked: autovacuum_vacuum_cost_limit = -1 inherits vacuum_cost_limit = 200,
     spent every autovacuum_vacuum_cost_delay = 2 ms, so 100,000 cost units a second shared by every
     worker, 20 per dirtied page, about 5,000 dirty pages a second or 40 MB/s. A 100 GB heap is about
     42 minutes per pass, indexes extra. -->

Postgres never overwrites a row. Every `UPDATE` and `DELETE` leaves a dead version behind

The defaults wait for 200 million of them before the first vacuum pass

```text
autovacuum_vacuum_threshold = 50      autovacuum_vacuum_scale_factor = 0.2
1,000,000,000 rows × 0.2 + 50  =  200,000,050 dead tuples before the first pass starts
                                  (PG 18+: capped at autovacuum_vacuum_max_threshold = 100,000,000)
```

```sql
ALTER TABLE events SET (autovacuum_vacuum_scale_factor = 0.01,
                        autovacuum_vacuum_threshold   = 10000,
                        autovacuum_vacuum_cost_delay  = 0);     -- this table's worker runs unthrottled
```

|  |  |  |
|---|---|---|
| alerting today | dead tuple ratio > 20% (the outcome) | yes |
|  | large tables still on default autovacuum settings | no |
| verify | `last_autovacuum` advances; `n_dead_tup` falls between samples |  |

<!--
PG 17: the dead-tuple store has no 1 GB cap and uses less memory per tuple; still sized by
autovacuum_work_mem / maintenance_work_mem. autovacuum_max_workers is still 3 and one table
gets one worker; partitioning (Mistake #2) lets each partition cross its own small threshold.
-->

---
```

## Closing-slide row (was on the `efficiency` slide)

| Mistake | What it does to connections | The efficiency fix |
|---|---|---|
| ignoring MVCC | every query reads the dead versions too | plan the cleanup with the workload |

## Catalog row (was on the `catalog` slide)

| Mistake | Already there | Proposed after writing this talk |
|---|---|---|
| Ignoring MVCC | `pg_dead_tuple_pct` | `pg_autovacuum_defaults_on_large_tables` |

## Wednesday-morning item (was item 5)

Per-table autovacuum settings on anything over ten million rows.

## Post copy that was removed

- LinkedIn: "Ignoring MVCC. Postgres never overwrites a row, and on a billion-row table the defaults wait for 200 million dead versions before the first vacuum pass."
- Facebook and Meetup: "forgetting that UPDATE leaves a dead row behind" in the list of topics.
- Reddit: "ignoring MVCC (200 million dead row versions before the first autovacuum pass on a billion-row table)".

Related material still in the repo: `demos/07_autovacuum.sql`, `dashboard-review.md` section 6
(autovacuum), the `defaults` appendix slide, and the vacuum holdback chart on the open-transactions
section, which already shows three autovacuum passes reclaiming nothing while a session is idle in
transaction.
