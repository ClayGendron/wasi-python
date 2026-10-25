import json, os, re, sys
SKILL = "./.agents/skills/security-audit"

def load_blocks(fname):
    """Map block name -> verbatim text for a skill markdown file."""
    text = open(os.path.join(SKILL, fname), encoding="utf-8").read()
    lines = text.split("\n")
    blocks = {}
    cur = None; buf = []
    def flush():
        if cur is not None:
            blocks[cur] = "\n".join(buf).rstrip() + "\n"
    for ln in lines:
        m_bold = re.match(r"^\*\*([^*]+)\*\*(\s*\(subagent_type: `[a-z]+`\))?\s*$", ln)
        m_head = re.match(r"^##\s+(.+?)\s*(\([^)]*\))?\s*$", ln)
        if m_bold:
            flush(); cur = m_bold.group(1).strip(); buf = [ln]; continue
        if m_head:
            flush(); cur = m_head.group(1).strip(); buf = [ln]; continue
        if ln.startswith("#") or ln.startswith("> **"):
            flush(); cur = None; buf = []; continue
        if cur is not None:
            buf.append(ln)
    flush()
    return blocks

CACHE = {}
def block(ref):
    fname, name = ref.split("#", 1)
    if fname not in CACHE:
        CACHE[fname] = load_blocks(fname)
    b = CACHE[fname].get(name)
    if b is None:
        raise SystemExit(f"block not found: {ref}; have {sorted(CACHE[fname])[:50]}")
    return f"<!-- {ref} -->\n" + b

