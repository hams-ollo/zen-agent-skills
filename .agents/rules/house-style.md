# Zen house style (edit freely)

This file is a **swappable module**. It holds the writing and formatting conventions the Zen Solutions skills assume. It is deliberately separated from the skills themselves so that anyone adopting this kit can replace these rules with their own voice without touching skill logic.

If you are adopting this kit for your own projects: keep this file, empty it, or rewrite it. The skills reference "the house style in `.agents/rules/house-style.md`" rather than hardcoding any specific rule, so whatever you put here is what they enforce.

## Writing

- **No em-dashes.** Use commas, colons, or parentheses. This applies to code comments, documentation, and drafted prose.
- **Sentence case headings.** Write `## Section title`, not `## Section Title`.
- **Name your sources.** Cite the primary author, paper, or developer. Avoid anonymous authority ("studies show", "experts say").
- **Never count the rows of a table in prose beside it.** Name the row instead. "The `house-review` row" survives an insertion; "the fifth row" and "the other four" do not, and neither does "four of them carry a marker". A count written next to the thing it counts looks permanently true and silently stops being true the moment a row is added, which is a change nobody thinks of as touching the prose. Four instances in this repository, each invisible to every gate: `ROADMAP.md` claiming eight autonomy rules and three held candidates against nine and four, `chore-0036` inheriting a claim of ten templates out of nine, and two in `docs/spec/README.md`, one fixed by `chore-0056` and one still open as `chore-0057`. The same reasoning is why `bug-0037` moved conformance-matrix citations off line numbers: a pointer that encodes position drifts when anything above it moves.

## Formatting

- **Markdown links.** Link to files and code symbols with clickable relative links so they resolve inside the repository.
- **Diagrams use Mermaid** fenced code blocks, never ASCII art. Keep labels concise and on one line where possible.

## Scope

These are defaults, not laws. A skill may state a local exception. A downstream adopter may override any of this. The point of pulling it into its own file is that the override is a one-file edit, and no adopter inherits a rule they did not choose.
