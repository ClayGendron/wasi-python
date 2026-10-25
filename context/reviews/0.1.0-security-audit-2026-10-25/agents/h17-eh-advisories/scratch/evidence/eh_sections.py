"""Read-only parse of a wasm module's type (1), import (2), tag (13) sections and the
target_features custom section: counts tags (defined and imported), recursive groups,
subtypes, non-func composite types and the longest supertype chain. Never executes."""
import sys, json

def leb_u(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7f) << s; s += 7
        if not x & 0x80: return r, i

def leb_s(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7f) << s; s += 7
        if not x & 0x80:
            if x & 0x40: r |= -(1 << s)
            return r, i

def name(b, i):
    n, i = leb_u(b, i); return b[i:i+n].decode('utf-8', 'replace'), i + n

def valtype(b, i, refs):
    t = b[i]; i += 1
    if t in (0x63, 0x64):  # (ref null ht) / (ref ht)
        ht, i = leb_s(b, i); refs.append((t, ht))
    else:
        refs.append((t, None))
    return t, i

def comptype(b, i, refs):
    form = b[i]; i += 1
    if form == 0x60:
        n, i = leb_u(b, i)
        for _ in range(n): _, i = valtype(b, i, refs)
        n, i = leb_u(b, i)
        for _ in range(n): _, i = valtype(b, i, refs)
        return 'func', i
    if form == 0x5f:
        n, i = leb_u(b, i)
        for _ in range(n): _, i = valtype(b, i, refs); i += 1
        return 'struct', i
    if form == 0x5e:
        _, i = valtype(b, i, refs); i += 1
        return 'array', i
    raise ValueError(hex(form))

def main(path):
    b = open(path, 'rb').read()
    out = {'file': path.split('/')[-1], 'size': len(b)}
    i = 8
    types = []; recgroups = 0; rec_multi = 0; subtypes = 0; supers = {}
    while i < len(b):
        sid = b[i]; i += 1
        sz, i = leb_u(b, i); start = i; end = i + sz
        if sid == 1:
            cnt, j = leb_u(b, i); out['type_section_entries'] = cnt
            idx = 0; kinds = {}; refvals = []
            for _ in range(cnt):
                group = 1
                if b[j] == 0x4e:
                    j += 1; group, j = leb_u(b, j); recgroups += 1
                    if group > 1: rec_multi += 1
                for _ in range(group):
                    if b[j] in (0x50, 0x4f):
                        j += 1; subtypes += 1
                        ns, j = leb_u(b, j)
                        sl = []
                        for _ in range(ns): s_, j = leb_u(b, j); sl.append(s_)
                        supers[idx] = sl
                    k, j = comptype(b, j, refvals)
                    kinds[k] = kinds.get(k, 0) + 1
                    idx += 1
            assert j == end, (j, end)
            out['types_total'] = idx
            out['composite_kinds'] = kinds
            out['explicit_rec_groups'] = recgroups
            out['rec_groups_with_more_than_one_type'] = rec_multi
            out['explicit_sub_declarations'] = subtypes
            depth = 0
            for t in supers:
                d = 0; cur = t; seen = set()
                while cur in supers and supers[cur] and cur not in seen:
                    seen.add(cur); cur = supers[cur][0]; d += 1
                depth = max(depth, d)
            out['longest_supertype_chain'] = depth
            vt = {}
            for t, ht in refvals:
                key = hex(t) if ht is None else f'{hex(t)} ht={ht}'
                vt[key] = vt.get(key, 0) + 1
            out['valtypes_in_signatures'] = vt
            out['typed_refs_in_signatures'] = sum(1 for t, _ in refvals if t in (0x63, 0x64))
        elif sid == 2:
            cnt, j = leb_u(b, i); imp_tags = 0; kinds = {}
            for _ in range(cnt):
                m, j = name(b, j); f, j = name(b, j); k = b[j]; j += 1
                kinds[k] = kinds.get(k, 0) + 1
                if k == 0: _, j = leb_u(b, j)
                elif k == 1:
                    j += 1; fl = b[j]; j += 1; _, j = leb_u(b, j)
                    if fl & 1: _, j = leb_u(b, j)
                elif k == 2:
                    fl = b[j]; j += 1; _, j = leb_u(b, j)
                    if fl & 1: _, j = leb_u(b, j)
                elif k == 3: j += 2
                elif k == 4: j += 1; _, j = leb_u(b, j); imp_tags += 1
            out['import_kinds'] = kinds
            out['imported_tags'] = imp_tags
        elif sid == 13:
            cnt, j = leb_u(b, i); tags = []
            for _ in range(cnt):
                attr = b[j]; j += 1; ti, j = leb_u(b, j); tags.append({'attribute': attr, 'type': ti})
            out['tag_section_bytes'] = sz
            out['defined_tags'] = tags
        elif sid == 0:
            nm, j = name(b, i)
            if nm == 'target_features':
                cnt, j = leb_u(b, j); feats = []
                for _ in range(cnt):
                    pre = chr(b[j]); j += 1; f, j = name(b, j); feats.append(pre + f)
                out['target_features'] = feats
        i = end
    out['total_tags'] = out.get('imported_tags', 0) + len(out.get('defined_tags', []))
    out['total_tags_is_odd'] = out['total_tags'] % 2 == 1
    return out

if __name__ == '__main__':
    print(json.dumps([main(p) for p in sys.argv[1:]], indent=1))
