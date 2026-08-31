#!/usr/bin/env python3
"""Reading a text file this toolchain owns, and saying so when it is not UTF-8.

Every file the distribution tooling reads is UTF-8 by contract. Eleven sites across four
scripts read one with `encoding="utf-8"` and no handler, so a single stray byte anywhere in
a skill body, a rules lens, a task file or a manifest killed the run on a `UnicodeDecodeError`
traceback that named no file and read as a defect in the tool (`chore-0081`).

The failure is the one [`check-provenance.py`](check-provenance.py) reasons about and avoids
in its own fetch path: "A traceback here would read as a defect in this script rather than as
the network being down, which is the common case by a wide margin." The hooks module avoids it
too. The distribution tooling was the inconsistent half, and it is the half a file from outside
this repository reaches first.

Why not `errors="ignore"`
-------------------------
Because silence is worse than the traceback it replaces. Reading past a bad byte gives a skill
whose description is quietly mangled, and that skill validates, installs, and ships. The file is
reported as an error and skipped, and the run ends with the exit code an error earns.

Why the message and not the catch is the deliverable
----------------------------------------------------
Catching is two lines and buys a reader nothing on its own. What turns a five-minute puzzle into
a one-line fix is the path, the offset, and the byte, which is `_validate_manifest()`'s principle
in `install.py`: "The message is half the fix."

Standard library only, per the conventions section of `AGENTS.md`.

Not shipped to adopters
-----------------------
This module is imported by the distribution scripts and reaches no adopter tree, so it carries
no portability contract of its own. `.tasks/validate.py` deliberately does **not** import it and
carries its own copy, because that file is a template `init-worktracking` writes into other
repositories, where nothing named `scripts/` exists. A test asserts the two produce the same
message rather than trusting that they still do.
"""
from __future__ import annotations

from pathlib import Path


class NotUTF8(ValueError):
    """A file in scope is not valid UTF-8.

    A ValueError rather than a new base, so a caller that already treats a malformed input as
    an ordinary finding needs no new branch. Its `str()` is the reportable message.
    """


def decode_error_message(path, exc: UnicodeDecodeError) -> str:
    """The one sentence a reader needs, built from the failure itself.

    Separate from `read_text_utf8` so a caller that already holds the bytes, or that decodes
    somewhere this helper does not reach, still produces the identical message. Two spellings
    of one diagnosis is the drift this repository keeps recording.
    """
    byte = exc.object[exc.start] if exc.start < len(exc.object) else 0
    return (f"{path}: not valid UTF-8. Byte 0x{byte:02x} at offset {exc.start} could not be "
            f"decoded ({exc.reason}). Every file this tool reads is UTF-8 by contract, so the "
            f"file is reported rather than read past: re-save it as UTF-8.")


def read_text_utf8(path) -> str:
    """The file's text, or `NotUTF8` naming the file and the byte that stopped it.

    `OSError` is deliberately not caught. A missing or unreadable file is a different fact
    from an undecodable one, callers here already handle it where they care, and folding the
    two together would report a deleted file as a corrupt one.
    """
    path = Path(path)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise NotUTF8(decode_error_message(path, exc)) from None
