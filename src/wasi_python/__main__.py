"""`python -m wasi_python run …` is `wasi-python run …` (spec 019)."""

from .cli import main

raise SystemExit(main())
