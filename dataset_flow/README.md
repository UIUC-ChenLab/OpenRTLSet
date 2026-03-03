# Dataset Flow: Multi-Flow Automation for Collecting Verilog Modules

This project provides four distinct automation flows to collect, convert, and process hardware design repositories from open-source sources like GitHub. 

---

## 1. GitHub Flow

**Purpose:**  
Automates the collection of Verilog repositories on GitHub.

**Features:**  
- Queries the GitHub API for repositories matching Verilog criteria.  
- Filters and processes the results based on date intervals defined in a configuration file.  
- Modular Python scripts handle querying, filtering, and orchestration of the entire workflow.

**Requirements:**  
- Python environment  
- Configuration file specifying date intervals for repository collection

---

## 2. VHDL Flow

**Purpose:**  
Scrapes VHDL repositories from GitHub, converts VHDL source files into Verilog, and organizes the resulting Verilog modules automatically.

**Features:**  
- Automated repository scraping and download  
- Conversion of VHDL code to Verilog using vhd2vl and custom scripts
- Structured output of Verilog modules for further processing

**Requirements:**  
- Python packages: `nltk`, `GitPython`, `bs4`, `chardet`, `openpyxl`

---

## 3. Verilator Flow

**Purpose:**  
Converts Verilog files into C++ source files using Verilator for providing more context in labeling.

**Features:**  
- Uses the `verilator_flow.py` script to automate Verilator invocation  
- Generates synthesizable and cycle-accurate C++ models from Verilog input  

**Requirements:**  
- Verilator installed and accessible in system PATH  
- Python environment to run the flow script

---

## 4. Vitis Flow

**Purpose:**  
Transforms open-source C and C++ repositories into Verilog code by leveraging Xilinx Vitis High-Level Synthesis (HLS).

**Features:**  
- Clones and processes C/C++ repositories  
- Uses Vitis HLS to synthesize Verilog from high-level C/C++ code  
- Automated handling and structuring of generated Verilog outputs

**Requirements:**  
- Python packages: `bs4`, `GitPython`, `numpy`  
- Xilinx Vitis HLS installed and configured

---

# Getting Started

1. Install the required Python packages for each flow as noted above.  
2. Configure date ranges or repository sources as needed (especially for GitHub and VHDL flows).  
3. Run the respective Python scripts for your flow of interest

---

For detailed instructions and troubleshooting, refer to individual flow documentation within the project.
