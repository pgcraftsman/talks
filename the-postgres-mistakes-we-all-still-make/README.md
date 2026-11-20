# The Postgres Mistakes We All Still Make

Talk by Scott Mead (scott@meads.us), NYC Postgres Meetup, November 18 2026.
Slides, charts, the SQL behind the detection slides, and the scripts that build all of it.

**View the slides:** https://pgcraftsman.github.io/talks/the-postgres-mistakes-we-all-still-make/deck/public/slides-postable.html

## Layout

| path | what |
|---|---|
| `deck/slides.md` | The deck, Marp markdown. Speaker notes are HTML comments. |
| `deck/pgslides.css` | Marp theme (imports gaia). |
| `deck/public/` | The published copies: `slides.pdf`, `slides.html`, and `slides-postable.html` with every chart inlined. No notes, no dev tags. |
| `charts/` | Chart generators and their output. `make_charts.py` draws the measured charts from `charts/data/`; the `make_mvcc_*.py` and `make_pool_*.py` scripts draw the MVCC pictures and the three SMIL animations and inline them into the deck. |
| `charts/data/` | Raw measurements: pgbench logs and the pgbouncer config from the connection runs, the vacuum holdback and HOT index series, the index write latency runs. |
| `demos/` | The SQL from the talk. `00_bubble_up.sql` is the one query that checks for every mistake; `01` to `08` are one file per mistake with the detection queries and the fix. |
| `posts/` | The announcement posts and the banner generator. |
| `parked/` | Material cut from the talk for time. |

## Build

Needs Node (for marp-cli, pinned in `deck/package.json`), Python 3.12, and Chrome or Chromium for the PDF and PNG renders.

```
cd deck
npm install
./build.sh          # regenerates the animations, renumbers, renders html/pdf/png, scans for overflow
./publish.sh        # writes the notes-free copies into deck/public/
```

`build.sh` creates `../.venv` with matplotlib and pypdf on first run. Set `CHROME_PATH` if Chrome is not found.
The measured charts are regenerated with `../.venv/bin/python charts/make_charts.py`.

Presenter view: open `deck/slides.html` and press P. The animations pause with `a` and restart with `r`.

## Where the numbers come from

- Connection charts: pgbench on a 10-core laptop, PostgreSQL 17.10, unix sockets, select-only, scale 10, 20 clients. Direct, through pgbouncer 1.26 in transaction mode, and with persistent connections. Logs in `charts/data/pgbench-churn/`.
- Vacuum holdback and HOT index charts: pgbench_accounts with one idle transaction, and an UPDATE workload with and without an index on the updated column. Series in `charts/data/`.
- The jsonb sizes on the MVCC slides are `pg_column_size()` on PostgreSQL 17.
- The index page counts in the appendix are from autovacuum logs of a production PostgreSQL 14 database, May and October 2026, with 62 percent of the rows deleted in between.


## Licence

Slides under CC BY 4.0, SQL and scripts under the PostgreSQL License. See `LICENSE`.
