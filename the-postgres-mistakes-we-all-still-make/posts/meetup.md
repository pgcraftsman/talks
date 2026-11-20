# Meetup event listing

<!-- Replacement text for the NYC Postgres event page, in the group's house style: a Details
     paragraph and a Speaker line, no agenda or food notes (see their Sep 16 and Jul 8 notices).
     Event: https://www.meetup.com/postgres-nyc/events/317310443/
     Hosts on the page: Mason S. and mila.zhou. Wednesday, November 18, 2026, 6:00 to 8:00 PM EST,
     5 Bryant Park, New York, NY 10018. -->

## Title

The Postgres Mistakes We All Still Make

## Details

Postgres runs a process per connection, and most of the production trouble I get called about starts there. On a laptop, Postgres 17 runs about 215,000 simple transactions a second over persistent connections and about 1,400 a second when the application opens a connection for every transaction. The talk starts with that gap and follows the same thread through MVCC and the rows that never fit back, idle transactions, bulk deletes, and unused indexes. Each mistake comes with the query that detects it and the fix. Bring your own war stories. You leave with code, graphs from real runs, and a short list to take back to work.

**Speaker:** Scott Mead is a Senior Staff Engineer at Databricks, where he works on managed PostgreSQL at scale. He has spent 22 years with Postgres as a user, DBA, developer, and contributor, most of it on production performance.
