"""Golden job: regex, the richer regular-expression engine (spec 047, Decision 7).

Usage: regex_features.py <data dir> <out dir> (both unused). Named `regex_features`, not
`regex`, so the script's own folder on sys.path cannot hide the package. It prints regex's
features (fuzzy matching, Unicode properties from regex's own tables, graphemes, full case
folding, named lists, captures, overlapped and reverse searches, partial matches, set
operations, recursion, atomic and possessive groups, branch reset, variable lookbehind, POSIX
matching, subf, split, named-group substitution, an error), then the five calls carried patch
0001 fixed: without it each trapped the guest ("indirect call type mismatch"), and `regex.sub`
with a `\\g<name>` template reads `groupindex`. The pickle's bytes name `regex._regex`, the module's
import name, which a builtin gets only through the inittab's package context (Decision 4).
"""

import hashlib
import pickle
import sys

import regex


def show(label, f):
    try:
        print(label, "->", f())
    except Exception as e:
        print(label, "-> RAISES", type(e).__name__, str(e)[:160])


print(f"versions python={sys.version_info[0]}.{sys.version_info[1]} regex={regex.__version__}")
show("fuzzy", lambda: regex.search(r"(?:color){e<=1}", "the colour red").group())
show("fuzzy counts", lambda: regex.fullmatch(r"(?e)(?:kitten){e<=3}", "sitting").fuzzy_counts)
show("bestmatch", lambda: regex.search(r"(?b)(?:hello){i<=2,d<=1}", "hxllo helo").span())
show("unicode props", lambda: regex.findall(r"\p{Script=Greek}+|\p{Han}+", "abc αβγ 中文 xyz"))
show("graphemes", lambda: regex.findall(r"\X", "\u00e9a\U0001f469\u200d\U0001f4bb"))
show("words V1", lambda: regex.findall(r"(?V1)\w+", "can't stop-now"))
show("casefold full", lambda: bool(regex.match(r"(?fi)strasse", "STRAßE")))
show("named lists", lambda: regex.findall(r"\L<pets>", "a cat and a dog", pets=["cat", "dog"]))
show("captures", lambda: regex.match(r"(?:(\w)\d)+", "a1b2c3").captures(1))
show("overlapped", lambda: regex.findall(r"\d\d", "12345", overlapped=True))
show("reverse", lambda: regex.findall(r"(?r)\w+", "one two three"))
show("partial", lambda: regex.match(r"\d{4}-\d{2}", "2026-1", partial=True).partial)
show("set ops", lambda: regex.findall(r"(?V1)[\p{L}--[aeiou]]+", "education"))
show("recursion", lambda: regex.fullmatch(r"(\((?:[^()]|(?1))*\))", "(a(b)(c(d)))") is not None)
show("atomic", lambda: regex.match(r"(?>a+)b", "aaab").group())
show("possessive", lambda: regex.match(r"a++a", "aaa"))
show("branch reset", lambda: regex.match(r"(?|(a)|(b))", "b").groups())
show("lookbehind", lambda: regex.findall(r"(?<=\b(?:Mr|Mrs)\.? )\w+", "Mr. Smith and Mrs Jones"))
show("posix", lambda: regex.search(r"(?p)a|ab|abc", "abcd").group())
show("subf", lambda: regex.subf(r"(\w+)@(\w+)", "{2} at {1}", "user@host"))
show("split", lambda: regex.split(r"(?V1)\b", "a b"))
show("named sub", lambda: regex.sub(r"(?P<y>\d{4})-(?P<m>\d\d)", r"\g<m>/\g<y>", "2026-10"))
show("escape", lambda: regex.escape("a.b*c"))
show("error", lambda: regex.compile(r"(a"))
show("bounded backtracking", lambda: regex.match(r"(a+)+b", "a" * 22 + "c"))
show(
    "unicode categories",
    lambda: [
        len(regex.findall(r"\p{" + c + "}", "".join(map(chr, range(0x3000)))))
        for c in ("Lu", "Ll", "Nd", "Mn", "Zs")
    ],
)

# The five calls patch 0001 fixed, and a pickle round trip.
p = regex.compile(r"(?P<a>\w)(?P<b>\d)+", regex.I)
m = p.match("x12")
show("groupindex", lambda: p.groupindex)
show("capturesdict", lambda: m.capturesdict())
show("allcaptures", lambda: m.allcaptures())
show("allspans", lambda: m.allspans())
data = pickle.dumps(p, protocol=5)
back = pickle.loads(data)
print("pickle", len(data), hashlib.sha256(data).hexdigest())
print("pickle names regex._regex", b"regex._regex" in data)
print("round trip", back.pattern == p.pattern, back.flags == p.flags)
print("round trip groupindex", back.groupindex == p.groupindex)
print("module", regex._regex.__name__, regex._regex.compile.__module__)
