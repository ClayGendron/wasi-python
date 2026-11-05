# Upstream 35: attest-action's fallback uv admits versions that refuse its lock

Status: **issue text drafted, not posted.** The owner reads it and posts it, in the owner's words if they prefer. Found while drafting spec 185 (`../../specifications/185-the-wheel-on-pypi-carries-its-provenance.md`, *Is this the practice*). Nothing here waits on it: spec 185 installs an exact uv before the action runs, so the fallback never runs in this project.

## Where

`astral-sh/attest-action`, at `39b6ce43875c196a579e31635b11aa2a2036384a` (v0.0.7). Licence MIT OR Apache-2.0.

## The facts (EXECUTED, 2026-11-05)

- `action.yml` installs uv only when none is on the path, with `astral-sh/setup-uv` and `version: ">=0.9.12"`.
- Then it runs `uv run --locked --no-dev --project "${GITHUB_ACTION_PATH}" "${GITHUB_ACTION_PATH}/action.py"`.
- `pyproject.toml` sets `exclude-newer = "P7D"` and `[tool.uv.exclude-newer-package]`; `uv.lock` records `exclude-newer-span = "P7D"`.
- From an empty folder, with the action's tree as `--project`, `uv run --locked --no-dev … python -I -c "import pypi_attestations"`:
  - uv 0.9.22, 0.9.30, 0.10.0, 0.11.0, 0.11.32, 0.12.5: `error: The lockfile at uv.lock needs to be updated, but --locked was provided.` (0.9.x adds "Ignoring existing lockfile due to removal of global exclude newer".)
  - uv 0.13.0, 0.13.5, 0.13.7: the import succeeds.
- So a workflow that already has uv 0.9.12 to 0.12.x on its path (uv's own guide installs uv first with setup-uv, which a project may pin) fails at the action's step, and the `>=0.9.12` fallback only works because setup-uv resolves the range to the newest uv.

## The issue text

> **Title:** The action needs uv 0.13 or newer, but its fallback asks for `>=0.9.12`
>
> `action.yml` installs uv with `version: ">=0.9.12"` when none is found, and uses any uv already on the path. The lock records a relative `exclude-newer` (`exclude-newer-span = "P7D"`), and `uv run --locked` with uv 0.9.22 to 0.12.5 refuses it ("The lockfile at `uv.lock` needs to be updated, but `--locked` was provided"). uv 0.13.0 and later accept it.
>
> A workflow that follows uv's GitHub guide and pins uv with setup-uv (say 0.9.22) before this action fails at the signing step, often on the release tag, when it is hardest to retry.
>
> Possible fixes: raise the fallback to `>=0.13.0`; check the version of a uv found on the path and fail early with a clear message (or install a suitable one alongside); and say the minimum in the README. Pinning the fallback to an exact version would also make the action's own install reproducible.
>
> Reproduce: clone the action at v0.0.7, then from an empty folder run `uvx --from uv==0.12.5 uv run --locked --no-dev --project <clone> python -c "import pypi_attestations"`.
