#!/usr/bin/env python3
import argparse, json, os, sys
from typing import Dict, List, Set, Tuple

# ----------------------------
# Bracket checking (unchanged)
# ----------------------------
PAIRS = {"(": ")", "[": "]", "{": "}"}
OPENERS = set(PAIRS.keys())
CLOSERS = set(PAIRS.values())
MATCH_FOR_CLOSE = {v: k for k, v in PAIRS.items()}
KEY_FOR = {"(": "()", ")": "()", "[": "[]", "]": "[]", "{": "{}", "}": "{}"}

def is_bracket_balanced(text: str) -> bool:
    stacks = {o: [] for o in OPENERS}
    for ch in text:
        if ch in OPENERS:
            stacks[ch].append(ch)
        elif ch in CLOSERS:
            opener = MATCH_FOR_CLOSE[ch]
            if not stacks[opener]:
                return False
            stacks[opener].pop()
    return all(len(v) == 0 for v in stacks.values())

# ----------------------------
# Helpers
# ----------------------------
def to_int_or_same(x):
    try:
        return int(x)
    except Exception:
        return x

def load_jsonl(path: str) -> Dict[int, dict]:
    data: Dict[int, dict] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception as e:
                print(f"[WARN] {path}:{ln}: bad JSON ({e}); skipping.", file=sys.stderr)
                continue
            if not isinstance(obj, dict) or "index" not in obj:
                print(f"[WARN] {path}:{ln}: not a dict or missing 'index'; skipping.", file=sys.stderr)
                continue
            idx = to_int_or_same(obj["index"])
            if not isinstance(idx, int):
                try:
                    idx = int(str(idx).strip())
                except Exception:
                    print(f"[WARN] {path}:{ln}: non-int index; skipping.", file=sys.stderr)
                    continue
            if idx in data:
                print(f"[WARN] duplicate index {idx}; keeping first.", file=sys.stderr)
                continue

            # normalize parents/children to int-lists
            for k in ("parents", "children"):
                lst = obj.get(k)
                if isinstance(lst, list):
                    clean = []
                    for v in lst:
                        vv = to_int_or_same(v)
                        if isinstance(vv, int):
                            clean.append(vv)
                        else:
                            try:
                                clean.append(int(str(vv).strip()))
                            except Exception:
                                pass
                    obj[k] = clean
                else:
                    obj[k] = []
            data[idx] = obj
    return data

def write_jsonl(path: str, items: Dict[int, dict]):
    with open(path, "w", encoding="utf-8") as f:
        for _, obj in items.items():
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def get_any_text(obj: dict) -> str:
    for k in ("full_text", "ioheader", "verilog_code"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""

def norm_ft_for_dedup(s: str) -> str:
    # For dedup comparison ONLY: remove \n, \t, and spaces
    return s.replace("\n", "").replace("\t", "").replace(" ", "")

def verilog_code_trim_for_empty(s: str) -> str:
    # Remove only \n and \t (keep spaces as requested)
    z = s.replace("\n", "").replace("\t", "")
    z = z.strip()
    return z

# ----------------------------
# Stage 1: drop "verified-leaf" (log exists and parents empty)
# ----------------------------
def drop_verified_leaf(items: Dict[int, dict], logs_dir: str) -> Tuple[Dict[int, dict], int]:
    removed = []
    for idx, obj in items.items():
        if not obj.get("parents"):
            p = os.path.join(logs_dir, f"{idx}.log")
            if os.path.isfile(p):
                removed.append(idx)
    for idx in removed:
        items.pop(idx, None)
    return items, len(removed)

# ----------------------------
# Stage 2: drop ioheader containing 'endmodule'
# ----------------------------
def drop_ioheader_endmodule(items: Dict[int, dict]) -> Tuple[Dict[int, dict], int]:
    removed = []
    for idx, obj in items.items():
        io = obj.get("ioheader")
        if isinstance(io, str) and "endmodule" in io.lower():
            removed.append(idx)
    for idx in removed:
        items.pop(idx, None)
    return items, len(removed)

# ----------------------------
# Stage 3: bracket imbalance removal
# ----------------------------
def drop_bracket_imbalanced(items: Dict[int, dict]) -> Tuple[Dict[int, dict], int]:
    removed = []
    for idx, obj in items.items():
        t = get_any_text(obj)
        if not is_bracket_balanced(t):
            removed.append(idx)
    for idx in removed:
        items.pop(idx, None)
    return items, len(removed)

# ----------------------------
# Stage 4: prune parents-only incomplete hierarchies (iterative)
# Rule: if parents non-empty and NONE of them exist -> remove the node.
# ----------------------------
def prune_parents_all_missing(items: Dict[int, dict]) -> Tuple[Dict[int, dict], int]:
    total_removed = 0
    while True:
        existing = set(items.keys())
        to_remove = []
        for idx, obj in items.items():
            parents = obj.get("parents") or []
            if parents:
                if not any(p in existing for p in parents):
                    to_remove.append(idx)
        if not to_remove:
            break
        for idx in to_remove:
            items.pop(idx, None)
        total_removed += len(to_remove)
    return items, total_removed

# ----------------------------
# Partial-missing parents -> strip missing ids
# ----------------------------
def strip_missing_parents(items: Dict[int, dict]) -> int:
    existing = set(items.keys())
    changed = 0
    for obj in items.values():
        parents = obj.get("parents") or []
        if not parents:
            continue
        present = [p for p in parents if p in existing]
        if present and len(present) != len(parents):
            obj["parents"] = present
            changed += 1
    return changed

# ----------------------------
# Deduplicate by normalized full_text
# Remove duplicates only if BOTH parents and children are empty.
# Count duplicates that we kept because they had parents/children.
# ----------------------------
def dedup_by_full_text(items: Dict[int, dict]) -> Tuple[Dict[int, dict], int, int]:
    groups: Dict[str, List[int]] = {}
    for idx, obj in items.items():
        ft = obj.get("full_text", "")
        if not isinstance(ft, str):
            ft = ""
        key = norm_ft_for_dedup(ft)
        groups.setdefault(key, []).append(idx)

    duplicates_kept_due_to_deps = 0
    to_remove: Set[int] = set()

    for key, idxs in groups.items():
        if len(idxs) <= 1:
            continue
        with_deps = [i for i in idxs if (items[i].get("parents") or items[i].get("children"))]
        no_deps = [i for i in idxs if not (items[i].get("parents") or items[i].get("children"))]

        if with_deps:
            duplicates_kept_due_to_deps += max(0, len(with_deps) - 1)
            # remove ALL no_deps because a dep-ful duplicate exists
            to_remove.update(no_deps)
        else:
            # No deps anywhere; keep one, drop the rest
            if len(no_deps) > 1:
                to_remove.update(no_deps[1:])

    for idx in to_remove:
        items.pop(idx, None)
    removed_count = len(to_remove)
    return items, removed_count, duplicates_kept_due_to_deps

# ----------------------------
# NEW: Merge dep-ful duplicates within the same Repo_url
# For each normalized full_text group:
#   - Partition entries with deps by Repo_url
#   - If a Repo_url bucket has >1 entries, merge parents/children (unique) into one rep and drop the rest
# Returns:
#   items, repo_merge_groups, repo_merge_entries_removed, remaining_duplicate_entries
# ----------------------------
def merge_depful_duplicates_within_repo(items: Dict[int, dict]) -> Tuple[Dict[int, dict], int, int, int]:
    # Build groups by normalized full_text
    groups: Dict[str, List[int]] = {}
    for idx, obj in items.items():
        ft = obj.get("full_text", "")
        if not isinstance(ft, str):
            ft = ""
        key = norm_ft_for_dedup(ft)
        groups.setdefault(key, []).append(idx)

    repo_merge_groups = 0
    repo_merge_removed = 0

    # We may remove while iterating: do in two passes (collect then apply)
    to_remove: Set[int] = set()
    parent_updates: Dict[int, Tuple[List[int], List[int]]] = {}

    for key, idxs in groups.items():
        if len(idxs) <= 1:
            continue

        # Only consider entries that have deps (parents or children)
        depful = [i for i in idxs if (items[i].get("parents") or items[i].get("children"))]
        if len(depful) <= 1:
            continue

        # Partition by Repo_url (string identity)
        buckets: Dict[str, List[int]] = {}
        for i in depful:
            r = items[i].get("Repo_url")
            # Only merge when Repo_url is present and comparable (string)
            if isinstance(r, str) and r:
                buckets.setdefault(r, []).append(i)

        # For each repo bucket with >1, merge
        for r, b in buckets.items():
            if len(b) <= 1:
                continue
            repo_merge_groups += 1

            # Choose representative (smallest index for determinism)
            rep = sorted(b)[0]
            all_parents: Set[int] = set(items[rep].get("parents") or [])
            all_children: Set[int] = set(items[rep].get("children") or [])

            for i in b:
                if i == rep:
                    continue
                p = items[i].get("parents") or []
                c = items[i].get("children") or []
                all_parents.update(p)
                all_children.update(c)

            # Save merged lists (sorted for stability)
            parent_updates[rep] = (sorted(all_parents), sorted(all_children))

            # All others in this bucket will be removed
            for i in b:
                if i != rep:
                    to_remove.add(i)

    # Apply updates and removals
    for rep, (p, c) in parent_updates.items():
        if rep in items:
            items[rep]["parents"] = p
            items[rep]["children"] = c

    for i in to_remove:
        if i in items:
            items.pop(i, None)
            repo_merge_removed += 1

    # Recompute remaining duplicates (entries beyond the first across all groups)
    remaining_duplicate_entries = 0
    # Rebuild fresh groups
    g2: Dict[str, List[int]] = {}
    for idx, obj in items.items():
        ft = obj.get("full_text", "")
        if not isinstance(ft, str):
            ft = ""
        key = norm_ft_for_dedup(ft)
        g2.setdefault(key, []).append(idx)
    for key, idxs in g2.items():
        if len(idxs) > 1:
            remaining_duplicate_entries += (len(idxs) - 1)

    return items, repo_merge_groups, repo_merge_removed, remaining_duplicate_entries

# ----------------------------
# Remove entries with empty/endmodule verilog_code after removing \n and \t
# ----------------------------
def drop_empty_or_endmodule_verilog(items: Dict[int, dict]) -> Tuple[Dict[int, dict], int]:
    removed = []
    for idx, obj in items.items():
        vc = obj.get("verilog_code")
        if not isinstance(vc, str):
            continue
        trimmed = verilog_code_trim_for_empty(vc)
        if trimmed == "" or trimmed == "endmodule":
            removed.append(idx)
    for idx in removed:
        items.pop(idx, None)
    return items, len(removed)

# ----------------------------
# Iterative parents cleanup again
# ----------------------------
def iterative_parents_cleanup(items: Dict[int, dict]) -> Tuple[Dict[int, dict], int, int]:
    total_removed = 0
    total_modified = 0
    while True:
        existing = set(items.keys())
        to_remove = []
        modified = 0
        for idx, obj in list(items.items()):
            parents = obj.get("parents") or []
            if not parents:
                continue
            present = [p for p in parents if p in existing]
            if not present:
                to_remove.append(idx)
            elif len(present) != len(parents):
                obj["parents"] = present
                modified += 1
        if not to_remove and modified == 0:
            break
        for i in to_remove:
            items.pop(i, None)
        total_removed += len(to_remove)
        total_modified += modified
    return items, total_removed, total_modified

# ----------------------------
# Final consistency pass
# ----------------------------
def final_consistency_pass(items: Dict[int, dict]) -> int:
    total_edits = 0
    while True:
        existing = set(items.keys())
        edits = 0
        for obj in items.values():
            p = obj.get("parents") or []
            pp = [x for x in p if x in existing]
            if len(pp) != len(p):
                obj["parents"] = pp
                edits += 1
            c = obj.get("children") or []
            cc = [x for x in c if x in existing]
            if len(cc) != len(c):
                obj["children"] = cc
                edits += 1
        if edits == 0:
            break
        total_edits += edits
    return total_edits

# ----------------------------
# Main
# ----------------------------
def main():
    ap = argparse.ArgumentParser(description="Filter & prune JSONL for Verilog dataset")
    ap.add_argument("input_jsonl")
    ap.add_argument("logs_dir")
    ap.add_argument("output_jsonl")
    args = ap.parse_args()

    items = load_jsonl(args.input_jsonl)
    print(f"[INFO] loaded: {len(items)} items")

    # Stage 1
    items, rm1 = drop_verified_leaf(items, args.logs_dir)
    print(f"[INFO] stage1 drop verified-leaf: {rm1}; remain: {len(items)}")

    # Stage 2
    items, rm2 = drop_ioheader_endmodule(items)
    print(f"[INFO] stage2 drop ioheader contains 'endmodule': {rm2}; remain: {len(items)}")

    # Stage 3
    items, rm3 = drop_bracket_imbalanced(items)
    print(f"[INFO] stage3 drop bracket-imbalanced: {rm3}; remain: {len(items)}")

    # Stage 4
    items, rm4 = prune_parents_all_missing(items)
    print(f"[INFO] stage4 prune parents-all-missing (iterative): {rm4}; remain: {len(items)}")

    # Partial-missing parents -> strip
    chA = strip_missing_parents(items)
    print(f"[INFO] partial-missing parents stripped (rows modified): {chA}; remain: {len(items)}")

    # Dedup by normalized full_text
    items, rmB, kept_due_to_deps = dedup_by_full_text(items)
    print(f"[INFO] dedup removed: {rmB}; duplicates kept due to parents/children: {kept_due_to_deps}; remain: {len(items)}")

    # Merge dep-ful duplicates within the same Repo_url
    items, merge_groups, merge_removed, remaining_dups = merge_depful_duplicates_within_repo(items)
    print(f"[INFO] repo-merge groups: {merge_groups}; repo-merge entries removed: {merge_removed}; remaining duplicate entries: {remaining_dups}; remain: {len(items)}")

    # Drop entries with empty/endmodule verilog_code
    items, rmC = drop_empty_or_endmodule_verilog(items)
    print(f"[INFO] drop empty/endmodule verilog_code: {rmC}; remain: {len(items)}")

    # Iterate parents cleanup again
    items, rmD, chD = iterative_parents_cleanup(items)
    print(f"[INFO] iterative parents cleanup -> removed nodes: {rmD}, modified parent lists: {chD}; remain: {len(items)}")

    # Final consistency pass
    editsE = final_consistency_pass(items)
    print(f"[INFO] final consistency pass edits (parents/children refs fixed): {editsE}; remain: {len(items)}")

    write_jsonl(args.output_jsonl, items)
    print(f"[INFO] wrote: {args.output_jsonl} with {len(items)} items")

if __name__ == "__main__":
    main()
