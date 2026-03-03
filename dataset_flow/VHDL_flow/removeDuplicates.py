import json

def remove_duplicates_by_code(input_file, output_file):
    seen_codes = set()
    unique_entries = []

    # Read JSONL file line-by-line
    with open(input_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            try:
                entry = json.loads(line)
                code = entry.get("code", "").strip()
                if code not in seen_codes:
                    seen_codes.add(code)
                    unique_entries.append(entry)
            except json.JSONDecodeError:
                continue  # skip invalid lines

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for entry in unique_entries:
            json.dump(entry, outfile)
            outfile.write('\n')

remove_duplicates_by_code('output_modules.jsonl', 'output_deduplicated.jsonl')
