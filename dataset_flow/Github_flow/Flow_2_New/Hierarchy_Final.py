import json, re, sys
from collections import defaultdict, Counter
from typing import Dict, Any, List, Set, Tuple

# ---------- config ----------
input_path  = '/mnt/shared/gpfs/escad_verilog_dataset/RERUN/re_label_new.jsonl'
output_path = '/mnt/shared/gpfs/escad_verilog_dataset/RERUN/hier.jsonl'
warn_on_unmatched = True

# ---------- helpers ----------
IDENT = r'[A-Za-z_][A-Za-z0-9_\$]*'

# module header: module [automatic|static] <name> ...
# FIX: make the (automatic|static) branch include the trailing space;
#     optional as a whole; name captured as "name".
RE_MODHDR = re.compile(
    rf'(?m)\bmodule\s+(?:(?:automatic|static)\s+)?(?P<name>{IDENT})\b'
)

# instantiation (mostly line-anchored for precision):
#   <mod> [#(...)] <inst> [ [array] ] (
# - allow indentation; allow optional parameterization; allow optional instance array dims.
# - keep it conservative to reduce false positives.
RE_INSTANTIATION = re.compile(
    rf'(?m)^\s*(?P<mod>{IDENT})\s*'            # module type
    rf'(?:#\s*\([^;]*?\))?\s+'                 # optional #(...), non-greedy until )
    rf'(?P<inst>{IDENT})\s*'                   # instance name
    rf'(?:\[[^\]]+\]\s*)?'                     # optional array dimensions, e.g., [3:0]
    rf'\('                                     # opening paren of port connection
)

# simple comment stripper (not string-literal aware, but robust enough for bulk)
RE_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
RE_LINE_COMMENT  = re.compile(r"//.*?$", re.M)

KEYWORDS: Set[str] = {
    'module','endmodule','begin','end','if','else','for','while','case','endcase',
    'generate','endgenerate','function','endfunction','task','endtask','always',
    'initial','assert','property','sequence','clocking','class','interface','package',
    'typedef','localparam','parameter','program','endprogram'
}
# Common gate primitives (ignored unless truly defined as modules)
PRIMITIVES: Set[str] = {
    'and','nand','or','nor','xor','xnor','buf','not','bufif0','bufif1','notif0','notif1',
    'pulldown','pullup','nmos','pmos','rnmos','rpmos','cmos','rcmos','tran','rtran',
    'tranif0','tranif1','rtranif0','rtranif1'
}

def strip_comments(s: str) -> str:
    s = RE_BLOCK_COMMENT.sub('', s or '')
    s = RE_LINE_COMMENT.sub('', s)
    return s

def normalize_repo(url: Any) -> str:
    """
    Normalize Repo_url strings so same repos compare equal.
    - Lowercase the scheme+host.
    - Strip trailing '.git' and trailing slashes.
    - Strip common 'git@' forms to https-like comparable chunks.
    - Return empty string on None.
    """
    if not url:
        return ''
    u = str(url).strip()

    # Handle SSH-like 'git@github.com:org/repo.git' -> 'github.com/org/repo'
    if u.startswith('git@') and ':' in u:
        host_repo = u.split('@', 1)[1]
        host_repo = host_repo.replace(':', '/', 1)
        u = host_repo

    u = u.replace('https://', 'https://').replace('http://', 'http://')
    # Lowercase host part if URL-like
    # crude split on '/', keep first chunk lowercased
    parts = u.split('/')
    if parts:
        parts[0] = parts[0].lower()
    u = '/'.join(parts)

    # drop trailing .git and slashes
    if u.endswith('.git'):
        u = u[:-4]
    u = u.rstrip('/')

    return u

def safe_get(d: Dict[str, Any], k: str, default=''):
    v = d.get(k)
    return default if v is None else v

# ---------- load + index ----------
samples: List[Dict[str, Any]] = []
module_defs: Dict[Tuple[str, str], List[Dict[str, int]]] = defaultdict(list)  # (repo_norm, modname) -> [{index}]
index_counts = Counter()

with open(input_path, 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip():
            continue
        sample = json.loads(line)
        samples.append(sample)
        idx = sample.get('index')
        index_counts[idx] += 1

        ioheader = safe_get(sample, 'ioheader', '')
        repo_norm = normalize_repo(sample.get('Repo_url'))

        # Record module definitions found in ioheader
        for m in RE_MODHDR.finditer(ioheader):
            modname = m.group('name')
            module_defs[(repo_norm, modname)].append({'index': idx})

# warn on duplicate indexes (optional)
dups = [k for k, c in index_counts.items() if c > 1]
if dups:
    print(f"[WARN] duplicate index ids encountered: {len(dups)} (first few: {dups[:10]})")

# quick lookup index->sample
index_to_sample: Dict[int, Dict[str, Any]] = {}
for s in samples:
    idx = s.get('index')
    if idx in index_to_sample:
        # keep the first occurrence; you can change policy if desired
        pass
    index_to_sample[idx] = s

# init parents/children
for s in samples:
    s['parents'] = []
    s['children'] = []

# ---------- build edges ----------
unmatched_by_sample: Dict[int, Set[str]] = defaultdict(set)
edges_added = 0

for s in samples:
    code = strip_comments(s.get('verilog_code', '') or '')
    my_idx = s.get('index')
    repo_norm = normalize_repo(s.get('Repo_url'))

    # scan per-line instantiations
    children_mods: Set[str] = set()
    for m in RE_INSTANTIATION.finditer(code):
        mod = m.group('mod')
        # filter obvious non-module tokens
        if mod in KEYWORDS or mod in PRIMITIVES:
            continue
        children_mods.add(mod)

    if not children_mods:
        continue

    for mod in children_mods:
        defs = module_defs.get((repo_norm, mod))  # STRICT same-repo scope
        if not defs:
            if warn_on_unmatched:
                unmatched_by_sample[my_idx].add(mod)
            continue

        for d in defs:
            cidx = d['index']
            if cidx is None or cidx == my_idx:
                continue
            # Safety: enforce same normalized repo on both ends (should already hold)
            child_repo_norm = normalize_repo(index_to_sample.get(cidx, {}).get('Repo_url'))
            if child_repo_norm != repo_norm:
                # shouldn't happen given the (repo,mod) scoping, but double-guard
                continue

            s['children'].append(cidx)
            if cidx in index_to_sample:
                index_to_sample[cidx]['parents'].append(my_idx)
                edges_added += 1

# ---------- finalize + write output ----------
with open(output_path, 'w', encoding='utf-8') as out:
    for s in samples:
        # dedupe + sort for stability
        s['parents']  = sorted(set(s['parents']))
        s['children'] = sorted(set(s['children']))
        out.write(json.dumps(s, ensure_ascii=False) + '\n')

# ---------- summary ----------
num_nodes = len(samples)
num_defs  = sum(len(v) for v in module_defs.values())
num_with_children = sum(1 for s in samples if s['children'])
num_with_parents  = sum(1 for s in samples if s['parents'])

print("Hierarchy added. Output written to:", output_path)
print(f"Nodes: {num_nodes}, Module definitions: {num_defs}, Edges: {edges_added}")
print(f"Nodes with children: {num_with_children}, Nodes with parents: {num_with_parents}")

if warn_on_unmatched and unmatched_by_sample:
    total_unmatched = sum(len(v) for v in unmatched_by_sample.values())
    print(f"[INFO] Unmatched instantiated module names (same-repo only): {total_unmatched} occurrences across "
          f"{len(unmatched_by_sample)} files (first few samples shown):")
    shown = 0
    for idx, mods in unmatched_by_sample.items():
        print(f"  - index {idx}: {sorted(mods)[:10]}")
        shown += 1
        if shown >= 10:
            break
