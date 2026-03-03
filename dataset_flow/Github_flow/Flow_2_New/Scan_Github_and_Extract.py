import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
import time
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple
import requests

# -----------------------------
# URL normalization / matching
# -----------------------------
def normalize_repo_url(url: str) -> str:
    u = url.strip()
    if not u:
        return ""
    u = u.replace("git@github.com:", "https://github.com/")
    u = u.replace("git://github.com/", "https://github.com/")
    if u.startswith("http://"):
        u = "https://" + u[len("http://"):]
    u = u.split("#", 1)[0].split("?", 1)[0]
    if u.endswith(".git"):
        u = u[:-4]
    u = u.rstrip("/")
    parts = u.split("/")
    try:
        gi = parts.index("github.com")
    except ValueError:
        if "github.com" in u:
            parts = u.split("/")
            gi = 2 if len(parts) > 2 and parts[2] == "github.com" else None
        else:
            return u.lower()
    if gi is None or gi + 2 >= len(parts):
        return u.lower()
    host = "github.com"
    owner = parts[gi + 1]
    repo = parts[gi + 2]
    return f"https://{host}/{owner.lower()}/{repo.lower()}"

def load_repo_txt(path: str) -> Set[str]:
    canon = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            n = normalize_repo_url(line)
            if n:
                canon.add(n)
    return canon

# -----------------------------
# JSONL helpers
# -----------------------------
def iter_jsonl(path: str) -> Iterator[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[WARN] Skipping bad JSON on line {ln}: {e}", file=sys.stderr)

def write_jsonl(path: str, objs: Iterable[Dict], mode: str = "w") -> None:
    with open(path, mode, encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

# ### NEW: atomic append of a list of JSON objects to a JSONL target.
def atomic_append_jsonl(target: Path, objs: List[Dict]) -> None:
    if not objs:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tf:
        tmp_path = Path(tf.name)
        for o in objs:
            tf.write(json.dumps(o, ensure_ascii=False) + "\n")
    # Append tmp to target atomically
    with open(target, "a", encoding="utf-8") as out_f, open(tmp_path, "r", encoding="utf-8") as in_f:
        shutil.copyfileobj(in_f, out_f)
    try:
        tmp_path.unlink(missing_ok=True)
    except Exception:
        pass

# -----------------------------
# Split JSONL by Repo_url
# -----------------------------
def split_jsonl_by_repo(
    src_jsonl: str,
    repo_txt_set: Set[str],
    match_out: str,
    nonmatch_out: str,
) -> Tuple[List[Dict], List[Dict], List[str]]:
    matches = []
    nonmatches = []
    match_urls = []
    for obj in iter_jsonl(src_jsonl):
        raw = obj.get("Repo_url", "") or obj.get("Repo_url".lower(), "")
        n = normalize_repo_url(str(raw))
        if n and n in repo_txt_set:
            matches.append(obj)
            match_urls.append(n)
        else:
            nonmatches.append(obj)
    write_jsonl(match_out, matches, mode="w")
    write_jsonl(nonmatch_out, nonmatches, mode="w")
    return matches, nonmatches, sorted(set(match_urls))

# -----------------------------
# GitHub ZIP download (with retry)
# -----------------------------
class RateLimitError(Exception):
    pass

def github_zipball_url(repo_url: str) -> str:
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 5:
        raise ValueError(f"Not a canonical GitHub repo URL: {repo_url}")
    owner, repo = parts[-2], parts[-1]
    return f"https://api.github.com/repos/{owner}/{repo}/zipball"

def _check_rate_limit(response: requests.Response):
    if response.status_code in (403, 429):
        raise RateLimitError(f"Rate limited with status {response.status_code}")

def download_repo_zip(repo_url: str, dest_zip: Path, token: Optional[str] = None) -> None:
    url = github_zipball_url(repo_url)
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with requests.get(url, headers=headers, stream=True, timeout=120, allow_redirects=False) as r:
        _check_rate_limit(r)
        if r.status_code in (301, 302, 303, 307, 308):
            redirect_url = r.headers.get("Location")
            if not redirect_url:
                r.raise_for_status()
            # keep the same headers so auth persists
            with requests.get(redirect_url, headers=headers, stream=True, timeout=120) as rr:
                _check_rate_limit(rr)
                rr.raise_for_status()
                with open(dest_zip, "wb") as f:
                    for chunk in rr.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
            return
        r.raise_for_status()
        with open(dest_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)


def download_with_retry(repo_url: str, dest_zip: Path, token: Optional[str], max_tries: int = 3, sleep_seconds: int = 60) -> bool:
    attempt = 1
    while attempt <= max_tries:
        try:
            download_repo_zip(repo_url, dest_zip, token)
            return True
        except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
            print(f"[WARN] Timeout downloading {repo_url} (attempt {attempt}/{max_tries}): {e}", file=sys.stderr)
            if attempt < max_tries:
                print(f"[INFO] Sleeping {sleep_seconds}s due to timeout before retry...", file=sys.stderr)
                time.sleep(sleep_seconds)
            attempt += 1
        except RateLimitError as e:
            print(f"[WARN] {e} for {repo_url} (attempt {attempt}/{max_tries})", file=sys.stderr)
            if attempt < max_tries:
                print(f"[INFO] Sleeping {sleep_seconds}s due to rate limit before retry...", file=sys.stderr)
                time.sleep(sleep_seconds)
            attempt += 1
        except requests.exceptions.ConnectionError as e:
            print(f"[WARN] Connection error for {repo_url} (attempt {attempt}/{max_tries}): {e}", file=sys.stderr)
            if attempt < max_tries:
                print(f"[INFO] Sleeping {sleep_seconds}s before retry...", file=sys.stderr)
                time.sleep(sleep_seconds)
            attempt += 1
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status in (403, 429) and attempt < max_tries:
                print(f"[WARN] HTTP {status} for {repo_url} (attempt {attempt}/{max_tries}); sleeping {sleep_seconds}s then retrying...", file=sys.stderr)
                time.sleep(sleep_seconds)
                attempt += 1
            else:
                print(f"[WARN] HTTP error for {repo_url}: {e}", file=sys.stderr)
                return False
        except Exception as e:
            print(f"[WARN] Unexpected error downloading {repo_url}: {e}", file=sys.stderr)
            return False
    return False

# -----------------------------
# License detection
# -----------------------------
LICENSE_FILENAMES = {
    "LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt", "COPYING.md",
    "LICENCE", "LICENCE.txt", "LICENCE.md"
}
def guess_lic_name(repo_root: Path) -> str:
    candidates = []
    top = repo_root
    entries = list(repo_root.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        top = entries[0]
    for p in top.iterdir():
        if p.is_file() and p.name.upper() in {s.upper() for s in LICENSE_FILENAMES}:
            candidates.append(p)
    if not candidates:
        for p in top.rglob("*"):
            if p.is_file() and p.name.upper() in {s.upper() for s in LICENSE_FILENAMES}:
                candidates.append(p)
                break
    if not candidates:
        return "Unknown"

    try:
        text = candidates[0].read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return candidates[0].name

    t = text.lower()
    if "mit license" in t or "permission is hereby granted" in t:
        return "MIT"
    if "apache license" in t and "version 2.0" in t:
        return "Apache-2.0"
    if "gnu general public license" in t and "version 3" in t:
        return "GPL-3.0"
    if "gnu general public license" in t and "version 2" in t:
        return "GPL-2.0"
    if "bsd license" in t or "redistribution and use in source and binary forms" in t:
        return "BSD"
    if "mozilla public license" in t:
        return "MPL"
    if "unlicense" in t:
        return "Unlicense"
    if "lgpl" in t or "lesser general public license" in t:
        return "LGPL"
    return candidates[0].name

# -----------------------------
# Verilog helpers
# -----------------------------
import re 
pattern = re.compile(
        r'//.*?$|/\*.*?\*/',
        re.DOTALL | re.MULTILINE
    )

def strip_comments(code: str) -> str:
    code = re.sub(pattern, "", code)
    return code

MODULE_RE = re.compile(r"\bmodule\b", flags=re.IGNORECASE)
ENDMODULE_RE = re.compile(r"\bendmodule\b", flags=re.IGNORECASE)

def find_modules(verilog_text: str):
    """
    Extract modules from comment-stripped Verilog text using a conservative rule:
    - Start at a literal "module " token (word boundary).
    - The module ends at the first "endmodule" *unless* another "module " occurs before that,
      in which case that later "module " becomes the new starting point.
    - If no matching "endmodule" is found for a start, we skip that incomplete chunk
      (i.e., we DO NOT merge to EOF). This avoids accidental concatenation.
    Returns: list of (start_idx, end_idx, text) for each detected module.
    """
    # We assume comments are already stripped upstream. If not, caller should strip first.
    mod_tok = re.compile(r'\bmodule \b', re.MULTILINE)
    end_tok = re.compile(r'\bendmodule\b', re.MULTILINE)

    modules = []
    i = 0
    n = len(verilog_text)

    while True:
        m = mod_tok.search(verilog_text, i)
        if not m:
            break
        start = m.start()

        # Seek a matching end considering possible nested stray "module " tokens.
        search_from = m.end()
        while True:
            next_end = end_tok.search(verilog_text, search_from)
            next_mod = mod_tok.search(verilog_text, search_from)

            if next_mod and (not next_end or next_mod.start() < next_end.start()):
                # Found another "module " before an "endmodule" -> restart the start here.
                start = next_mod.start()
                search_from = next_mod.end()
                continue

            if next_end:
                # Properly closed module.
                end = next_end.end()
                modules.append((start, end, verilog_text[start:end]))
                i = end  # continue scanning after this module
                break

            # No endmodule ahead. Fallback: skip this start.
            # If there is another "module " later, continue from there; otherwise, we're done.
            if next_mod:
                i = next_mod.start()
            else:
                i = n
            break

    return modules

def split_statements_semicolon(text: str) -> List[str]:
    parts = []
    buf = []
    for ch in text:
        buf.append(ch)
        if ch == ";":
            parts.append("".join(buf))
            buf = []
    if buf:
        parts.append("".join(buf))
    return parts

def move_port_decls_to_header(ioheader: str, body: str) -> Tuple[str, str]:
    stmts = split_statements_semicolon(body)
    kept = []
    moved = []
    for s in stmts:
        st = s.strip()
        if not st:
            continue
        if DECL_START_RE.match(st) and not HAS_ASSIGN_EQ_RE.search(st):
            moved.append(st if st.endswith(";") else st + ";")
        else:
            kept.append(s)
    if moved:
        ioheader2 = ioheader + ("\n" if not ioheader.endswith("\n") else "")
        ioheader2 += "\n".join(moved)
    else:
        ioheader2 = ioheader
    new_body = "".join(kept).strip()
    return ioheader2, new_body

def clean_whitespace(s: str) -> str:
    return re.sub(r"[ \t]+\n", "\n", s).strip()

# -----------------------------
# Repo processing
# -----------------------------
def extract_verilog_modules_from_repo_zip(zip_path: Path, repo_url: str) -> List[Dict]:
    out = []
    with zipfile.ZipFile(zip_path) as z:
        with tempfile.TemporaryDirectory() as tdir:
            z.extractall(tdir)
            repo_root = Path(tdir)
            lic_name = guess_lic_name(repo_root)

            for info in z.infolist():
                name = info.filename
                if not (name.lower().endswith(".v") or name.lower().endswith(".sv")):
                    continue
                try:
                    with z.open(info, "r") as f:
                        raw_bytes = f.read()
                except Exception:
                    continue
                try:
                    text = raw_bytes.decode("utf-8", errors="ignore")
                except Exception:
                    continue

                no_comments = strip_comments(text)
                print(no_comments)
                modules = find_modules(no_comments)
                for mod in modules:
                    ioheader, body = split_ioheader_and_body(mod)
                    ioheader2, body2 = move_port_decls_to_header(ioheader, body)
                    ioheader2 = clean_whitespace(ioheader2)
                    body2 = clean_whitespace(body2)
                    out.append({
                        "ioheader": ioheader2,
                        "verilog_code": body2,
                        "Repo_url": repo_url,
                        "lic_name": lic_name,
                        "conversation": "",
                        "full_text": mod,
                    })
    return out

# -----------------------------
# ### NEW: checkpoint helpers
# -----------------------------
def repo_id(owner_repo_url: str) -> str:
    # github.com/owner/repo -> owner__repo
    parts = owner_repo_url.rstrip("/").split("/")
    return f"{parts[-2]}__{parts[-1]}"

def load_done_set(done_list_path: Path) -> Set[str]:
    if not done_list_path.exists():
        return set()
    with open(done_list_path, "r", encoding="utf-8") as f:
        return {normalize_repo_url(line.strip()) for line in f if line.strip()}

def append_done(done_list_path: Path, url: str) -> None:
    done_list_path.parent.mkdir(parents=True, exist_ok=True)
    with open(done_list_path, "a", encoding="utf-8") as f:
        f.write(normalize_repo_url(url) + "\n")

# -----------------------------
# Main orchestrator
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="Process JSONL by GitHub repos, download, extract Verilog modules, and output ioheader/verilog_code JSONL with checkpointing.")
    ap.add_argument("--repo_txt", default="/mnt/shared/gpfs/escad_verilog_dataset/RERUN/matched_repo_urls.txt")
    ap.add_argument("--src_jsonl", default="/mnt/shared/gpfs/escad_verilog_dataset/RERUN/Merge_July_28_FIN_hierarchy_new_index.jsonl")
    ap.add_argument("--match_jsonl", default="/mnt/shared/gpfs/escad_verilog_dataset/RERUN/match_jsonl_rerun.jsonl")
    ap.add_argument("--nonmatch_jsonl", default="/mnt/shared/gpfs/escad_verilog_dataset/RERUN/nonmatch_jsonl_rerun.jsonl")
    ap.add_argument("--modules_jsonl", default="/mnt/shared/gpfs/escad_verilog_dataset/RERUN/modules_jsonl_rerun.jsonl")
    ap.add_argument("--modules_dir", default="/mnt/shared/gpfs/escad_verilog_dataset/RERUN/modules_by_repo3", help="Optional per-repo JSONLs for debugging/resume")
    ap.add_argument("--cache_dir", default="/mnt/shared/gpfs/escad_verilog_dataset/RERUN/.cache_repo_zips_new2")
    ap.add_argument("--force_download", action="store_true")
    ap.add_argument("--max_download_retries", type=int, default=5)
    ap.add_argument("--retry_sleep_seconds", type=int, default=60)
    ap.add_argument("--done_list", default="/mnt/shared/gpfs/escad_verilog_dataset/RERUN/newremaining.txt", help="Checkpoint list of finished repos")
    ap.add_argument("--redo_failed_only", action="store_true", help="If set, only process repos not in done_list (default behavior). If unset and you delete per-repo file, it will recompute that repo.")
    args = ap.parse_args()

    repo_set = load_repo_txt(args.repo_txt)
    if not repo_set:
        print("[ERROR] No valid GitHub repos found in repo_txt.", file=sys.stderr)
        sys.exit(1)

    matches, _, match_urls = split_jsonl_by_repo(
        args.src_jsonl, repo_set, args.match_jsonl, args.nonmatch_jsonl
    )
    print(f"[INFO] Matching entries written: {len(matches)}")
    print(f"[INFO] Unique matching repos: {len(match_urls)}")

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    modules_dir = Path(args.modules_dir)
    modules_dir.mkdir(parents=True, exist_ok=True)
    modules_jsonl_path = Path(args.modules_jsonl)
    done_list_path = Path(args.done_list)
    done_set = load_done_set(done_list_path)
    token = "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"

    # ### NEW: Resume — skip repos alread existing per-repo file and not empty
    to_process = []
    for repo_url in match_urls:
        nurl = normalize_repo_url(repo_url)
        per_repo_file = modules_dir / f"{repo_id(nurl)}.jsonl"
        per_repo2 = Path("/mnt/shared/gpfs/escad_verilog_dataset/RERUN/modules_by_repo3")
        per_repo_file2 = per_repo2 / f"{repo_id(nurl)}.jsonl"
        if nurl in done_set:
            print(f"[RESUME] Skipping already-done {nurl}")
            continue
        if per_repo_file.exists():
            # Consider it completed; add to done for idempotence
            print(f"[RESUME] Per-repo file exists; marking done: {nurl}")
            append_done(done_list_path, nurl)
            done_set.add(nurl)
            continue
        if per_repo_file2.exists():
             per_repo_file2.unlink()
        to_process.append(nurl)

    print(f"[INFO] Repos to process this run: {len(to_process)}")

    processed_count = 0
    for repo_url in to_process:
        zip_name = normalize_repo_url(repo_url).rstrip("/").split("/")[-2] + "_" + normalize_repo_url(repo_url).split("/")[-1] + ".zip"
        zip_path = cache_dir / zip_name

        if args.force_download or not zip_path.exists():
            print(f"[INFO] Downloading {repo_url} ...")
            ok = download_with_retry(
                repo_url, zip_path, token,
                max_tries=args.max_download_retries,
                sleep_seconds=args.retry_sleep_seconds
            )
            if not ok:
                print(f"[WARN] Skipping {repo_url} after retries.", file=sys.stderr)
                continue
        else:
            print(f"[INFO] Using cached ZIP for {repo_url}")

        # Extract modules
        try:
            mod_objs = extract_verilog_modules_from_repo_zip(zip_path, repo_url)
            print(f"[INFO] {repo_url}: extracted {len(mod_objs)} module(s)")
        except zipfile.BadZipFile:
            print(f"[WARN] Bad ZIP for {repo_url}", file=sys.stderr)
            mod_objs = []
        except Exception as e:
            print(f"[WARN] Failed to extract modules for {repo_url}: {e}", file=sys.stderr)
            mod_objs = []

        # ### NEW: Write per-repo JSONL first (temp → move), then atomically append to global, then mark done
        per_repo_path = modules_dir / f"{repo_id(repo_url)}.jsonl"
        tmp_dir = per_repo_path.parent
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_repo_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", delete=False, encoding="utf-8",
                dir=tmp_dir, prefix=per_repo_path.name + ".", suffix=".tmp"
            ) as tf:
                tmp_repo_path = Path(tf.name)
                for o in mod_objs:
                    tf.write(json.dumps(o, ensure_ascii=False) + "\n")
                tf.flush()
                os.fsync(tf.fileno())  # ensure contents hit disk

            # Atomic swap on the *same* filesystem
            os.replace(tmp_repo_path, per_repo_path)

        except Exception as e:
            print(f"[WARN] Could not write per-repo file for {repo_url}: {e}", file=sys.stderr)
            if tmp_repo_path and tmp_repo_path.exists():
                try:
                    tmp_repo_path.unlink()
                except Exception:
                    pass
    # you can `continue` here if you don't want to append globally when per-repo fails


        # Mark repo as done ONLY after successful append to global JSONL
        append_done(done_list_path, repo_url)
        done_set.add(repo_url)
        processed_count += 1

        # ### NEW: small heartbeat to reduce work loss if killed mid-loop
        if processed_count % 10 == 0:
            print(f"[HEARTBEAT] Processed {processed_count} repos this run…")

    print(f"[INFO] Wrote modules JSONL (appended): {args.modules_jsonl}")
    print(f"[INFO] Finished this run. Newly processed repos: {processed_count}")

if __name__ == "__main__":
    main()


