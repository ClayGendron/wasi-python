# 179: A display frame is bounded before it is parsed

- **Status:** built 2026-11-01 on `spec/179-a-display-frame-is-bounded-before-it-is-parsed` from `dev` at `0d105cc1` (Landing notes), its pull request, #94, in review; amended against the review's Lows (Landing notes, "Review round 1"). Drafted the same day to close High H1 of the 0.1.3 release's security review (`../reviews/0.1.3-security-review-2026-11-01.md`, "H1"), which holds the release.
- **Date:** 2026-11-01
- **Owner:** Clay Gendron
- **Kind:** a fix to the runner, and **a judge change** (new rows in a check file and in a unit file). Not structural: it adds no module-level mutable or lock (one constant, `VALUES`), no use of wasmtime-py's private API, no platform branch and no test seam; `_results.py` stays under its 400 lines and every function changed under 80. No guest import or export, no recipe, no artifact changes; `tests/public_api.txt` does not change.
- **Depends on:** landed: 031 and 036 (the tool protocol and its parse rules), 163 (the result an agent reads, whose Decision 7 set the display frame's bounds).
- **Research it stands on:** the 0.1.3 security review's H1, its defect, failure and fix (`../reviews/0.1.3-security-review-2026-11-01.md`), and its probe of the host's growth, reproduced here as the check's frame. **Drafting reads** (READ): `src/wasi_python/_results.py`, `src/wasi_python/_tool_host.py` (`_nesting`, `_parse`, `_decoded`, `admit`), `recipes/guest/host/display.py` (`_exchange`) and `../specifications/163-the-result-an-agent-reads.md`.

Labels: EXECUTED, run and seen; READ, read from a file, cited; INFERRED, reasoned.

## The problem

1. With `results=True`, `_ResultHost.admit` reads a frame up to 6 × the room left plus 1 KiB (163, Decision 7): the room is `output_bytes`, and the factor is the worst case of a JSON escape. With `output_bytes=None` it reads a frame of any length (READ, `src/wasi_python/_results.py`, `admit`).
2. `_ResultHost._answer` then runs the tool host's `_parse` on the whole frame: `json.loads`, then `_decoded`, which copies every list and object. Only afterwards does `_refusal` judge the frame's shape (READ, `_results.py`, `_answer`; `_tool_host.py`, `_parse`). A frame of empty objects, `{"v":1,"id":1,"op":"display","x":[{},{},…]}`, makes about sixteen bytes of objects for each byte sent, and the copy doubles it.
3. Under `tools=`, a frame that is not a display goes through the same parse before it reaches the tool host, whose 1 MiB cap would have refused it unread: `admit` lets through the larger of the two bounds.
4. **Measured** (EXECUTED, the new check's frame, tracemalloc's peak of the host's Python during the call, an arm64 Mac): a frame of 6,291,456 bytes at `output_bytes` = 1 MiB held 315,345,260 bytes at once, 50 times the frame and about 300 times `output_bytes`; with `output_bytes=None` 315,336,494; as a tool call under `tools=` 315,337,627. At `output_bytes` = 4 MiB a 24 MiB frame held 1,216 MiB (the review's probe measured 4,239 MiB of resident growth there, the guest's memory with it). A guest can repeat it, and each session adds its own.

The rubric's "every channel to the host is bounded" held in name only: the length was bounded, and the work a frame could ask of the host was not.

## Decisions

### 1. A display frame holds at most 64 values outside its strings

A frame's **values** are counted outside its strings: each `[`, each `{` and each `,` opens one. Every value a parse makes is a container one of these opens, or an item or member a comma or an opening bracket introduces, so a parse of a frame of N values makes at most about 2N objects, keys included (INFERRED).

The largest display the guest sends (READ, `recipes/guest/host/display.py`, `_exchange`) holds 19:

- the frame's object and the commas between its six keys (`v`, `id`, `op`, `value`, `data`, `truncated`): 1 + 5;
- `data`'s object and the commas between its six MIME types: 1 + 5;
- the `$bytes` object of `image/png`: 1;
- `truncated`'s list and the commas between its six types at most: 1 + 5.

The bound, `VALUES` in `_results.py`, is 64: more than three times 19, so a key or two a later version of the protocol adds does not reach it, and small enough that its objects cost a few kibibytes at most. Within it, a parse costs about the frame's length: each string about its own length (up to four bytes a character, once one character needs four), each number at most 64 characters (the existing rule), and at most 64 containers.

The count is made in the pass `_nesting` already makes: its token pattern gains the comma, and the pass stops at the first value past the bound, so the count costs one pass that ends early on a hostile frame. The pass reads the frame's bytes, not its decoded text: in UTF-8 no byte of a character past ASCII is a quote, a backslash, a bracket or a comma, so a frame refused by its shape is never decoded. An escape pair outside a string is not JSON and counts as nothing; the parse refuses it as not JSON. `_parse(frame, most)` refuses a frame past `most` values before it decodes it, with "the frame holds more than 64 values outside its strings", which `_ResultHost` answers `protocol`. The tool host calls `_parse` without `most`, as today: a tool's arguments may hold many values, and its 1 MiB cap bounds them.

### 2. Under tools, a frame past the tool cap is parsed only as a display

`_ResultHost._answer` parses every frame with the display bound. A frame the bound refuses goes to the tool host when the call has tools, as a frame that is not JSON does today; the tool host's own `admit` then refuses one past its 1 MiB cap by its length, unread, and reads one within it by its own rules. So a frame past the tool cap is parsed only under the display bounds, at a display's linear cost (Decision 3), and a tool frame of more than 64 values only within the tool cap. A `call` frame past the cap of 64 values or fewer is still parsed by the result host before the tool host refuses it by its length: the result host cannot tell it from a display unparsed, and its cost is a display's. The review's fix named `admit` for this; the route is `_answer`'s, since `admit` sees only the length, and the length cannot tell a display from a tool frame. `admit` is unchanged.

A tool frame within the cap that holds more than 64 values is scanned once by the result host, to the 65th value, then parsed by the tool host: the cost it has without results.

### 3. A frame whose strings cannot fit is answered before it is decoded

A display frame of one long string is allowed, but the frame is read up to six times the room, and a parse holds the frame, its decoded text and the string, up to four bytes a character once one character needs four. A frame of six times `output_bytes` of ASCII with one four-byte character held about nine times the frame, 54 times `output_bytes` (EXECUTED, the check's row on the first build).

So the same pass sums the frame's **text**: the bytes inside its strings, less what each escape adds, `\uXXXX` counted as one byte and any other pair as one. That is a lower bound on the strings' UTF-8 once decoded (INFERRED: a raw byte is itself; `\uXXXX` is at least one byte, a surrogate pair at least two of its four; `\n` and its kin are one). A display that fits the room holds at most `(4 × room + 8) // 3 + ENVELOPE` of text: its text values as they are, its PNG as base64 (four bytes for every three, rounded up to whole groups of four, so at most `(4n + 8) / 3` for n bytes), and its keys, MIME types and cut types within the kibibyte of `ENVELOPE`. A frame whose text passes that is answered `too_large` with `room` before it is decoded, its `id` null as `admit`'s are, and counted as a record that cut "displays": the answer the parse would have given, sooner. The guest then sends its text alone, cut to fit, as today. No display that fits is refused (INFERRED, the bound above; a unit row keeps a PNG of `room - 1` bytes).

Under tools, the rule applies only to a frame past the tool cap: within it, a tool's arguments may hold long strings, and the frame goes to the tool host as before. So under tools a display frame within the cap is parsed whatever its text, and its cost is bounded by about nine times the tool request cap, not by the room: with `output_bytes` of 1 KiB, a 1 MiB display of ASCII and one four-byte character held 8,391,211 bytes, 8,195 times `output_bytes` (EXECUTED by the pull request's review, round 2, its L5). The documents say "at most about 36 times `output_bytes`, or with tools about nine times the tool request cap when that is more".

**What is left.** A frame that passes both bounds is read, and its cost is linear in its length, which `admit` holds to six times the room. The worst is a frame of escapes (`\u0041` six bytes for one) whose text fits the room and holds one four-byte character: the whole frame decodes four bytes a character. It held 35.4 times `output_bytes` (EXECUTED, a row bounds it at 40), about 566 MiB at the default 16 MiB. Lowering it would refuse a display whose text is mostly control characters, which the guest's encoder writes as `\u00XX`, or need a parser of our own; neither is taken here, and `docs/reference/tool-protocol.md` states the number. A frame that is refused costs about twice its length, the frame's two copies as it leaves the guest's memory (`_call.py`, the door).

### 4. With `output_bytes=None`, only the guest's memory bounds a display frame

`output_bytes=None` keeps no length bound on a display frame, as 163 decided, and Decision 3's rule needs a room. The embedder that passes it removes the bound on stdout and stderr too, and a guest can already make the host hold any number of bytes through them. What changes is the cost per byte: with the value bound, a display frame of N bytes holds about 2N bytes of the host's memory when it is refused, and at most about 9N when it is read, since Decision 3's rule needs a room, against 50N before. The guest's memory limit, 1 GiB by default, bounds N.

## Intent

A guest's display frame costs the host a few times its own length, whatever it holds.

## Design

- `src/wasi_python/_tool_host.py`: `_TOKEN` reads bytes and matches the comma too; `_nesting(frame, most=None)` returns a `_Shape`, the deepest nesting, the values and the text, and stops past either bound; `_parse(frame, most=None, shape=None)` refuses a frame past `most` values before it decodes it.
- `src/wasi_python/_results.py`: `VALUES = 64`, with its reasoning in the comment; `_most_text(room)`; `_answer` reads the shape once, answers a frame whose text cannot fit, then parses with the bound.
- `docs/reference/tool-protocol.md`: the rule, the route under tools, and what `output_bytes=None` leaves. `docs/explanation/security-model.md`: one sentence.
- **The judge:** `tests/checks/test_v1_2_hostile_guest.py::test_a_display_frame_costs_the_host_about_its_length`, seven rows, in the `own-hostile` shard by its file; five rows in `tests/unit/test_results.py`; `tests/unit/test_tools.py`'s one-pass row hands the scan bytes.

## Scope

In: Decisions 1 to 4. Out: Decision 3's residual, a frame of escapes that fits; the tool host's own parse of a tool frame within its 1 MiB cap, whose cost a frame of empty objects also raises to about fifty times the frame, at most about 50 MiB at once and freed when it is answered (INFERRED from the rows' factor); a parser that holds a string once.

## Acceptance criteria

1. **The hostile frame.** A row sends `{"v":1,"id":1,"op":"display","x":[{},{},…]}` of six times `output_bytes` (1 MiB): it is answered `protocol`, and the host's Python holds at most three times the frame at once during the call, read by tracemalloc, which counts the host's allocations and none of the guest's memory. Rows the same with `output_bytes=None`, and as a `call` under `tools=`, answered `too_large`. Each seen failing first on `dev`'s code. EXECUTED.
2. **The long string.** A row sends six times `output_bytes` of ASCII with one four-byte character: answered `too_large` with a null `id`, before it is decoded, and held to three times the frame (it was 54 times `output_bytes`), seen failing first. A row of escapes whose text fits the room with one four-byte character is held to 40 times `output_bytes`, the residual. Rows of one 3 MiB string, kept, held to four times the frame, and with one four-byte character, to ten. EXECUTED.
3. **The unit rows.** A frame of exactly 64 values is kept and one of 65 is refused `protocol` without `json.loads`; a frame of a million empty objects too; commas and brackets inside a string are not counted. The largest display the guest sends holds at most a third of the bound and is kept. Under tools, a call frame past the cap is answered `too_large` without `json.loads`, and a tool call within the cap that holds 1,000 values is served. A display whose text cannot fit is answered `too_large` without `json.loads`, one whose text is just under is answered after it, one of escapes is counted a byte an escape, a PNG of `room - 1` bytes is kept, and a tool call of a 5,000-byte string under a room of 10 is served. An escape pair outside a string is answered "not JSON" by both hosts. The first, third, fourth and fifth seen failing first. EXECUTED.
4. **The run.** The fast tier, the lint and `ci-status` green; no accepted pass lost.

The news file's CHANGELOG line:

- Security: `` - **A display frame no longer costs the host fifty times its size.** With `results=True`, a guest could send a display frame of empty objects, or of text far past `output_bytes`, that the host parsed whole before refusing it. Such a frame is now answered before it is parsed. [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/) ``

## Landing notes

Built 2026-11-01 by an agent (Claude Opus 5.5), a builder sub-agent of the orchestrating session, on `spec/179-a-display-frame-is-bounded-before-it-is-parsed` from `dev` at `0d105cc1`. The set was 174's, read-only through `WASI_PYTHON_ARTIFACTS`: `src/`, `recipes/`, `scripts/` and `downloads/` are the same at its head and at `0d105cc1`, and this change touches only `src/`, which is the host's Python. Everything below is EXECUTED on an arm64 Mac (Darwin 25.5.0).

**Seen failing first.** On `dev`'s code with the new rows in place: the check's rows "display", "display, no output cap" and "call, under tools" failed, the host holding 315,345,260, 315,336,494 and 315,337,627 bytes for a frame of 6,291,456; the two long-string rows passed. The unit rows `test_a_frame_with_more_values_than_a_display_holds_is_refused_before_it_is_parsed` (the 65-value frame was kept) and `test_under_tools_a_frame_past_the_tool_cap_is_never_parsed` (`json.loads` ran once on the 2 MiB call frame) failed; `test_the_largest_display_the_guest_sends_holds_a_third_of_the_values` passed, as a guard.

**After.** The host's peak during the call, above what it held before:

| row | frame | before | after |
|---|---|---|---|
| display, `output_bytes` 1 MiB | 6,291,456 | 315,345,260 (50.1×) | 12,753,161 (2.03×) |
| display, `output_bytes=None` | 6,291,456 | 315,336,494 | 12,717,336 (2.02×) |
| call under tools, 1 MiB | 6,291,456 | 315,337,627 | 12,651,245 (2.01×) |
| one long string, kept | 3,145,728 | passes | 9,504,882 (3.02×) |
| the same, one four-byte character | 3,145,728 | passes | 28,375,731 (9.02×) |

The review's case, `output_bytes` = 4 MiB and a 24 MiB frame of empty objects, measured by a probe that counts the first call's imports too: 1,216 MiB before, 48.1 MiB after (2.0×).

**Review round 1** (`../reviews/179-a-display-frame-is-bounded-before-it-is-parsed-pr-2026-11-01.md`, "Lands", four Lows; the fix is one commit). Measured on 167's set, read-only (174's had been removed; `recipes/guest` and the bootstrap are the same at its head and here), against the first build's `src/` run from an export of `f9dde3db`.

- **L1, the long string.** Decision 3 is new: a frame whose strings cannot fit the room is answered before it is decoded, and the scan reads bytes. The row "one long string past the room" (6,291,456 bytes of ASCII and one four-byte character, `output_bytes` 1 MiB) held 56,688,627 bytes on the first build (54.1 times `output_bytes`, and answered after the parse, `id` 1) and holds 12,645,517 (12.1 times, `id` null). The residual, a frame of escapes that fits the room with one four-byte character, holds 37,133,595 bytes on both builds (35.4 times `output_bytes`), bounded at 40 by a row and stated in `docs/reference/tool-protocol.md`. The other rows: the hostile frames 12,748,591, 12,712,830 and 12,649,179 bytes (2.0 times the frame, as before); the kept strings 9,504,003 and 28,374,927. The unit row `test_a_display_whose_strings_cannot_fit_is_answered_before_it_is_decoded` failed first on the first build (`id` 7, `json.loads` called once).
- **L2, an escape pair outside a string.** The scan counts only `[`, `{` and `,` outside a string, so `{"v":1}` and seventy `\a` is answered "the frame is not JSON" by both hosts, as on `dev`. `test_an_escape_outside_a_string_is_not_a_value` failed first on the first build ("more than 64 values").
- **L3.** Decision 2 now says what the build does: a `call` frame past the cap of 64 values or fewer is parsed by the result host at a display's cost, then refused by the tool host by its length. Sending it to the cap's refusal unread would need its `op`, which only the parse reads.
- **L4**, the Windows box, is the orchestrator's.
- **L5** (round 2), documentation only: under tools a display within the tool cap is bounded by about nine times that cap, not by the room. The protocol page, the security-model page and Decision 3 say so, in the review's words.
