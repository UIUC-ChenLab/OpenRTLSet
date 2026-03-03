#!/usr/bin/env python3
import os, sys, time, argparse, datetime as dt
import requests

API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "repo-scan-verilog-systemverilog"
}

def guarded_get(url, params, token, max_retries=6):
    h = dict(HEADERS)
    if token:
        h["Authorization"] = f"Bearer {token}"
    for attempt in range(max_retries):
        r = requests.get(url, headers=h, params=params, timeout=30)
        # Handle rate limiting gracefully
        if r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
            reset = int(r.headers.get("X-RateLimit-Reset", "0"))
            sleep_s = max(1, reset - int(time.time()) + 2)
            print(f"[rate-limit] sleeping {sleep_s}s…", file=sys.stderr)
            time.sleep(sleep_s)
            continue
        if 500 <= r.status_code < 600:
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code != 200:
            raise RuntimeError(f"GitHub error {r.status_code}: {r.text[:200]}")
        return r
    raise RuntimeError("Exceeded retries to GitHub.")

def search_repos_once(created_start, created_end, language, page=1, per_page=100, token=None, sort="stars", order="desc"):
    """One Search API call for a single language and date window."""
    q = f"created:{created_start}..{created_end} language:{language}"
    url = f"{API}/search/repositories"
    r = guarded_get(url, {
        "q": q, "per_page": per_page, "page": page, "sort": sort, "order": order
    }, token)
    return r.json()

def window_total_count(created_start, created_end, language, token):
    data = search_repos_once(created_start, created_end, language, page=1, per_page=1, token=token)
    return int(data.get("total_count", 0))

def iso_date(d):
    return d.strftime("%Y-%m-%d")

def split_until_under_limit(start_date, end_date, languages, token, limit=950):
    s = iso_date(start_date)
    e = iso_date(end_date)
    counts = {lang: window_total_count(s, e, lang, token) for lang in languages}
    if all(c <= limit for c in counts.values()):
        yield (s, e, counts)
        return

    # Split the window in half using pure date arithmetic
    delta = end_date - start_date
    if delta.days <= 1:
        # fallback: single-day windows (or empty) – just yield to avoid infinite recursion
        yield (s, e, counts)
        return

    mid = start_date + dt.timedelta(days=delta.days // 2)

    # Recurse on [start, mid] and [mid+1, end] to avoid overlapping days
    left_end = mid
    right_start = mid + dt.timedelta(days=1)

    yield from split_until_under_limit(start_date, left_end, languages, token, limit)
    yield from split_until_under_limit(right_start, end_date, languages, token, limit)
def iter_search(created_start, created_end, languages, token):
    """
    Iterate over all windows & pages; merge both languages; dedupe by repo id.
    """
    seen = set()
    for (s, e, counts) in split_until_under_limit(created_start, created_end, languages, token):
        for lang in languages:
            page = 1
            while True:
                data = search_repos_once(s, e, lang, page=page, per_page=100, token=token)
                items = data.get("items", [])
                if not items:
                    break
                for it in items:
                    rid = it["id"]
                    if rid in seen:
                        continue
                    seen.add(rid)
                    yield {
                        "id": rid,
                        "full_name": it.get("full_name"),
                        "html_url": it.get("html_url"),
                        "created_at": it.get("created_at"),
                        "updated_at": it.get("updated_at"),
                        "pushed_at": it.get("pushed_at"),
                        "language": it.get("language"),
                        "stargazers_count": it.get("stargazers_count"),
                        "forks_count": it.get("forks_count"),
                        "open_issues_count": it.get("open_issues_count"),
                        "description": it.get("description"),
                        "owner_login": (it.get("owner") or {}).get("login"),
                        "license": (it.get("license") or {}).get("spdx_id"),
                    }
                page += 1
                # Safety: stop if we've clearly hit the 1000 cap (though we split windows to avoid it)
                if page > 10:  # 10 * 100 = 1000
                    break

def main():
    ap = argparse.ArgumentParser(description="List GitHub repos created after a date with language Verilog or SystemVerilog.")
    ap.add_argument("--since", default="2025-01-01", help="Start date (YYYY-MM-DD), inclusive. Default: 2025-01-01")
    ap.add_argument("--until", default=None, help="End date (YYYY-MM-DD), inclusive. Default: today")
    ap.add_argument("--out", default="new_repos.jsonl", help="Output path (.jsonl). Use '-' for stdout.")
    ap.add_argument("--token", default="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", help="GitHub token (env GITHUB_TOKEN used by default).")
    args = ap.parse_args()

    if not args.token:
        print("ERROR: Please set GITHUB_TOKEN or pass --token.", file=sys.stderr)
        sys.exit(1)

    start_date = dt.date.fromisoformat(args.since)
    end_date = dt.date.fromisoformat(args.until) if args.until else dt.date.today()

    languages = ["Verilog", "SystemVerilog"]

    out = sys.stdout if args.out == "-" else open(args.out, "w", encoding="utf-8")
    try:
        for repo in iter_search(start_date, end_date, languages, args.token):
            # Write JSONL
            import json
            out.write(json.dumps(repo, ensure_ascii=False) + "\n")
        if out is not sys.stdout:
            print(f"Wrote JSONL to {args.out}", file=sys.stderr)
    finally:
        if out is not sys.stdout:
            out.close()

if __name__ == "__main__":
    main()
