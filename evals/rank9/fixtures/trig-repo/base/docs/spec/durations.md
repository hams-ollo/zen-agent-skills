---
status: approved
---

# Retry spec

- **S-001.** Given a function that always fails, when `retry(func, attempts=3)` runs, then the
  function is called exactly three times and the last error propagates.
- **S-002.** Given three retries, when delays are computed, then each delay is at most 10% above
  `base * 2 ** attempt`.
