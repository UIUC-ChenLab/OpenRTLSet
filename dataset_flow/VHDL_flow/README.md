# Generating Verilog Code from VHDL Code

This guide outlines the overall workflow to **scrape VHDL repositories from GitHub**, **convert VHDL to Verilog**, and **structure the Verilog modules** using automated scripts.
Ensure the following python packages are installed nltk, GitPython, bs4, chardet and openpyxl.

---

## Workflow Instructions
Before starting ensure you follow the instructions to the converter https://github.com/ldoolitt/vhd2vl to setup the converter.

### Step 1: Scrape VHDL Repositories
Run the script:

```bash
python GithubAPI_VHDL.py
```

- This script scrapes GitHub for repositories containing `.vhd` files.
- Specify date ranges using the function calls at the bottom of the file.
- Output will be stored as JSON files containing metadata for each VHDL repo.
Note: Please add your personal access token before running script

---

### Step 2: Extract Executable Repos to Excel
Use the `create_executable_Repo` function from `Utility.py` to parse the JSON files and output an Excel sheet of usable repositories.
Note: Please put the folder name the excel file should be downloaded into

---

### Step 3: Download Repositories
Use the Excel file as input and run:

```bash
python gitDownloadFiles.py
```

- This script clones or downloads the repositories listed in the Excel into a local folder of only the approporiate licensed repos.

---

### Step 4: Convert VHDL (.vhd) to Verilog (.v)
Run the script:

```bash
python convertVHDL.py
```

- This finds all `.vhd` files in the downloaded repos.
Note: Please set the repoPath variable where all the repositiory files are. If you run it multiple times delete previous version before running new one.

---
Then run:

``` bash
bash script2.sh
```
- It uses a VHDL-to-Verilog converter and auto-generates a bash script to perform the conversion.
- The converted `.v` (Verilog) files are stored within the respective repo directories.


### Step 5: Postprocess Modules
Use functions in `formattingModules.py` to:

- Check duplicate files 
- Separate I/O headers
- Prepare files for downstream JSONL or dataset generation

Run the file to generate the output jsonl, there is also a commented out function call for checking if all modules are unique 'checkVerilogUnique()'. It creates matching_modules.json and matching_modules.txt.  Set the variable github_scrape_folder before running the file. 

After this run:

``` bash
python removeDuplicates.py 
```
To remove duplicates from this jsonl and this creates a final jsonl file.

---
Remember to change some of the file paths to local file paths on the machine and to add your github token
