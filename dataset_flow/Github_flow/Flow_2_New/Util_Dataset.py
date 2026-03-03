## COUNT THE NUMBER OF OVERLAP REPOS IN THE JSONL FILE
##==================================================
import argparse, json, sys
from urllib.parse import urlparse

def norm_repo(u: str) -> str | None:
    if not u: return None
    u = u.strip()
    if not u: return None
    try:
        p = urlparse(u if "://" in u else "https://" + u)
    except Exception:
        return None
    host = (p.netloc or "").lower().removeprefix("www.")
    path = (p.path or "").strip("/")
    if not host or not path:
        return None
    # Expect owner/repo at minimum
    parts = path.split("/")
    if len(parts) < 2:
        return None
    owner, repo = parts[0].lower(), parts[1].lower()
    repo = repo.removesuffix(".git").strip("/")
    if not owner or not repo:
        return None
    # Normalize to host/owner/repo (works for GitHub/GitLab/etc.)
    return f"{host}/{owner}/{repo}"

def load_txt(txt_path: str) -> set[str]:
    s = set()
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            n = norm_repo(line)
            if n: s.add(n)
    return s

def count_overlap(txt_set: set[str], jsonl_path: str):
    jsonl_set = set()
    overlap = 0
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line: continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # skip bad lines but continue
                continue
            u = obj.get("html_url")
            n = norm_repo(u)
            if not n: 
                continue
            # count overlap on the fly
            if n in txt_set:
                overlap += 1
            jsonl_set.add(n)
    return jsonl_set, overlap

def main():
    ap = argparse.ArgumentParser(description="Count how many JSONL html_url repos also appear in a TXT list.")
    ap.add_argument("txt",default="matched_repo_urls.txt", help="Text file with one repo URL per line")
    ap.add_argument("jsonl", default="new_repos.jsonl",help="JSONL file with key 'html_url'")
    ap.add_argument("--save-matches", help="Optional path to save matched URLs (normalized)", default=None)
    args = ap.parse_args()

    txt_set = load_txt(args.txt)
    jsonl_set, overlap_count = count_overlap(txt_set, args.jsonl)

    # If you want unique-overlap (set intersection), compute this too:
    unique_overlap = len(txt_set & jsonl_set)

    print(f"TXT unique repos            : {len(txt_set)}")
    print(f"JSONL unique repos (html_url): {len(jsonl_set)}")
    print(f"Matches (line-wise count)    : {overlap_count}")
    print(f"Unique-overlap repos         : {unique_overlap}")

    if args.save_matches:
        with open(args.save_matches, "w", encoding="utf-8") as w:
            for u in sorted(txt_set & jsonl_set):
                w.write(u + "\n")
        print(f"Saved unique-overlap to: {args.save_matches}")

if __name__ == "__main__":
    main()
##==================================================
##==================================================




## PARTITION THE JSONL FILE BY THE OVERLAP REPOS
##==================================================
import argparse, pathlib

PREFIX = "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/.cache_repo_zips_new2/"
GITHUB = "https://github.com/"

def url_to_zip_path(url: str) -> str:
    url = url.strip().rstrip("/")
    assert url.startswith(GITHUB), f"Not a GitHub URL: {url}"
    body = url[len(GITHUB):]           # e.g., "2cc2ic/dma-s2mm-and-mm2s"
    mapped = body.replace("/", "_")    # -> "2cc2ic_dma-s2mm-and-mm2s"
    return f"{PREFIX}{mapped}.zip"

def main():
    ap = argparse.ArgumentParser(description="Partition file1 URLs by presence of mapped zip path in file2.")
    ap.add_argument("file1", help="Text file with GitHub URLs (one per line).")
    ap.add_argument("file2", help="Text file with zip paths (one per line).")
    ap.add_argument("-o", "--out-matched", default="matched.txt",
                    help="Where to write URLs from file1 whose mapped zip path is in file2 (default: matched.txt)")
    ap.add_argument("-r", "--out-remaining", default="remaining.txt",
                    help="Where to write the rest of the URLs from file1 (default: remaining.txt)")
    ap.add_argument("--in-place", action="store_true",
                    help="Also overwrite file1 with remaining URLs.")
    args = ap.parse_args()

    p1 = pathlib.Path(args.file1)
    p2 = pathlib.Path(args.file2)
    f1_lines = [ln.strip() for ln in p1.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
    f2_set = set(ln.strip() for ln in p2.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip())

    matched, remaining = [], []
    for url in f1_lines:
        try:
            mapped = url_to_zip_path(url)
        except AssertionError:
            # Not a GitHub URL -> keep it in remaining untouched
            remaining.append(url)
            continue
        if mapped in f2_set:
            matched.append(url)     # “copy” this line out
        else:
            remaining.append(url)   # keep in file1

    pathlib.Path(args.out_matched).write_text("\n".join(matched) + ("\n" if matched else ""), encoding="utf-8")
    pathlib.Path(args.out_remaining).write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")

    if args.in_place:
        p1.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")

    print(f"Matched: {len(matched)} → {args.out_matched}")
    print(f"Remaining: {len(remaining)} → {args.out_remaining}")
    if args.in_place:
        print(f"file1 overwritten with remaining URLs.")

if __name__ == "__main__":
    main()

##==================================================
##==================================================



## ADD FULL TEXT TO THE JSONL FILE
##==================================================
import json

# ==== EDIT THESE PATHS ====
INPUT_JSONL = "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/output_filtered2_2.jsonl"
OUTPUT_JSONL = "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/edited_mid2.jsonl"
# ==========================

with open(INPUT_JSONL, "r", encoding="utf-8") as fin, \
     open(OUTPUT_JSONL, "w", encoding="utf-8") as fout:
    for line in fin:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)

        ioheader = obj.get("ioheader", "")
        verilog_code = obj.get("verilog_code", "")

        obj["full_text"] = f"{ioheader}\n{verilog_code}"

        fout.write(json.dumps(obj) + "\n")
##==================================================


## CHECK BRACKET BALANCE IN THE JSONL FILE
##==================================================


import argparse, json, sys

PAIRS = {"(": ")", "[": "]", "{": "}"}
OPENERS = set(PAIRS.keys())
CLOSERS = set(PAIRS.values())
MATCH_FOR_CLOSE = {v: k for k, v in PAIRS.items()}

def strip_comments_and_strings(s: str) -> str:
    """
    State-machine stripper for //, /* */, "strings", and 'strings'.
    Keeps everything else intact to preserve bracket order outside of those.
    """
    i, n = 0, len(s)
    out = []
    NORMAL, SLASH, LINE, BLOCK, SQUO, DQUO = range(6)
    state = NORMAL
    while i < n:
        ch = s[i]
        if state == NORMAL:
            if ch == "/":
                state = SLASH
                i += 1
            elif ch == "'":
                state = SQUO
                i += 1
            elif ch == '"':
                state = DQUO
                i += 1
            else:
                out.append(ch)
                i += 1
        elif state == SLASH:
            if i < n:
                nxt = s[i]
                if nxt == "/":
                    state = LINE
                    i += 1
                elif nxt == "*":
                    state = BLOCK
                    i += 1
                else:
                    # it was just a single '/'
                    out.append("/")
                    out.append(nxt)
                    state = NORMAL
                    i += 1
            else:
                out.append("/")
                state = NORMAL
        elif state == LINE:
            # consume to end-of-line
            if ch == "\n":
                out.append("\n")
                state = NORMAL
            i += 1
        elif state == BLOCK:
            # consume until */
            if ch == "*" and i + 1 < n and s[i + 1] == "/":
                state = NORMAL
                i += 2
            else:
                i += 1
        elif state == SQUO:
            # Verilog allows escaped quotes like \' and escaped backslashes
            if ch == "\\" and i + 1 < n:
                i += 2
            elif ch == "'":
                state = NORMAL
                i += 1
            else:
                i += 1
        elif state == DQUO:
            if ch == "\\" and i + 1 < n:
                i += 2
            elif ch == '"':
                state = NORMAL
                i += 1
            else:
                i += 1
    return "".join(out)

def bracket_imbalance(s: str):
    """
    Return (unmatched_open_count, unmatched_close_count) aggregated over (), [], {}.
    Uses proper stack discipline and treats cross-type mismatches as a close-unmatched.
    """
    stacks = {o: [] for o in OPENERS}
    unmatched_close = {"()": 0, "[]": 0, "{}": 0}
    key_for = {"(": "()", ")": "()", "[": "[]", "]": "[]", "{": "{}", "}": "{}"}

    for ch in s:
        if ch in OPENERS:
            stacks[ch].append(ch)
        elif ch in CLOSERS:
            opener = MATCH_FOR_CLOSE[ch]
            if stacks[opener]:
                stacks[opener].pop()
            else:
                unmatched_close[key_for[ch]] += 1

    unmatched_open = { "()" : len(stacks["("]),
                       "[]" : len(stacks["["]),
                       "{}" : len(stacks["{"]) }

    total_open  = sum(unmatched_open.values())
    total_close = sum(unmatched_close.values())
    return total_open, total_close, unmatched_open, unmatched_close

def check_text(text: str):
    cleaned = strip_comments_and_strings(text or "")
    return bracket_imbalance(cleaned)

def main():
    ap = argparse.ArgumentParser(description="Print indices with bracket imbalance in ioheader or verilog_code.")
    ap.add_argument("jsonl", help="Path to input JSONL")
    ap.add_argument("-v", "--verbose", action="store_true", help="Show per-field breakdown for each failing index")
    args = ap.parse_args()

    count = 0
    total = 0
    try:
        f = open(args.jsonl, "r", encoding="utf-8", errors="ignore")
    except OSError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    with f:
        for ln, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            total += 1
            try:
                obj = json.loads(s)
            except Exception as e:
                print(f"[WARN] {args.jsonl}:{ln}: bad JSON ({e}); skipping.", file=sys.stderr)
                continue
            idx = obj.get("index")
            ioheader = obj.get("ioheader", "")
            vcode    = obj.get("verilog_code", obj.get("full_text", ""))  # fallback if you use full_text

            io_o, io_c, io_open_map, io_close_map = check_text(ioheader)
            vc_o, vc_c, vc_open_map, vc_close_map = check_text(vcode)

            imbalanced = (io_o + io_c) > 0 or (vc_o + vc_c) > 0
            if imbalanced:
                count += 1
                print(idx if idx is not None else f"(no-index at line {ln})")
                if args.verbose:
                    def fmt(open_total, close_total, omap, cmap):
                        return (f"opens={open_total}, closes={close_total}, "
                                f"detail_open={omap}, detail_close={cmap}")
                    if (io_o + io_c) > 0:
                        print(f"  ioheader: {fmt(io_o, io_c, io_open_map, io_close_map)}")
                    if (vc_o + vc_c) > 0:
                        print(f"  verilog_code: {fmt(vc_o, vc_c, vc_open_map, vc_close_map)}")

    print(f"\nScanned {total} lines; {count} with imbalance.", file=sys.stderr)

if __name__ == "__main__":
    main()


##==================================================
##==================================================

## COUNT THE NUMBER OF UNKNOWN LICENSES IN THE JSONL FILE
##==================================================

import json, sys
path = sys.argv[1] if len(sys.argv) > 1 else "new_edits_and_counts_full_text2.jsonl"
cnt = 0
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            if json.loads(line).get("lic_name") == "Unknown":
                cnt += 1
        except json.JSONDecodeError:
            pass
print(cnt)
##==================================================
##==================================================


## COUNT BRACKET BALANCE, ENDMODULE IN IOHEADER, AND COMMENT TOKENS IN THE JSONL FILE
##==================================================

import argparse, json, sys, os
from collections import defaultdict

# We consider (), [], {} as "brackets".
PAIRS = {"(": ")", "[": "]", "{": "}"}
OPENERS = set(PAIRS.keys())
CLOSERS = set(PAIRS.values())
MATCH_FOR_CLOSE = {v: k for k, v in PAIRS.items()}

def count_bracket_imbalance(s: str):
    """
    Return dict with unmatched opens/closes per bracket type and a total.
    We treat ordering (stack discipline). Mismatches count as a close-unmatched,
    and the remaining stack size counts as open-unmatched.
    """
    stacks = {o: [] for o in OPENERS}
    unmatched_close = {"()": 0, "[]": 0, "{}": 0}
    key_for = {"(": "()", ")": "()", "[": "[]", "]": "[]", "{": "{}", "}": "{}"}

    for ch in s:
        if ch in OPENERS:
            stacks[ch].append(ch)
        elif ch in CLOSERS:
            opener = MATCH_FOR_CLOSE[ch]
            if stacks[opener]:
                stacks[opener].pop()
            else:
                unmatched_close[key_for[ch]] += 1

    unmatched_open = {
        "()" : len(stacks["("]),
        "[]" : len(stacks["["]),
        "{}" : len(stacks["{"])
    }

    per_type_total = {
        "()" : unmatched_open["()"] + unmatched_close["()"],
        "[]" : unmatched_open["[]"] + unmatched_close["[]"],
        "{}" : unmatched_open["{}"] + unmatched_close["{}"],
    }
    return {
        "unmatched_open": unmatched_open,
        "unmatched_close": unmatched_close,
        "per_type_total": per_type_total,
        "total": sum(per_type_total.values())
    }

def token_counts(s: str):
    """
    Count non-overlapping occurrences of //, /*, */ in s.
    (Usual expectation for comment tokens.)
    """
    return {
        "//": s.count("//"),
        "/*": s.count("/*"),
        "*/": s.count("*/"),
    }

def main():
    ap = argparse.ArgumentParser(
        description="Count bracket imbalances, 'endmodule' in ioheader, and comment tokens in a JSONL file; also save indices for each case."
    )
    ap.add_argument("jsonl_file", help="Path to JSONL file")
    ap.add_argument(
        "--outprefix",
        default="report",
        help="Prefix for output index lists (default: 'report')"
    )
    args = ap.parse_args()

    if not os.path.isfile(args.jsonl_file):
        print(f"ERROR: file not found: {args.jsonl_file}", file=sys.stderr)
        sys.exit(1)

    # Accumulators
    n_entries = 0
    n_endmodule_in_ioheader = 0

    # Per-key bracket imbalance totals (sum over all entries)
    keys = ["full_text", "ioheader", "verilog_code"]
    bracket_totals = {
        k: {"()": 0, "[]": 0, "{}": 0, "ALL": 0}
        for k in keys
    }
    # Overall across all three fields
    overall_brackets = {"()": 0, "[]": 0, "{}": 0, "ALL": 0}

    # Comment token totals across any of the keys
    totals_tokens = {"//": 0, "/*": 0, "*/": 0}

    # Sets to store indices for each condition
    idx_bracket_imbalance = set()
    idx_endmodule_in_ioheader = set()
    idx_comment_tokens = set()

    with open(args.jsonl_file, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                print(f"[WARN] Skipping bad JSON at line {line_no}: {e}", file=sys.stderr)
                continue

            # Require an index to save; if missing, warn and skip saving but still count stats
            idx = obj.get("index", None)
            if idx is None:
                print(f"[WARN] Line {line_no} has no 'index' key; stats counted but index cannot be saved.", file=sys.stderr)

            n_entries += 1

            ft = str(obj.get("full_text", "") or "")
            ih = str(obj.get("ioheader", "") or "")
            vc = str(obj.get("verilog_code", "") or "")

            # 'endmodule' in ioheader (case-sensitive)
            endmodule_here = ("endmodule" in ih)
            if endmodule_here:
                n_endmodule_in_ioheader += 1
                if idx is not None:
                    idx_endmodule_in_ioheader.add(idx)

            # Bracket imbalances per key
            entry_total_imbalance = 0
            for k, text in (("full_text", ft), ("ioheader", ih), ("verilog_code", vc)):
                res = count_bracket_imbalance(text)
                for t in ("()", "[]", "{}"):
                    bracket_totals[k][t] += res["per_type_total"][t]
                    overall_brackets[t] += res["per_type_total"][t]
                bracket_totals[k]["ALL"] += res["total"]
                overall_brackets["ALL"] += res["total"]
                entry_total_imbalance += res["total"]

            if entry_total_imbalance > 0 and idx is not None:
                idx_bracket_imbalance.add(idx)

            # Token counts across ANY key (sum on concatenated text)
            joined = ft + "\n" + ih + "\n" + vc
            tc = token_counts(joined)
            for tok in totals_tokens:
                totals_tokens[tok] += tc[tok]
            if (tc["//"] + tc["/*"] + tc["*/"]) > 0 and idx is not None:
                idx_comment_tokens.add(idx)

    print("=== Summary ===")
    print(f"Entries processed: {n_entries}")
    print(f'Entries with "endmodule" in ioheader: {n_endmodule_in_ioheader}')
    print()
    print("Bracket imbalance totals (sum of unmatched opens + unmatched closes):")
    for k in keys:
        t = bracket_totals[k]
        print(f"  {k}: ()={t['()']}  []={t['[]']}  {{}}={t['{}']}  ALL={t['ALL']}")
    t = overall_brackets
    print(f"  OVERALL: ()={t['()']}  []={t['[]']}  {{}}={t['{}']}  ALL={t['ALL']}")
    print()
    print("Comment token counts across full_text + ioheader + verilog_code:")
    print(f"  // = {totals_tokens['//']}")
    print(f"  /* = {totals_tokens['/*']}")
    print(f"  */ = {totals_tokens['*/']}")

    out_brackets = f"{args.outprefix}_bracket_imbalance_indices.txt"
    out_endmodule = f"{args.outprefix}_endmodule_in_ioheader_indices.txt"
    out_comments = f"{args.outprefix}_comment_token_indices.txt"

    def write_idx_list(path, idxset, label):
        try:
            with open(path, "w", encoding="utf-8") as g:
                for v in sorted(idxset):
                    g.write(f"{v}\n")
            print(f"{label}: wrote {len(idxset)} indices to {path}")
        except Exception as e:
            print(f"[ERROR] Failed writing {label} to {path}: {e}", file=sys.stderr)

    write_idx_list(out_brackets, idx_bracket_imbalance, "Bracket-imbalance indices")
    write_idx_list(out_endmodule, idx_endmodule_in_ioheader, '"endmodule" in ioheader indices')
    write_idx_list(out_comments, idx_comment_tokens, "Comment-token indices")

if __name__ == "__main__":
    main()
##==================================================
##==================================================


## COUNT THE NUMBER OF EMPTY PARENTS AND CHILDREN IN THE JSONL FILE
##==================================================

import json, sys, re

path = sys.argv[1] if len(sys.argv) > 1 else "data.jsonl"

def is_empty(v):
    if v is None: 
        return True
    if isinstance(v, str):
        return re.sub(r"\s+", "", v) == ""
    if isinstance(v, (list, tuple, dict, set)):
        return len(v) == 0
    return False  # numbers/bools considered non-empty

total = parent_empty = children_empty = either_empty = both_empty = 0

with open(path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        total += 1
        pe = ("parents" not in obj) or is_empty(obj.get("parent"))
        ce = ("children" not in obj) or is_empty(obj.get("children"))

        if pe: parent_empty += 1
        if ce: children_empty += 1
        if pe or ce: either_empty += 1
        if pe and ce: both_empty += 1

print(f"Total lines: {total}")
print(f"parent empty (or missing): {parent_empty}")
print(f"children empty (or missing): {children_empty}")
print(f"Either empty: {either_empty}")
print(f"Both empty: {both_empty}")

##==================================================
##==================================================    

## DELETE THE LOG FILES THAT CONTAIN THE LINE: /bin/sh: 1: verilator: not found
##==================================================
import argparse, os, sys
from pathlib import Path

PATTERN = b"/bin/sh: 1: verilator: not found"

def log_files(root: Path, recursive: bool):
    if recursive:
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if name.lower().endswith(".log"):
                    yield Path(dirpath) / name
    else:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() == ".log":
                yield p

def file_contains_pattern(path: Path, pattern: bytes, chunk_size: int = 1 << 20) -> bool:
    # Read in binary to avoid encoding issues; search chunk-wise.
    # Handles pattern spanning chunk boundaries by overlapping.
    overlap = len(pattern) - 1
    try:
        with path.open("rb") as f:
            prev = b""
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                data = prev + chunk
                if pattern in data:
                    return True
                prev = data[-overlap:] if overlap > 0 else b""
        return False
    except Exception as e:
        print(f"[WARN] Skipping {path}: {e}", file=sys.stderr)
        return False

def main():
    ap = argparse.ArgumentParser(
        description="Delete .log files that contain the line: /bin/sh: 1: verilator: not found"
    )
    ap.add_argument("folder", nargs="?", default=".", help="Folder to scan (default: current directory)")
    ap.add_argument("-n", "--dry-run", action="store_true", help="Show what would be deleted without deleting")
    ap.add_argument("-R", "--non-recursive", action="store_true", help="Only scan the top-level folder")
    ap.add_argument("-v", "--verbose", action="store_true", help="Print each checked file")
    args = ap.parse_args()

    root = Path(args.folder).resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] Not a directory: {root}", file=sys.stderr)
        sys.exit(2)

    to_delete = []
    checked = 0

    for f in log_files(root, recursive=not args.non_recursive):
        checked += 1
        if args.verbose:
            print(f"[CHECK] {f}")
        if file_contains_pattern(f, PATTERN):
            to_delete.append(f)

    if args.dry_run:
        for f in to_delete:
            print(f"DELETE: {f}")
        print(f"\n[DRY-RUN] {len(to_delete)} of {checked} .log files match; nothing deleted.")
        return

    deleted = 0
    for f in to_delete:
        try:
            f.unlink()
            print(f"Deleted: {f}")
            deleted += 1
        except Exception as e:
            print(f"[ERROR] Failed to delete {f}: {e}", file=sys.stderr)

    print(f"\nDone. Deleted {deleted} of {checked} .log files.")

if __name__ == "__main__":
    main()
##==================================================
##==================================================




## FILTER THE JSONL FILE BY THE LOG FILES
##==================================================
import json
import os

def filter_jsonl_by_log(jsonl_file, log_folder, output_file):
    """
    Extract lines from jsonl_file whose 'index' value has a corresponding <index>.log file in log_folder.
    Saves the filtered lines into output_file.
    """
    filtered = []
    
    # Collect all available .log filenames in the folder (without extension)
    log_indices = {os.path.splitext(f)[0] for f in os.listdir(log_folder) if f.endswith(".log")}
    
    with open(jsonl_file, "r", encoding="utf-8") as infile, \
         open(output_file, "w", encoding="utf-8") as outfile:
        
        for line in infile:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip bad lines

            index_val = str(obj.get("index"))
            if index_val in log_indices:
                outfile.write(json.dumps(obj) + "\n")
                filtered.append(obj)
    
    print(f"Filtered {len(filtered)} lines. Saved to {output_file}.")

# Example usage
if __name__ == "__main__":
    jsonl_file = "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/with_keys.jsonl"          # path to your jsonl file
    log_folder = "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/test"         # path to your folder containing <index>.log files
    output_file = "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/filtered.jsonl"     # where to save results
    
    filter_jsonl_by_log(jsonl_file, log_folder, output_file)

##==================================================
##==================================================




## FIND THE MISSING INDICES IN THE JSONL FILE
##==================================================
import json

def find_missing_indices(jsonl_file):
    existing_indices = set()
    referenced_indices = set()

    with open(jsonl_file, "r", encoding="utf-8") as infile:
        for line in infile:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip invalid JSON lines

            # collect the actual existing indices
            if "index" in obj:
                existing_indices.add(obj["index"])

            # collect referenced indices from parents and children
            for key in ("parents", "children"):
                if key in obj and isinstance(obj[key], list):
                    referenced_indices.update(obj[key])

    # find indices that are referenced but missing from the file
    missing_indices = referenced_indices - existing_indices
    return list(missing_indices)


if __name__ == "__main__":
    jsonl_file = "hier.jsonl"  # path to your jsonl file
    missing = find_missing_indices(jsonl_file)
    with open("missing_index_test.txt","w") as f:
      f.write(str(missing))
    count = len(missing)
    print(count)
##==================================================
##==================================================




## FIND THE TOP NODES AND THEIR CHILDREN IN THE JSONL FILE
##==================================================
import argparse, json, sys
from collections import deque
from typing import Dict, List, Set

# ----------------------------
# JSONL loading
# ----------------------------
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
            idx = obj["index"]
            if not isinstance(idx, int):
                print(f"[WARN] {path}:{ln}: 'index' not int; skipping.", file=sys.stderr)
                continue
            if idx in data:
                print(f"[WARN] duplicate index {idx}; keeping first occurrence.", file=sys.stderr)
                continue
            data[idx] = obj
    if not data:
        print(f"[ERROR] no valid records in {path}", file=sys.stderr)
        sys.exit(2)
    return data

# ----------------------------
# Graph helpers
# ----------------------------
def children_of(obj: dict) -> List[int]:
    raw = obj.get("children") or []
    if not isinstance(raw, (list, tuple)):
        return []
    return [c for c in raw if isinstance(c, int)]

def derive_top_nodes(D: Dict[int, dict]) -> List[int]:
    all_nodes: Set[int] = set(D.keys())
    as_child: Set[int] = set()
    for o in D.values():
        as_child.update(children_of(o))
    tops = sorted(all_nodes - as_child)
    if tops:
        return tops
    # fallback: parents == []
    tops2 = [i for i, o in D.items()
             if isinstance(o.get("parents") or [], list) and not o.get("parents")]
    return sorted(tops2) if tops2 else sorted(all_nodes)

def descendants_closure(start: int, D: Dict[int, dict]) -> Set[int]:
    seen: Set[int] = set()
    q = deque([start])
    while q:
        u = q.popleft()
        if u in seen:
            continue
        seen.add(u)
        for v in children_of(D.get(u, {})):
            if v not in seen:
                q.append(v)
    return seen

# ----------------------------
# Main
# ----------------------------
def main():
    ap = argparse.ArgumentParser(
        description="From a JSONL with indices and children, write a JSON file listing each top's descendant indices."
    )
    ap.add_argument("jsonl", help="Path to input JSONL file")
    ap.add_argument("-o", "--out", default="top_children_map.json",
                    help="Output JSON file (default: top_children_map.json)")
    ap.add_argument("--format", choices=["array", "dict"], default="array",
                    help="Output format: 'array' of objects or 'dict' mapping top->list (default: array)")
    ap.add_argument("--include-top", action="store_true",
                    help="Include the top index itself in the children list")
    args = ap.parse_args()

    D = load_jsonl(args.jsonl)
    tops = derive_top_nodes(D)
    print(f"[INFO] Loaded {len(D)} nodes. Found {len(tops)} top node(s).")

    if args.format == "array":
        out_obj = []
        for t in tops:
            closure = sorted(descendants_closure(t, D))
            if not args.include_top:
                closure = [x for x in closure if x != t]
            out_obj.append({"top": t, "children": closure})
    else:
        out_obj = {}
        for t in tops:
            closure = sorted(descendants_closure(t, D))
            if not args.include_top:
                closure = [x for x in closure if x != t]
            out_obj[str(t)] = closure  # JSON object keys must be strings
            print("done")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, indent=2, ensure_ascii=False)

    print(f"[DONE] Wrote {args.out}")

if __name__ == "__main__":
    main()
##==================================================
##==================================================



## FILTER THE JSONL FILE BY THE IOHEADER AND VERILOG CODE
##==================================================
import json, re, sys

def is_blank(x: str) -> bool:
    return x is None or (isinstance(x, str) and x.strip() == "")

def is_endmodule_only(code: str) -> bool:
    # remove all whitespace (\n, \t, spaces, etc.) and check exact match
    return re.sub(r"\s+", "", code or "") == "endmodule"

def keep(obj: dict) -> bool:
    ioheader = obj.get("ioheader", "")
    vcode = obj.get("verilog_code", "")
    if is_blank(ioheader):
        return False
    if is_blank(vcode):
        return False
    if is_endmodule_only(vcode):
        return False
    return True

def main(in_path: str, out_path: str):
    in_count = kept = dropped = 0
    with open(in_path, "r", encoding="utf-8") as fin, \
         open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            in_count += 1
            try:
                obj = json.loads(line)
            except Exception:
                dropped += 1
                continue
            if keep(obj):
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                kept += 1
            else:
                dropped += 1
    print(f"Input lines: {in_count}")
    print(f"Kept lines : {kept}")
    print(f"Dropped    : {dropped}")

if __name__ == "__main__":
    main("/mnt/shared/gpfs/escad_verilog_dataset/RERUN/full_no_comments.jsonl", "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/New_filtered_no_comments.jsonl")

##==================================================
##==================================================


## ADD BACK THE MISSING INDICES TO THE JSONL FILE
##==================================================
import json

# paths to your files
text_file = "missing_index_round2_2.txt"        # file with list of index values
input_jsonl = "hier.jsonl"      # your source JSONL file
output_jsonl = "filtered_new_add_back2_2.jsonl"  # file to save matching lines


# read the list of indexes (in JSON array format)
with open(text_file, "r") as f:
    content = f.read().strip()
    # parse the list safely
    valid_indexes = set(map(str, json.loads(content)))

# filter jsonl
with open(input_jsonl, "r") as infile, open(output_jsonl, "w") as outfile:
    for line in infile:
        try:
            obj = json.loads(line)
            if str(obj.get("index")) in valid_indexes:
                outfile.write(line)  # write the whole line as-is
        except json.JSONDecodeError:
            continue  # skip malformed lines
##==================================================
##==================================================


## COUNT THE NUMBER OF BRACKET MISMATCH, COMMENTS, AND DUPLICATES IN THE JSONL FILE
##==================================================
# read a jsonl file
import json
verilog_code_set = set()
ioheader_set = set()
with open('merged.jsonl', 'r') as f:
    for line in f:
        data = json.loads(line)
        #read the kye called verilog_code
        verilog_code = data['verilog_code']
        ioheader = data['ioheader']
        full_text = data['full_text']
        index = data['index']
        parents = data['parents']
        children = data['children']
        #count the number of [ in verilog_code
        num_brackets_open_square = verilog_code.count('[')
        num_brackets_close_square = verilog_code.count(']')
        num_brackets_open_curly = verilog_code.count('{')
        num_brackets_close_curly = verilog_code.count('}')
        num_brackets_open_round = verilog_code.count('(')
        num_brackets_close_round = verilog_code.count(')')
        if num_brackets_open_square != num_brackets_close_square or num_brackets_open_curly != num_brackets_close_curly or num_brackets_open_round != num_brackets_close_round:
            with open('text_brackets_mismatch.txt', 'a') as f:
                f.write(f"{index}\n")
        
        #count the number of comments in verilog_code
        num_comments = verilog_code.count('//') + verilog_code.count('/*') + verilog_code.count('*/')
        if num_comments > 0:
            with open('text_comments.txt', 'a') as f:
                f.write(f"{index}\n")
        
        verilog_code_new = verilog_code.strip().replace(' ', '').replace('\n', '').replace('\t', '').replace('\r', '')
        ioheader_new = ioheader.strip().replace(' ', '').replace('\n', '').replace('\t', '').replace('\r', '')
        #if the verilog_code in this run is already exactly the same as one in the set then make it as a duplicate
        #length of set of verilog_code and ioheader
        len_verilog_code_set = len(verilog_code_set)

        for i in range(len_verilog_code_set):
            if verilog_code_new == list(verilog_code_set)[i] and ioheader_new == list(ioheader_set)[i]:
                if parents == [] or children == []:
                    with open('text_duplicate_no_parents_or_children.txt', 'a') as f:
                        f.write(f"{index}\n")
                else:
                    with open('text_duplicate_with_parents_and_children.txt', 'a') as f:
                        f.write(f"{index}\n")
                break
        verilog_code_set.add(verilog_code_new)
        ioheader_set.add(ioheader_new)

        full_text_new = ioheader + verilog_code
        #add the full_text_new key to the jsonl file
        data['full_text_new'] = full_text_new
        #write the data to a new jsonl file
        with open('new_edits_and_counts_full_text.jsonl', 'a') as f:
            f.write(json.dumps(data) + '\n')
##==================================================
##==================================================



## REINDEX THE JSONL FILE
##==================================================
import json, sys

def main(in_path: str, out_path: str):
    idx = 0
    with open(in_path, "r", encoding="utf-8") as fin, \
         open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # skip malformed lines (doesn't advance idx)
                continue
            obj["index"] = idx  # overwrite if it already exists
            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            idx += 1

if __name__ == "__main__":
    main("/mnt/shared/gpfs/escad_verilog_dataset/RERUN/modules_jsonl_rerun.jsonl", "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/re_label_new.jsonl")

##==================================================
##==================================================




## FIND THE INDEX VALUE IN THE JSONL FILE
##==================================================
import sys, json

def usage():
    print(f"Usage: {sys.argv[0]} <path/to/file.jsonl> <index_value>")
    print("Tip: <index_value> can be a number (e.g., 42) or a string (e.g., abc).")
    sys.exit(1)

if len(sys.argv) != 3:
    usage()

path = sys.argv[1]
target_raw = sys.argv[2]

# Try to interpret the target as JSON (so 42 -> int, "abc" -> str if you pass quotes).
# If that fails, keep it as a plain string.
try:
    target_val = json.loads(target_raw)
except json.JSONDecodeError:
    target_val = target_raw
target_str = str(target_val)

found = 0
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        line_stripped = line.rstrip("\n")
        if not line_stripped.strip():
            continue
        try:
            obj = json.loads(line_stripped)
        except json.JSONDecodeError:
            continue  # skip malformed lines

        if "index" not in obj:
            continue

        v = obj["index"]
        # match either exact value OR stringified equality to be forgiving
        if v == target_val or str(v) == target_str:
            print(line_stripped)
            found += 1

if found == 0:
    print("notfound")
    sys.exit(1)

##==================================================
##==================================================





## ANNOTATE THE JSONL FILE WITH THE IS_VERIFIED AND IS_DEPENDENCY
##==================================================
import argparse, json, os, sys
from collections import defaultdict

def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"JSON parse error on line {ln}: {e}", file=sys.stderr)
                sys.exit(1)
            yield obj

def write_jsonl(path, objs):
    with open(path, "w", encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

def coerce_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    # Sometimes people store singletons; be permissive.
    return [value]

def main():
    ap = argparse.ArgumentParser(description="Annotate JSONL with is_verified and is_dependency.")
    ap.add_argument("jsonl_in", help="Input JSONL file (each line a JSON object with key 'index')")
    ap.add_argument("logs_dir", help="Directory containing <index>.log files")
    ap.add_argument("-o", "--out", default=None, help="Output JSONL path (default: <input>.annotated.jsonl)")
    args = ap.parse_args()

    if not os.path.isfile(args.jsonl_in):
        print(f"Input file not found: {args.jsonl_in}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.logs_dir):
        print(f"Logs directory not found: {args.logs_dir}", file=sys.stderr)
        sys.exit(1)

    # First pass: read all objects, gather dependency sources
    objs = []
    dep_sources = defaultdict(set)  # index_value -> set of indices of lines that reference it
    for obj in load_jsonl(args.jsonl_in):
        if "index" not in obj:
            print("ERROR: every object must have an 'index' key.", file=sys.stderr)
            sys.exit(1)
        idx = obj["index"]
        parents = coerce_list(obj.get("parents"))
        children = coerce_list(obj.get("children"))
        for p in parents:
            dep_sources[p].add(idx)
        for c in children:
            dep_sources[c].add(idx)
        objs.append(obj)

    # Second pass: compute flags and write
    out_path = args.out or (os.path.splitext(args.jsonl_in)[0] + ".annotated.jsonl")
    annotated = []
    for obj in objs:
        idx = obj["index"]

        # is_verified: False if <index>.log exists, else True
        log_path = os.path.join(args.logs_dir, f"{idx}.log")
        is_verified = not os.path.exists(log_path)

        # is_dependency: True if this idx appears in any other line's parents/children
        sources = dep_sources.get(idx, set())
        # Exclude self if someone ever listed itself
        if idx in sources:
            sources = set(sources)
            sources.discard(idx)
        is_dependency = len(sources) > 0

        obj["is_verified"] = is_verified
        obj["is_dependency"] = is_dependency
        annotated.append(obj)

    write_jsonl(out_path, annotated)
    print(f"Done. Wrote: {out_path}")

if __name__ == "__main__":
    main()
##==================================================
##==================================================




## FILTER THE JSONL FILE BY THE IS_VERIFIED AND PRUNE INVALID PARENT/CHILD REFERENCES UNTIL STABLE
##==================================================
import argparse, json, sys
from pathlib import Path

def read_jsonl(path):
    objs = []
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                objs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[WARN] Skipping bad JSON at line {ln}: {e}", file=sys.stderr)
    return objs

def write_jsonl(path, objs):
    with open(path, "w", encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

def as_index(o):
    # assumes index is hashable (int/str). Cast to str if your data mixes types.
    return o.get("index")

def refs(o):
    p = o.get("parents") or []
    c = o.get("children") or []
    # Ensure they’re lists of indices; ignore Nones
    return set(x for x in list(p) + list(c) if x is not None)

def filter_jsonl(objs, verbose=True):
    # 1) initial filter: is_verified must be True (missing -> treat as True)
    keep = [o for o in objs if o.get("is_verified", True) is True]

    # build map for quick lookups while preserving order-based stability
    idx_to_obj = {as_index(o): o for o in keep if as_index(o) is not None}

    # 2) prune iteratively until stable
    changed = True
    round_no = 0
    while changed:
        round_no += 1
        changed = False
        present = set(idx_to_obj.keys())

        # find indices that reference missing parents/children
        bad = []
        for idx, o in idx_to_obj.items():
            missing = refs(o) - present
            if missing:
                bad.append(idx)

        if bad:
            changed = True
            for idx in bad:
                idx_to_obj.pop(idx, None)
            if verbose:
                print(f"[INFO] Round {round_no}: removed {len(bad)} nodes with missing refs", file=sys.stderr)

    # return in original input order (filtered)
    final_indices = set(idx_to_obj.keys())
    result = [o for o in objs if as_index(o) in final_indices]
    return result

def main():
    ap = argparse.ArgumentParser(description="Filter JSONL by is_verified and prune invalid parent/child references until stable.")
    ap.add_argument("input_jsonl", help="Path to input JSONL")
    ap.add_argument("output_jsonl", help="Path to write filtered JSONL")
    ap.add_argument("--quiet", action="store_true", help="Reduce logging")
    args = ap.parse_args()

    objs = read_jsonl(args.input_jsonl)
    if not objs:
        print("[ERROR] No valid objects found.", file=sys.stderr)
        sys.exit(1)

    before = len(objs)
    result = filter_jsonl(objs, verbose=not args.quiet)
    after = len(result)

    write_jsonl(args.output_jsonl, result)

    if not args.quiet:
        print(f"[DONE] kept {after} / {before} lines", file=sys.stderr)

if __name__ == "__main__":
    main()
##==================================================
##==================================================