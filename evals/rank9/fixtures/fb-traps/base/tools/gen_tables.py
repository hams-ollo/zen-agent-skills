"""Generate build/generated_tables.py from the column layout. Run before the tests."""
import pathlib

WIDTHS = {"name": 12, "qty": 6, "price": 10}

out = pathlib.Path("build")
out.mkdir(exist_ok=True)
(out / "__init__.py").write_text("", encoding="utf-8")
(out / "generated_tables.py").write_text(f"WIDTHS = {WIDTHS!r}\n", encoding="utf-8")
print("wrote build/generated_tables.py")
