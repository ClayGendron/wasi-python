"""`python -m wasi_python run …` is `wasi-python run …`."""

from wasi_python.cli import main

raise SystemExit(main())
