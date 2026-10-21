"""reportlab's start-up hooks, empty on purpose.

On import, reportlab looks for a module named `reportlab_mods`, and `reportlab.rl_config` for one
named `reportlab_settings`. Only when the import fails does it run `~/.reportlab_mods` or
`~/.reportlab_settings` from the home folder as Python code. In a sandbox whose home folder an
earlier program could write, that would run planted code in a later program that only imported
reportlab. This module is packed twice at the top of the stdlib zip, as `reportlab_mods.py` and
`reportlab_settings.py`, so both imports succeed and reportlab never reads either file. It
defines nothing, so reportlab's settings keep their defaults; set them with `RL_*` environment
variables, or through `reportlab.rl_config` in the program.
"""
