"""`python -m wasi_python run …` is `wasi-python run …`."""

from .cli import main

raise SystemExit(main())
