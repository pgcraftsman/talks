# Facebook post

<!-- Shorter and more casual than LinkedIn. Event: NYC Postgres, Wednesday Nov 18 2026, 6 to 8 pm,
     5 Bryant Park. -->

NYC Postgres folks, I'm speaking at the meetup on Wednesday, November 18. The talk is **The Postgres Mistakes We All Still Make**.

It starts with connections, because that is where most of my incidents start. Postgres runs a process per connection. On my laptop this week, Postgres 17 did about 215,000 simple transactions a second with persistent connections and about 1,400 a second when the app connected for every transaction. From there we go through the rest of the usual suspects. UPDATEs that copy the whole row, transactions left idle, bulk deletes from tables that should have been partitioned, and unused indexes.

It's a developer talk. Code on the screen, graphs from real runs, and a short list of things to check the next morning.

Pizza and networking at 6:00, talk at 6:30, hanging out after until 8:00.

RSVP: https://www.meetup.com/postgres-nyc/events/317310443/
Where: 5 Bryant Park, New York, NY 10018
