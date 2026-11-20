# LinkedIn post

<!-- Event: NYC Postgres meetup, Wednesday Nov 18 2026, 6 to 8 pm, 5 Bryant Park.
     Pizza and networking 6:00 to 6:30, talk 6:30 to 7:30, networking after. -->

Postgres runs a process per connection. After 22 years of being paged for Postgres, connections are where most of my incidents start. On Wednesday, November 18, I'm giving a talk at NYC Postgres called **The Postgres Mistakes We All Still Make**. It's a developer talk. Real code, real graphs, and a detection query for each problem.

I measured the opening on my laptop this week. Postgres 17 ran about 215,000 simple transactions a second over persistent connections. The same box, the same query, with the application connecting for every transaction, ran 1,415. Seven of every fourteen milliseconds went to connecting. Through pgbouncer the same workload ran 31,000. That is the first mistake, and the rest of the talk follows the same thread:

- Ignoring MVCC. Every UPDATE writes a whole new copy of the row, and a document that only grows never fits the space its last version freed.
- Open transactions. A session that sits idle in transaction holds a connection nobody else can use, and it pins vacuum, so the table keeps growing while autovacuum reports success.
- Bulk DELETE instead of partitioning. A nightly DELETE holds one connection for hours, writes a WAL spike, and lags every replica. Dropping a partition is a catalog change.
- Unused indexes. Every UPDATE maintains all of them, so every transaction holds its connection a little longer.

I have made every one of these myself, watched customers make them, or been paged for them. None of them need a new feature to avoid. They need a decision, made ahead of time, about how the application treats the database. You leave with a short list to work through the next morning.

Pizza and networking at 6:00. Talk at 6:30. More networking after.

RSVP: https://www.meetup.com/postgres-nyc/events/317310443/
Where: 5 Bryant Park, New York, NY 10018

#PostgreSQL #PGDayNYC
