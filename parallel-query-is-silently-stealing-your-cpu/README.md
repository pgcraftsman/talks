# Parallel Query is Silently Stealing Your CPU

Talk by Scott Mead, Postgres Conference San Jose, April 2026.
Three ways parallel query quietly costs you CPU, and how to detect and tune each one.

**View the slides:** https://pgcraftsman.github.io/talks/parallel-query-is-silently-stealing-your-cpu/deck/public/slides.html

## Layout

| path | what |
|---|---|
| `deck/slides.md` | The deck, Marp markdown. Styles and the diagram are inline, so it has no other files. |
| `deck/public/slides.pdf` | PDF render of `deck/slides.md`. The conference posted an earlier copy with my AWS title and email. |
| `deck/public/slides.html` | HTML render of `deck/slides.md`. |

## Build

```
cd deck
npx @marp-team/marp-cli@4.5.1 slides.md --html -o public/slides.html
npx @marp-team/marp-cli@4.5.1 slides.md --html --pdf -o public/slides.pdf
```

`--html` is needed for the inline SVG. The PDF render needs Chrome or Chromium (set `CHROME_PATH` if it is not found).

## Licence

Slides under CC BY 4.0, any code under the PostgreSQL License. See `LICENSE`.
