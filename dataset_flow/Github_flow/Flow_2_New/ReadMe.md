# OpenRTLSet – Flow_2_New

## Overview

`Flow_2_New` is a processing pipeline of **OpenRTLSet**.  
It performs:

1. GitHub repository discovery  
2. Repository downloading & license extraction  
3. Verilog module extraction  
4. JSONL construction  
5. Structural hierarchy construction  
6. Cleaning & deduplication  
7. Bracket and syntax validation  
8. Verilator-based lint verification    

This flow converts raw GitHub repositories into a **clean, hierarchical, verified Verilog dataset** in JSONL format.

---
# Scripts Description

## 1. Scan_Github.py  

### Purpose
Search GitHub repositories by: Creation date range; Language (Verilog/SystemVerilog); Pagination beyond 1000 repo API limit (recursive date splitting)

### Key Features
- Handles GitHub rate limits
- Recursively splits date windows
- Deduplicates repos by ID
- Outputs metadata JSONL

### Usage
```bash
python Scan_Github.py --start-date 2020-01-01 --end-date 2023-01-01
````

---

## 2️. Scan_Github_and_Extract.py

### Purpose

Download repositories as ZIP; Extract Verilog files; Detect licenses; Strip comments; and Extract `module ... endmodule` blocks

### Key Features

* Retry logic for GitHub API
* License detection (MIT, GPL, Apache, BSD, etc.)
* Verilog module parser
* Comment stripping

### Output

JSONL entries containing: `index`; `Repo_url`; `ioheader`; `verilog_code`; and `lic_name`

---

## 3️. Remove_comments_Merge_duplicates.py

### Purpose

Remove Verilog comments; Merge duplicate modules; Deduplicate by `(Repo_url, normalized full_text)`

### Features

* Aggressive whitespace normalization
* Keeps first occurrence
* Merges missing metadata fields

---

## 4️. Edit_Recreate_Keys.py

### Purpose

Reconstruct: `ioheader` and `verilog_code` from `full_text`.

### Logic

* Splits module into: Header; Input/output declarations; and Body
* Fixes malformed parentheses
* Cleans stray tokens

This script repairs improperly split modules.

---

## 5️. Filter_and_Edit_postverification.py

### Purpose

Post-verification dataset cleanup:

Removes: Entries with verified logs + no parents; `ioheader` containing `endmodule`; Bracket-imbalanced modules; and Incomplete hierarchy nodes

### Deduplication Rules

* Removes duplicates without dependencies
* Merges dependency-aware duplicates by Repo_url

---

## 6️. Hierarchy_Final.py

### Purpose

Construct module hierarchy graph by adding `parents` and `children`

### How

* Detects module definitions
* Detects instantiations
* Matches within same normalized repo
* Avoids primitives & keywords

Result: Directed dependency graph.

---

## 7️. Count_All_Errors_1.py

### Purpose

Global dataset diagnostics. It Counts: Comment tokens (`//`, `/*`, `*/`); Bracket imbalance; `endmodule` in `ioheader`; `generate` misuse; Empty `verilog_code`.
Used for debugging.

---

## 8️. Verify_Final.py

### Purpose

Run Verilator lint verification.

### Process

For each index:

* Write temporary `.sv`
* Include all transitive children
* Run Verilator
* Write `<index>.log` on failure

Parallelized using ThreadPoolExecutor.

### Result

* Pass
* Fail (log generated)
* Skipped (already verified)

---

## 9️. Util_Dataset.py

### Utilities

Contains:

* Overlap counting
* Repo partitioning
* Adding `full_text`
* Bracket balance checks
* Unknown license counting
* Statistical reporting

Supports dataset auditing.

---

# Data Format

Sample JSONL entry:

```json
{
  "index": 12345,
  "Repo_url": "https://github.com/user/repo",
  "ioheader": "module example(input clk);",
  "verilog_code": "...",
  "full_text": "...",
  "parents": [123],
  "children": [456, 789],
  "lic_name": "MIT"
}
```

---

# Verification Strategy

- Structural checks
-  Bracket balance
-  Comment removal
-  Duplicate merging
-  Hierarchy validation
-  Verilator lint
Only verified entries are retained in final dataset.

---
