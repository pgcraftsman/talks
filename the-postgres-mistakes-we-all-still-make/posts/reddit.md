# Reddit post (r/PostgreSQL)

<!-- Image post with posts/banner-1200x675.png, or a text post with the body below. Reddit
     wants plain prose, no hashtags, and a link only where it does work. Event: NYC Postgres
     meetup, Wednesday Nov 18 2026, 6 to 8 pm, 5 Bryant Park. -->

## Title

NYC meetup Wed Nov 18: The Postgres Mistakes We All Still Make (free, Bryant Park, pizza at 6)

## Body

I'm giving a talk at NYC Postgres this Wednesday, November 18, at the Databricks office at 5 Bryant Park. Pizza and networking at 6:00, talk at 6:30, hanging out after until 8:00. Free, RSVP on Meetup: https://www.meetup.com/postgres-nyc/events/317310443/

It starts with connections, because that is where most of the incidents I get paged for start. Postgres runs a process per connection. On my laptop this week, Postgres 17 did about 215,000 simple transactions a second over persistent connections, about 31,000 through pgbouncer, and about 1,400 when the application opened a connection for every transaction. Same box, same query.

From there the talk follows the same thread through the rest of the usual suspects:

- UPDATEs that copy the whole row, and documents that only grow so the copy never fits back
- sessions left idle in transaction, and what they do to vacuum
- bulk DELETE on tables that should have been partitioned
- unused indexes that every UPDATE still has to maintain

Each one comes with the query that detects it and the fix. Developer talk, code and graphs from real runs, no slides full of bullet points. Bring war stories.

If you can't make it, the slides and the detection queries will be on GitHub after the talk and I'll post the link here.
