# Verilator Flow

The `verilator_flow.py` script is used to generate C++ files from Verilog files using Verilator.

## Steps to Use

1. **Install Verilator**  
   Make sure Verilator is installed in your local environment. If it's not installed, you can download and install it by following the instructions here:  
   [https://verilator.org/guide/latest/install.html](https://verilator.org/guide/latest/install.html)

2. **Set Verilog File Path**  
   In the `main` function of `verilator_flow.py`, change the value of `folder_path` to the **absolute path** of the folder containing your Verilog files.

3. **Run the Script**  
   Execute the script by running the following command:  
   ```bash
   python verilator_flow.py
   ```
