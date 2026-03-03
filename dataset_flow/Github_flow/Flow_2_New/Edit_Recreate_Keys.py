## EDIT/RECREATE THE IOHEADER AND VERILOG CODE TO REMOVE THE COMMENTS
##==================================================
import os, json, math, signal, contextlib
from concurrent.futures import ProcessPoolExecutor, as_completed

# --------- your per-line transformation (same logic as before, no prints) ---------
def _process_one_line(line: str):
    try:
        obj = json.loads(line)
    except Exception:
        return None  # skip bad JSON

    ioheader = obj.get('ioheader', '')
    verilog_code = obj.get('verilog_code', '')
    full_code = obj.get('full_text', '')

    ioheader_main = ""
    verilog_main = ""
    ioheader_start = ""
    verilog_start = ""

    full_code_parts = full_code.split(';')
    for i in range(len(full_code_parts)):
        part = full_code_parts[i]
        stripped = part.strip()
        test_part = stripped.replace(" ", "").replace("\n", "").replace("\t", "")

        if "module " in part and "endmodule" not in part:
            parts = part.split("module")
            module_tail = parts[-1]
            if module_tail.count("(") > module_tail.count(")"):
                for j in range(i + 1, len(full_code_parts)):
                    next_piece = full_code_parts[j]
                    module_tail += next_piece
                    full_code_parts[j] = ""
                    if ")" in next_piece:
                        break
            if module_tail.count("(") < module_tail.count(")"):
                module_tail = module_tail.replace(")", "", -1)
            ioheader_start = "module" + module_tail + ";"
            verilog_start = part.replace("module" + module_tail, "", 1) + ";"

        elif (test_part.startswith("input") or test_part.startswith("output")) and "=" not in test_part:
            ioheader_main += part + ";"
            if ioheader_main.count("(") > ioheader_main.count(")"):
                for j in range(i + 1, len(full_code_parts)):
                    next_piece = full_code_parts[j]
                    ioheader_main += ";" + next_piece
                    full_code_parts[j] = ""
                    if ")" in next_piece:
                        break
            if ioheader_main.count("(") < ioheader_main.count(")"):
                ioheader_main = ioheader_main.replace(")", "", -1)

        elif ")input" in test_part:
            tail = part.split("input")[-1]
            ioheader_main += "input " + tail + ";"
            if ioheader_main.count("(") > ioheader_main.count(")"):
                for j in range(i + 1, len(full_code_parts)):
                    next_piece = full_code_parts[j]
                    ioheader_main += ";" + next_piece
                    full_code_parts[j] = ""
                    if ")" in next_piece:
                        break
            if ioheader_main.count("(") < ioheader_main.count(")"):
                ioheader_main = ioheader_main.replace(")", "", -1)

        elif ")output" in test_part:
            tail = part.split("output")[-1]
            ioheader_main += "output " + tail + ";"
            if ioheader_main.count("(") > ioheader_main.count(")"):
                for j in range(i + 1, len(full_code_parts)):
                    next_piece = full_code_parts[j]
                    ioheader_main += ";" + next_piece
                    full_code_parts[j] = ""
                    if ")" in next_piece:
                        break
            if ioheader_main.count("(") < ioheader_main.count(")"):
                ioheader_main = ioheader_main.replace(")", "", -1)

        else:
            verilog_main += part + ";"
            if verilog_main.count("(") > verilog_main.count(")"):
                for j in range(i + 1, len(full_code_parts)):
                    next_piece = full_code_parts[j]
                    verilog_main += ";" + next_piece
                    full_code_parts[j] = ""
                    if ")" in next_piece:
                        break
            if verilog_main.count("(") < verilog_main.count(")"):
                verilog_main = verilog_main.replace(")", "", -1)

        for s in ("module)",):
            verilog_main   = verilog_main.replace(s, "")
            ioheader_start = ioheader_start.replace(s, "")
            ioheader_main  = ioheader_main.replace(s, "")
            verilog_start  = verilog_start.replace(s, "")

    verilog_full = (verilog_start + ";" + verilog_main).replace(";;", ";")
    verilog_full_parts = verilog_full.split(';')

    for j in range(len(verilog_full_parts)):
        pats = verilog_full_parts[j]
        part = pats.strip().replace(" ", "").replace("\n", "").replace("\t", "")
        if part.startswith("input") and "=" not in part:
            verilog_full_parts[j] = ""
            ioheader_main += pats + ";"
        elif part.startswith("output") and "=" not in part:
            verilog_full_parts[j] = ""
            ioheader_main += pats + ";"

    for j in range(len(verilog_full_parts)):
        pats = verilog_full_parts[j]
        if not pats:
            continue
        part = pats.strip().replace(" ", "").replace("\n", "").replace("\t", "")
        if (part.startswith("endinput") or part.startswith("endendgenerateinput")
            or part.startswith("endfunctioninput") or part.startswith("`endifinput")
            or part.startswith("`define") or part.startswith("endendfunctioninput")
            or part.startswith("`timescale") or part.startswith("`include")) and "=" not in part:
            pieces = pats.split("input")
            verilog_full_parts[j] = ";".join(pieces[0:-1])
            ioheader_main += "input " + pieces[-1] + ";"
        elif (part.startswith("endoutput") or part.startswith("endendgenerateoutput")
              or part.startswith("endfunctionoutput") or part.startswith("`endifoutput")
              or part.startswith("`define") or part.startswith("endendfunctionoutput")
              or part.startswith("`timescale") or part.startswith("`include")) and "=" not in part:
            pieces = pats.split("output")
            verilog_full_parts[j] = ";".join(pieces[0:-1])
            ioheader_main += "output " + pieces[-1] + ";"

    verilog_full = ";".join(p for p in verilog_full_parts if p)
    obj['ioheader'] = (ioheader_start + ";" + ioheader_main).replace(";;", ";")
    obj['verilog_code'] = verilog_full
    print("new2")

    try:
        return json.dumps(obj)
    except Exception:
        return None

# --------- 60s per-line timeout (Unix fast path with signal; safe fallback otherwise) ---------
class Timeout(Exception): pass

@contextlib.contextmanager
def _time_limit(seconds: int):
    # Works on Unix; no-op elsewhere
    if hasattr(signal, "SIGALRM"):
        def handler(signum, frame):
            raise Timeout()
        old = signal.signal(signal.SIGALRM, handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    else:
        # Fallback: just yield (no hard kill possible)
        yield

def process_shard(in_path: str, out_path: str, per_line_timeout_sec: int = 60) -> dict:
    """Process one shard; skip lines exceeding per_line_timeout_sec."""
    processed = 0
    written = 0
    timeouts = 0
    badjson = 0
    with open(in_path, 'r', encoding='utf-8') as fin, open(out_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            processed += 1
            try:
                with _time_limit(per_line_timeout_sec):
                    res = _process_one_line(line)
            except Timeout:
                timeouts += 1
                continue
            except Exception:
                # e.g., catastrophic parse failure outside json.loads
                badjson += 1
                continue
            if res:
                fout.write(res + "\n")
                written += 1
    return {"shard": os.path.basename(in_path), "processed": processed, "written": written, "timeouts": timeouts, "badjson": badjson}

# --------- split → parallel process → concat ---------
def split_jsonl(input_path: str, shards_dir: str, num_shards: int = 1500):
    os.makedirs(shards_dir, exist_ok=True)
    # First pass: count lines
    total = 0
    with open(input_path, 'r', encoding='utf-8') as f:
        for _ in f:
            total += 1
    if total == 0:
        return 0

    per = max(1, math.ceil(total / num_shards))
    shard_idx = 0
    written_in_shard = 0
    pad = len(str(num_shards))
    out = None

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if out is None or written_in_shard >= per:
                if out:
                    out.close()
                shard_name = f"shard_{str(shard_idx).zfill(pad)}.jsonl"
                out = open(os.path.join(shards_dir, shard_name), 'w', encoding='utf-8')
                shard_idx += 1
                written_in_shard = 0
            out.write(line)
            written_in_shard += 1

    if out:
        out.close()
    return shard_idx  # number of shards actually created

def process_all_shards(shards_dir: str, out_dir: str, workers: int = None, per_line_timeout_sec: int = 60):
    os.makedirs(out_dir, exist_ok=True)
    shard_files = sorted([f for f in os.listdir(shards_dir) if f.endswith(".jsonl")])
    tasks = []
    results = []
    max_workers = workers or min(64, os.cpu_count() or 1)

    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        for fname in shard_files:
            in_path = os.path.join(shards_dir, fname)
            out_path = os.path.join(out_dir, fname.replace(".jsonl", "_out.jsonl"))
            tasks.append(ex.submit(process_shard, in_path, out_path, per_line_timeout_sec))

        for fut in as_completed(tasks):
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({"error": str(e)})

    return results

def concat_outputs(processed_dir: str, final_path: str):
    out_files = sorted([f for f in os.listdir(processed_dir) if f.endswith("_out.jsonl")])
    with open(final_path, 'w', encoding='utf-8') as fout:
        for fname in out_files:
            with open(os.path.join(processed_dir, fname), 'r', encoding='utf-8') as fin:
                for line in fin:
                    fout.write(line)

if __name__ == "__main__":
    # ---- CONFIG ----
    INPUT = "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/edited_mid.jsonl"
    SHARDS_DIR = "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/_shards_1500"
    PROCESSED_DIR = "/mnt/shared/gpfs/escad_verilog_dataset/RERUN/_shards_1500_processed"
    FINAL = "//mnt/shared/gpfs/escad_verilog_dataset/RERUN/filtered_no_comments_new.jsonl"
    NUM_SHARDS = 1500
    WORKERS = min(64, os.cpu_count() or 1)   # adjust if you want more/less node parallelism
    PER_LINE_TIMEOUT_SEC = 60

    n = split_jsonl(INPUT, SHARDS_DIR, NUM_SHARDS)
    print(f"Created {n} shards in {SHARDS_DIR}")

    stats = process_all_shards(SHARDS_DIR, PROCESSED_DIR, WORKERS, PER_LINE_TIMEOUT_SEC)
    # optional: print aggregate stats
    total = {"processed":0,"written":0,"timeouts":0,"badjson":0}
    for s in stats:
        if "error" in s: 
            print("Shard error:", s["error"])
            continue
        for k in total: total[k] += s.get(k,0)
    print("Totals:", total)

    concat_outputs(PROCESSED_DIR, FINAL)
    print(f"Final concatenated file: {FINAL}")
