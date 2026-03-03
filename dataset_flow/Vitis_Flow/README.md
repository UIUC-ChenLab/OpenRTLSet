# Vitis Flow

The goal of this flow is to convert **open-source C and C++ repositories** into **Verilog code** using **Xilinx Vitis HLS**. Ensure that the packages bs4, GitPython and numpy are installed.

---

## Workflow Overview

### Step 1: Collect Repositories
Run `get_Repos.py` to collect metadata for repositories containing `.c` and `.cpp` files.

> **Note:**  
> Include your GitHub `personal_access_token` in `get_Repos.py` to avoid rate limits.

---

### Step 2: Filter by License
Run `get_accepted_license.py` to filter repositories based on open-source licenses.

Only repositories with the following license keys will be accepted:

- `mit`
- `gpl-2.0`
- `gpl-3.0`
- `apache-2.0`
- `bsd-2-clause`
- `bsd-3-clause`

This will create a folder called 'process_accepted_batch' of JSON files containing only the accepted repositories. If the directory is not current change metadata_dir.

---

### Step 3: Set Vitis HLS Path
Update the `vitis_path` variable inside `HLS_flow.py` to the **path where Vitis HLS is installed** on your system.

---

### Step 4: Generate Verilog Files
Run `parse_all_files.py` by providing the folder of accepted repositories as input.

This script:
- Uses functions from `reg_parser.py` and `HLS_flow.py`
- Creates necessary `.tcl` scripts
- Generates Verilog code using Vitis HLS

> Output will be saved in a folder called `Vitis_folders`, where:
> - Each subfolder is named after a repository.
> - Verilog output is stored under a `solution` folder.

>  **Note:**  
> Not all C/C++ files will be successfully converted due to:
> - Invalid headers  
> - Complex dependencies  
> - Non-HLS-compatible constructs  

---

### Step 5: Extract Verilog Metadata
Finally, run `final_json.py` by setting `folder_1` and `folder_2` to the relevant input and output directories.

This will produce a `.jsonl` file containing metadata and structure of the generated Verilog modules.

---

