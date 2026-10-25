"""Parse a wasm module's sections: imports, exports, memories, custom sections,
and scan the code section for br_table target counts. Data only; never executes."""
import sys, json, re, collections

def leb_u(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7f) << s; s += 7
        if not x & 0x80: return r, i

def leb_s(b, i, bits=64):
    r = s = 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7f) << s; s += 7
        if not x & 0x80:
            if s < bits and (x & 0x40): r |= -(1 << s)
            return r, i

def name(b, i):
    n, i = leb_u(b, i); return b[i:i+n].decode('utf-8', 'replace'), i + n

def limits(b, i):
    flag = b[i]; i += 1
    mn, i = leb_u(b, i); mx = None
    if flag & 1: mx, i = leb_u(b, i)
    return {'flag': flag, 'shared': bool(flag & 2), 'mem64': bool(flag & 4), 'min': mn, 'max': mx}, i

def main(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'\0asm', 'not wasm'
    out = {'file': path, 'size': len(b), 'version': int.from_bytes(b[4:8], 'little'),
           'sections': [], 'imports': [], 'exports': [], 'memories': [], 'custom': [], 'tables': []}
    i = 8; code = None
    while i < len(b):
        sid = b[i]; i += 1
        sz, i = leb_u(b, i); start = i; end = i + sz
        out['sections'].append({'id': sid, 'size': sz})
        if sid == 0:
            nm, j = name(b, i)
            ent = {'name': nm, 'size': sz}
            if nm == 'target_features':
                cnt, j = leb_u(b, j); feats = []
                for _ in range(cnt):
                    pre = chr(b[j]); j += 1
                    f, j = name(b, j); feats.append(pre + f)
                ent['features'] = feats
            elif nm == 'producers':
                ent['body'] = b[j:end].decode('latin-1')
            out['custom'].append(ent)
        elif sid == 2:
            cnt, j = leb_u(b, i)
            for _ in range(cnt):
                m, j = name(b, j); f, j = name(b, j); k = b[j]; j += 1
                d = {'module': m, 'field': f, 'kind': k}
                if k == 0: d['type'], j = leb_u(b, j)
                elif k == 1: j += 1; d['limits'], j = limits(b, j)
                elif k == 2: d['limits'], j = limits(b, j)
                elif k == 3: d['valtype'] = b[j]; d['mut'] = b[j+1]; j += 2
                elif k == 4: j += 1; d['tag'], j = leb_u(b, j)
                out['imports'].append(d)
        elif sid == 4:
            cnt, j = leb_u(b, i)
            for _ in range(cnt):
                et = b[j]; j += 1; l, j = limits(b, j); l['elem'] = et; out['tables'].append(l)
        elif sid == 5:
            cnt, j = leb_u(b, i)
            for _ in range(cnt):
                l, j = limits(b, j); out['memories'].append(l)
        elif sid == 7:
            cnt, j = leb_u(b, i)
            for _ in range(cnt):
                f, j = name(b, j); k = b[j]; j += 1; idx, j = leb_u(b, j)
                out['exports'].append({'field': f, 'kind': k, 'index': idx})
        elif sid == 10:
            code = (start, end)
        i = end
    # br_table scan via a full instruction decoder would be long; use llvm-objdump instead (see driver).
    return out, b, code

if __name__ == '__main__':
    out, b, code = main(sys.argv[1])
    print(json.dumps(out, indent=1))
