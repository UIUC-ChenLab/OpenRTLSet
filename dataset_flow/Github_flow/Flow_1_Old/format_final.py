import json

def Count(jsonl_path):
    updated_lines = []
    # Process JSONL file
    i=0
    h=0
    with open(jsonl_path, 'r') as f:
        for line in f:
            obj = json.loads(line)
            if 'Repo_url' not in obj: 
                if 'repo_url' not in obj:
                    i+=1
            if "Repo_url" in obj and (obj['Repo_url']=="" or obj['Repo_url']==" "):
                    h+=1
    print(i)
    print(h)

Count('/work/nvme/bcct/lad2025/outputnn8.jsonl')

##################################


import json

import re

import json
from pathlib import Path
from typing import Dict, Any

def normalize_code(code):
    # 1) Remove all real whitespace (spaces, newlines, tabs, etc.)
    code = re.sub(r"\s+", "", code)
    # 2) Remove literal backslash‑n and backslash‑t sequences
    code = code.replace("\\n", "").replace("\\t", "")
    code = code.strip()
    return code



def update_jsonl_with_license_and_repo(
    jsonl_path: str,
    json_path: str,
    output_path: str,
    normalize_code: callable
) -> None:

    code_lookup: Dict[str, Dict[str, str]] = {}
    with open(json_path, 'r') as meta_f:
        for line in meta_f:
            try:
                record = json.loads(line)
                raw_code = record.get('CODE', '')
                key = normalize_code(raw_code)
                code_lookup[key] = {
                    'Repo_url': record.get('Repo_url', ''),
                    'lic_name': record.get('lic_name', '')
                }
            except json.JSONDecodeError:
                continue  # skip malformed lines
    # with open(json_path, 'r') as meta_f:
    #     json_data = json.load(meta_f)
    #     # try:
    # # # Build a lookup mapping normalized CODE to repo/license
    #     code_lookup = {
    #         normalize_code(item['CODE']): {
    #             'Repo_url': item.get('Repo_url', ''),
    #             'lic_name': item.get('lic_name', '')
    #         }
    #         for item in json_data}
        # except json.JSONDecodeError:
        #         continue  # skip malformed lines

    # 2) Process the JSONL, updating where matches occur
    input_lines = Path(jsonl_path).read_text().splitlines()
    enriched: Dict[str, Any]
    with open(output_path, 'w') as out_f:
        for raw in input_lines:
            try:
                enriched = json.loads(raw)
            except json.JSONDecodeError:
                # preserve original line if invalid JSON
                out_f.write(raw + "\n")
                continue

            # Combine ioheader + verilog_code and normalize
            combined = f"{enriched.get('ioheader', '').strip()}\n{enriched.get('verilog_code', '').strip()}"
            key = normalize_code(combined)

            if key in code_lookup:
                print("h")
                meta = code_lookup[key]
                # Only overwrite if missing or empty
                if not enriched.get('Repo_url') or enriched.get('Repo_url')=="" or enriched.get('Repo_url')==" ":
                    enriched['Repo_url'] = meta['Repo_url']
                if not enriched.get('lic_name') or enriched.get('lic_name') =="" or enriched.get('lic_name') ==" ":
                    enriched['lic_name'] = meta['lic_name']
            # Write enriched record back
            out_f.write(json.dumps(enriched) + "\n")

update_jsonl_with_license_and_repo('/work/nvme/bcct/lad2025/outputn7.jsonl', '/work/nvme/bcct/mjha1/ver_with_repo.jsonl', '/work/nvme/bcct/lad2025/outputnn8.jsonl', normalize_code)



 

