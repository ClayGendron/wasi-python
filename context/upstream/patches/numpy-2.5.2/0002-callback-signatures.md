- **Project:** numpy (https://github.com/numpy/numpy)
- **Against:** 2.5.2 (the pinned tarball)
- **Status:** drafted
- **Title:** BUG: give six C callbacks the signatures CPython calls them with
- **Files:** numpy/_core/src/multiarray/array_converter.c, numpy/_core/src/multiarray/array_method.c, numpy/_core/src/multiarray/convert_datatype.c, numpy/_core/src/multiarray/convert_datatype.h, numpy/_core/src/multiarray/getset.c, numpy/_core/src/multiarray/scalartypes.c.src, numpy/_core/src/umath/_scaled_float_dtype.c
- **Why we carry it:** on `wasm32-wasip1` a call through a function pointer of the wrong type traps, so `copy.copy` of any numpy scalar and `a.dtype = …` end the guest in a wasm trap (`indirect call type mismatch`) where native numpy prints the copy, or warns and works.

This draft is not the pull request's description. numpy's AI policy
(`doc/source/dev/ai_policy.rst` on `main`, read 2026-10-18) forbids AI-written "comments, pull
request descriptions, or issue descriptions" and an agent that "submits a pull request
autonomously", and asks every pull request for a disclosure of "which tool(s) have been used, how
they were used". So the owner writes and sends it, from the facts in
[`../../13-numpy-callback-signatures/pr.md`](../../13-numpy-callback-signatures/pr.md), laid out
under numpy's template headings, as for patch 0001.

Before sending, the owner weighs the policy's clauses as for 0001: the AI disclosure; "Code
Quality"; "Copyright"; and "Responsibility" (the submitter "must understand and be able to
explain" the change). All of this change was written by an agent.

The change adds, to each of six functions, the parameter CPython passes and the function ignores,
marked `NPY_UNUSED`; nothing else changes, on any platform. The upstream base is numpy's `main`
(`7ed6cf7`, 2026-10-17, where all six definitions are unchanged); six of the seven hunks apply
there as they are, and `convert_datatype.h`'s context has moved. `fix.patch` beside the facts is
the carried patch, against 2.5.2; the agent rebases it onto `main` in a scratch clone when the
owner asks to send it.
