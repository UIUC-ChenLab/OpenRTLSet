## VERIFY THE JSONL FILE ITERATION 
##==================================================
import argparse
import os
import sys
import json
import subprocess
import tempfile
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

def parse_args():
    parser = argparse.ArgumentParser(
        description="Parse a JSONL file and process its contents."
    )
    parser.add_argument(
        "jsonl_file",
        type=str,
        help="Path to the JSONL file to parse"
    )
    args = parser.parse_args()
    if not os.path.isfile(args.jsonl_file):
        print(f"Error: File '{args.jsonl_file}' does not exist or is not a file.", file=sys.stderr)
        sys.exit(1)
    return args.jsonl_file

def basic_parsing_checks(jsonl_obj: dict):
    # Only keep type check now; duplicates no longer fatal
    if type(jsonl_obj) is not dict:
        print(f"ERROR: bad type on object: {jsonl_obj}")
        sys.exit(-1)

def process_json(filepath: str) -> 'dict[int, dict]':
    print("Loading structure")
    dict_to_return: 'dict[int, dict]' = {}
    dup_count = 0
    with open(filepath, 'r', encoding='utf-8') as json_f:
        for line_no, line in enumerate(json_f, 1):
            obj: dict = json.loads(line)
            basic_parsing_checks(obj)
            my_key = obj['index']
            if my_key in dict_to_return:
                dup_count += 1
                # Keep the first occurrence; skip later duplicates
                print(f"[WARN] Duplicate index {my_key} at line {line_no}; keeping first occurrence, skipping this one.", file=sys.stderr)
                continue
            dict_to_return[my_key] = obj
    print(f"Finished processing datastructure. It has {len(dict_to_return.keys())} entries"
          + (f" (skipped {dup_count} duplicates)" if dup_count else ""))
    return dict_to_return

def write_full_entry(jsonl_obj: dict, target_filepath: str):
    ioheader = jsonl_obj.get('ioheader', '')
    code = jsonl_obj.get('verilog_code', '')
    with open(target_filepath, 'w') as out_f:
        out_f.write(ioheader)
        # be forgiving about missing newline between header/body
        if ioheader and not ioheader.endswith("\n"):
            out_f.write("\n")
        out_f.write(code)

def _all_descendants(start_idx: int, all_objs: dict[int, dict]) -> set[int]:
    """
    Compute the full transitive closure of children for a given index.
    Cycle-safe (uses 'visited'). Includes only *children*, not the start node.
    """
    visited: set[int] = set()
    q = deque()

    # Seed with immediate children (if any)
    root = all_objs.get(start_idx, {})
    for c in root.get('children', []) or []:
        if isinstance(c, int) and c not in visited:
            visited.add(c)
            q.append(c)

    # BFS over children-of-children, etc.
    while q:
        cur = q.popleft()
        cur_obj = all_objs.get(cur)
        if not cur_obj:
            continue
        for nxt in cur_obj.get('children', []) or []:
            if isinstance(nxt, int) and nxt not in visited:
                visited.add(nxt)
                q.append(nxt)
    return visited

def _lint_one(index: int, obj: dict, all_objs: dict, verilator_cmd: str) -> tuple[str, int]:
    """
    Returns: ("skipped"|"pass"|"fail", index)
    - Writes <index>.log on failure (like original code).
    - Uses a per-task temp dir to avoid file collisions.
    - Uses the full transitive closure of 'children'.
    """
    # Skip if .log already exists in current working directory
    log_path = f"{index}.log"
    if os.path.exists(log_path):
        return ("skipped", index)

    with tempfile.TemporaryDirectory(prefix=f"lint_{index}_") as tmpdir:
        # Write top module
        top_sv = os.path.join(tmpdir, f"{index}.sv")
        write_full_entry(obj, top_sv)
        sv_files = [top_sv]

        # Write ALL descendants (children, grandchildren, ...)
        all_kids = _all_descendants(index, all_objs)
        for child in all_kids:
            child_obj = all_objs.get(child)
            if not child_obj:
                # Missing child in dictionary; let Verilator complain if referenced
                continue
            child_sv = os.path.join(tmpdir, f"{child}.sv")
            write_full_entry(child_obj, child_sv)
            sv_files.append(child_sv)

        # Compose command and run in temp dir
        sv_basenames = " ".join(os.path.basename(p) for p in sv_files)
        full_cmd = ["/bin/sh", "-lc", f"{verilator_cmd} {sv_basenames}"]
        result = subprocess.run(full_cmd, cwd=tmpdir, capture_output=True, text=True)

        if result.returncode != 0:
            # On failure, write stderr to <index>.log in CWD (consistent with original)
            with open(log_path, "w") as errf:
                errf.write(result.stderr)
            return ("fail", index)

        return ("pass", index)

def lint_test(jsonl_dict: 'dict[int, dict]', fail_log_path: str):
    print("Starting Lint tests!")
    verilator_cmd = 'verilator --lint-only --no-timing -Wno-style -Wno-fatal --bbox-sys --bbox-unsup'

    total = len(jsonl_dict)
    failed_indices = []
    skipped = 0
    passed = 0

    # If you prefer CPU-based default, replace 10 with (os.cpu_count() or 1)
    max_workers = max(1, 10 or 1)
    print(f"Running with up to {max_workers} parallel workers...")

    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for idx, obj in jsonl_dict.items():
            futures.append(ex.submit(_lint_one, idx, obj, jsonl_dict, verilator_cmd))

        for i, fut in enumerate(as_completed(futures), 1):
            status, idx = fut.result()
            if status == "skipped":
                skipped += 1
            elif status == "pass":
                passed += 1
            elif status == "fail":
                failed_indices.append(idx)

            # Lightweight progress
            if i % 100 == 0 or i == total:
                print(f"Progress: {i}/{total} | pass={passed} fail={len(failed_indices)} skipped={skipped}")

    # Write failures once (thread-safe)
    if failed_indices:
        with open(fail_log_path, 'w') as f:
            for idx in failed_indices:
                f.write(str(idx) + "\n")

    print(f"Done. Total={total} | Passed={passed} | Failed={len(failed_indices)} | Skipped(existing logs)={skipped}")

    if failed_indices:
        print(f"ERROR: >0 TESTCASES FAILED LINT.")
        print(f"See {fail_log_path} for the full list. {len(failed_indices)} entries failed lint!")
        sys.exit(-1)

def build_test(jsonl_dict: 'dict[int, dict]', fail_log_path: str):
    pass

if __name__ == "__main__":
    jsonl_path: str = parse_args()
    jsonl_dict: 'dict[int, dict]' = process_json(jsonl_path)
    lint_test(jsonl_dict, "lint_failures.txt")
    # build_test(jsonl_dict, "build_failures.txt")
##==================================================
##==================================================