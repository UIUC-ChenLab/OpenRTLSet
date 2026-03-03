## REMOVE VERILOG COMMENTS AND MERGE DUPLICATES BY REPO_URL + CODE
##==================================================
import argparse, json, sys, re

def strip_verilog_comments(text: str) -> str:
    """
    Remove Verilog comments in two passes:
      1) Block comments:  /* ... */   (non-greedy, spans lines)
      2) Line comments:   // ... \n   (to end-of-line)
    NOTE: This simple remover doesn't protect comment-like tokens inside strings.
    """
    no_block = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    no_line  = re.sub(r'//.*?$',    '', no_block, flags=re.MULTILINE)
    return no_line

def normalize_for_dedup(text: str, aggressive_whitespace: bool = True) -> str:
    """
    Create a comparable version of text for deduplication.
    By default, removes *all* whitespace so formatting differences don't block merges.
    """
    t = text.replace('\r\n', '\n').replace('\r', '\n')
    if aggressive_whitespace:
        t = re.sub(r'\s+', '', t)
    else:
        t = "\n".join(line.rstrip() for line in t.splitlines()).strip()
    return t

def process(in_path: str, out_path: str, keep_whitespace: bool = False):
    total = 0
    cleaned = 0
    merged = 0
    buckets = {}  # (Repo_url, norm_full_text) -> record (keep first by default)

    with open(in_path, "r", encoding="utf-8", errors="ignore") as fin:
        for line_no, line in enumerate(fin, 1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception as e:
                print(f"[WARN] {in_path}:{line_no}: bad JSON ({e}); skipping.", file=sys.stderr)
                continue
            if not isinstance(obj, dict) or "full_text" not in obj or "Repo_url" not in obj:
                print(f"[WARN] {in_path}:{line_no}: missing 'full_text' or 'Repo_url'; skipping.", file=sys.stderr)
                continue

            total += 1

            # 1) remove comments
            raw = obj.get("full_text") or ""
            stripped = strip_verilog_comments(raw)
            obj["full_text"] = stripped
            cleaned += 1

            # 2) normalized code for dedup
            norm = normalize_for_dedup(stripped, aggressive_whitespace=not keep_whitespace)
            key = (obj.get("Repo_url"), norm)

            if key in buckets:
                # Keep the first record as-is; optionally fill only missing fields
                base = buckets[key]
                for k, v in obj.items():
                    if k not in base or base.get(k) in (None, "", [], {}):
                        base[k] = v
                merged += 1
            else:
                buckets[key] = obj

    with open(out_path, "w", encoding="utf-8") as fout:
        for rec in buckets.values():
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[INFO] Input lines:         {total}", file=sys.stderr)
    print(f"[INFO] Cleaned 'full_text': {cleaned}", file=sys.stderr)
    print(f"[INFO] Unique after merge:  {len(buckets)}", file=sys.stderr)
    print(f"[INFO] Merged duplicates:   {merged}", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser(
        description="Remove Verilog comments from JSONL 'full_text' and merge duplicates by Repo_url + code."
    )
    ap.add_argument("input", help="Path to input .jsonl")
    ap.add_argument("output", help="Path to output .jsonl")
    ap.add_argument(
        "--keep-whitespace",
        action="store_true",
        help="Don't strip all whitespace when comparing for duplicates."
    )
    args = ap.parse_args()
    process(args.input, args.output, keep_whitespace=args.keep_whitespace)

if __name__ == "__main__":
    main()
##==================================================
##==================================================