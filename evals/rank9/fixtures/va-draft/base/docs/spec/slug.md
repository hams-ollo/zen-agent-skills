---
status: draft
---

# Slug spec

## Scenarios

- **S-001.** Given a title with capitals, when it is slugified, then the slug is lowercase.
- **S-002.** Given a title with a run of spaces or punctuation between words, when it is slugified,
  then that run becomes exactly one hyphen.
- **S-003.** Given a title that starts or ends with punctuation, when it is slugified, then the slug
  neither starts nor ends with a hyphen.
