## COUNT ALL ERRORS IN THE JSONL FILE ITERATION 1
##==================================================
import argparse, json, sys, re
from collections import defaultdict, Counter

PAIRS = {"(": ")", "[": "]", "{": "}"}
OPENERS = set(PAIRS.keys())
CLOSERS = set(PAIRS.values())
MATCH_FOR_CLOSE = {v: k for k, v in PAIRS.items()}
BR_PAIR_KEYS = {"(": "()", ")": "()", "[": "[]", "]": "[]", "{": "{}", "}": "{}"}

# Regexes (case-insensitive for keywords; exact tokens where needed)
RE_MODULE_WORD = re.compile(r"\bmodule \b", re.IGNORECASE)   # matches "module " (module + whitespace)
RE_ENDMODULE = re.compile(r"\bendmodule\b", re.IGNORECASE)
RE_GENERATE = re.compile(r"\bgenerate\b", re.IGNORECASE)
RE_ENDGENERATE_WORD = re.compile(r"\bendgenerate\b", re.IGNORECASE)
RE_END_GENERATE_SPACED = re.compile(r"\bend\s*generate\b", re.IGNORECASE)

# Count occurrences of a literal substring (non-overlapping)
def count_lit(text: str, sub: str) -> int:
    return text.count(sub)

def bracket_imbalance_counts(s: str):
    """
    Returns:
      unmatched_close: dict {"()": n, "[]": n, "{}": n}
      unmatched_open:  dict {"()": n, "[]": n, "{}": n}
      total_unmatched: sum of all unmatched (opens + closes)
    """
    stacks = {o: [] for o in OPENERS}
    unmatched_close = {"()": 0, "[]": 0, "{}": 0}

    for ch in s:
        if ch in OPENERS:
            stacks[ch].append(ch)
        elif ch in CLOSERS:
            opener = MATCH_FOR_CLOSE[ch]
            if stacks[opener]:
                stacks[opener].pop()
            else:
                unmatched_close[BR_PAIR_KEYS[ch]] += 1

    unmatched_open = {"()": len(stacks["("]), "[]": len(stacks["["]), "{}": len(stacks["{"])}
    total_unmatched = sum(unmatched_close.values()) + sum(unmatched_open.values())
    return unmatched_close, unmatched_open, total_unmatched

def main():
    ap = argparse.ArgumentParser(description="Analyze JSONL fields: full_text, ioheader, verilog_code.")
    ap.add_argument("jsonl", help="Path to input .jsonl file")
    args = ap.parse_args()

    keys = ["full_text", "ioheader", "verilog_code"]

    # Aggregate structures
    comment_counts = {k: Counter({"//": 0, "/*": 0, "*/": 0}) for k in keys}
    bracket_entries_with_imbalance = {k: 0 for k in keys}
    bracket_totals_open = {k: Counter({"()": 0, "[]": 0, "{}": 0}) for k in keys}
    bracket_totals_close = {k: Counter({"()": 0, "[]": 0, "{}": 0}) for k in keys}

    # Specific metrics
    total_endmodule_in_ioheader = 0
    ioheader_module_occ_ge2_entries = 0
    ioheader_module_occ_eq2_entries = 0
    total_engenerate_in_ioheader = 0  # literal "engenerate" (as requested)

    endgenerate_without_generate_entries = 0  # in full_text: endgenerate/end generate present, but no standalone generate
    # Helper regex to subtract "end generate"/"endgenerate" when counting standalone generate
    # We’ll remove end-generate forms and then search for remaining "generate".
    def has_endgenerate_but_no_generate(text: str) -> bool:
        t = text or ""
        if not t:
            return False
        has_endgen = bool(RE_ENDGENERATE_WORD.search(t) or RE_END_GENERATE_SPACED.search(t))
        if not has_endgen:
            return False
        # Remove all end-generate tokens, then check for generate
        t_removed = RE_END_GENERATE_SPACED.sub(" ", RE_ENDGENERATE_WORD.sub(" ", t))
        return not bool(RE_GENERATE.search(t_removed))

    verilog_code_empty_or_only_endmodule_entries = 0

    total_objs = 0
    with open(args.jsonl, "r", encoding="utf-8", errors="ignore") as f:
        for ln, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception as e:
                print(f"[WARN] {args.jsonl}:{ln}: bad JSON: {e}", file=sys.stderr)
                continue

            total_objs += 1

            # ---- Per-key common metrics ----
            for k in keys:
                val = obj.get(k, "")
                if not isinstance(val, str):
                    val = "" if val is None else str(val)

                # comment markers
                comment_counts[k]["//"] += count_lit(val, "//")
                comment_counts[k]["/*"] += count_lit(val, "/*")
                comment_counts[k]["*/"] += count_lit(val, "*/")

                # bracket imbalance
                _, _, total_unmatched = bracket_imbalance_counts(val)
                if total_unmatched > 0:
                    bracket_entries_with_imbalance[k] += 1
                # Also track per-bracket totals for more visibility
                uc, uo, _ = bracket_imbalance_counts(val)
                for pair in ["()", "[]", "{}"]:
                    bracket_totals_close[k][pair] += uc[pair]
                    bracket_totals_open[k][pair] += uo[pair]

            # ---- ioheader-specific metrics ----
            io = obj.get("ioheader", "")
            if not isinstance(io, str):
                io = "" if io is None else str(io)

            total_endmodule_in_ioheader += len(RE_ENDMODULE.findall(io))
            module_occ = len(RE_MODULE_WORD.findall(io))
            if module_occ >= 2:
                ioheader_module_occ_ge2_entries += 1
            if module_occ == 2:
                ioheader_module_occ_eq2_entries += 1
            total_engenerate_in_ioheader += io.lower().count("engenerate")

            # ---- full_text: end generate without generate ----
            ft = obj.get("full_text", "")
            if not isinstance(ft, str):
                ft = "" if ft is None else str(ft)
            if has_endgenerate_but_no_generate(ft):
                endgenerate_without_generate_entries += 1

            # ---- verilog_code: only 'endmodule' or empty ----
            vc = obj.get("verilog_code", "")
            if not isinstance(vc, str):
                vc = "" if vc is None else str(vc)
            stripped = vc.strip()
            if stripped == "" or stripped.lower() == "endmodule":
                verilog_code_empty_or_only_endmodule_entries += 1

    # ----- Output -----
    # Print a concise, readable summary
    print("\n=== Summary ===")
    print(f"Total JSONL objects processed: {total_objs}\n")

    for k in keys:
        print(f"[{k}]")
        print(f"  Comment markers:")
        print(f"    '//'  occurrences: {comment_counts[k]['//']}")
        print(f"    '/*'  occurrences: {comment_counts[k]['/*']}")
        print(f"    '*/'  occurrences: {comment_counts[k]['*/']}")
        print(f"  Bracket imbalance:")
        print(f"    Entries with any imbalance: {bracket_entries_with_imbalance[k]}")
        print(f"    Total unmatched OPENS by type:  ()={bracket_totals_open[k]['()']}, []={bracket_totals_open[k]['[]']}, {{}}={bracket_totals_open[k]['{}']}")
        print(f"    Total unmatched CLOSES by type: ()={bracket_totals_close[k]['()']}, []={bracket_totals_close[k]['[]']}, {{}}={bracket_totals_close[k]['{}']}")
        print()

    print("[ioheader specifics]")
    print(f"  Total 'endmodule' occurrences in ioheader: {total_endmodule_in_ioheader}")
    print(f"  Entries where 'module ' occurs >= 2 times in ioheader: {ioheader_module_occ_ge2_entries}")
    print(f"  Entries where 'module ' occurs exactly 2 times in ioheader: {ioheader_module_occ_eq2_entries}")
    print(f"  Total 'engenerate' occurrences in ioheader: {total_engenerate_in_ioheader}\n")

    print("[generate/endgenerate consistency]")
    print("  Entries where (endgenerate/end generate) appears in full_text BUT no standalone 'generate':",
          endgenerate_without_generate_entries, "\n")

    print("[verilog_code minimal content]")
    print("  Entries where verilog_code is empty OR exactly 'endmodule':",
          verilog_code_empty_or_only_endmodule_entries)

if __name__ == "__main__":
    main()
