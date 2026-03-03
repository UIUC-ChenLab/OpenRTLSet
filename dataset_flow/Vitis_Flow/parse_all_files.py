# import reg_parser
from reg_parser import *
from HLS_flow import *

import os
import json
import requests
import shutil
import subprocess

def collect_tcl_files(repo_path):
    tcl_files = []
    
    # Walk through the repository directory
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.tcl'):
                # Add the full file path to the list
                tcl_files.append(os.path.join(root, file))
    
    return tcl_files

# Function to collect resource metrics (example implementation)
def collect_resource_metrics(repo_path):
    metrics = {}
    # Here you can implement logic to gather metrics from the repository or report files
    # For example, reading a hypothetical report file
    report_file_path = os.path.join(repo_path, 'report.txt')  # Adjust as necessary
    
    if os.path.exists(report_file_path):
        with open(report_file_path, 'r') as report_file:
            for line in report_file:
                if "Resource Usage" in line:
                    metrics['resource_usage'] = line.strip()  # Example line processing
                # Add more conditions here to extract different metrics

    return metrics

def download_repo(repo_url, dest_path):
    os.system(f'git clone {repo_url} {dest_path}')

def save_results(results, output_file):
    # Check if the file already exists
    file_exists = os.path.isfile(output_file)

    # If the file does not exist, initialize it with a JSON array
    # Open the file in append mode
    with open(output_file, 'a') as f:
        # If the file already exists, we need to add a comma to separate JSON objects
        if file_exists:
            f.write(",\n")  # Add a comma and newline before appending new data
        
        # Dump the new results
        json.dump(results, f)

# Call this function at the end to close the JSON array
def finalize_json_file(output_file):
    if os.path.isfile(output_file):
        with open(output_file, 'a') as f:
            f.write("\n]")  # Close the JSON array

def process_repo(repo_name, path, target_path):
    VALID_EXTS = [".h", ".hpp", ".c", ".cpp"]


    REPO_NAME = repo_name

    # Collect c files first
    repo_parse_dict = {}
    d = False
    # Traverse the repo and collect all .c files with their codetexts
    for root, dirs, files in os.walk(os.path.join(path, REPO_NAME)):  # Search in destination path
        for file in files:
            if d:
                break
            if os.path.join(root, file) not in repo_parse_dict and (file.endswith('.c') or file.endswith('.cpp') or file.endswith('.hpp') or file.endswith('.h')):
                try:
                    print(os.path.join(root, file))
                    repo_parse_dict[os.path.join(root, file)] = parse_file(os.path.join(root, file))
                except Exception as e:
                    continue
                    # print(os.path.join(root, file))
                    # print("#############################")
                    # print(e)
                    # print("-------------------------------------------------------------")
                    d = True
                    break

    keys_list = list(repo_parse_dict.keys())

    flag=0
    for each_c_file in keys_list:
        # print(len(repo_parse_dict))
        for each_fn in repo_parse_dict[each_c_file]:
            if flag==1:
                break
            if each_fn.type == 'function':
                try:
                    write_project(each_fn.name, os.path.join(target_path, REPO_NAME) ,os.path.join(path, REPO_NAME),each_fn.filePath,repo_parse_dict)
                except Exception as e:
                    # print(each_fn.name)
                    # print(each_c_file)
                    # print(e)
                    flag=1
                    break

    # Example usage:
    repo_path = os.path.join(target_path, REPO_NAME)  # Replace this with your repo path
    tcl_files = collect_tcl_files(repo_path)

    if len(tcl_files) > 1000:
        return

    # Output the list of .tcl files
    for tcl_file in tcl_files:
        print(tcl_file)

    for root, dirs, files in os.walk(repo_path):
        for fname in files:
            if os.path.splitext(fname)[1] in [".tcl"]:
                if all([f not in os.path.join(os.path.join(root, fname)) for f in [
                    ".autopilot", "/solution/impl/", "/solution/verilog/", "/solution/vhdl/", "/solution/csim/", "/solution/syn/",
                    "/syn/verilog/", "/syn/vhdl/"]]):
                    if "/syn/" not in os.path.join(os.path.join(root, fname)):
                        tcl_files.append(os.path.join(os.path.join(root, fname)))
    print("Total of", len(tcl_files), "tcl_file_paths added.")

    cmd_all_res = []
    success_count = 0
    total_count = 0
    for ftcl in tcl_files:
        _done = False
        for d in os.listdir(os.path.dirname(ftcl)):
            d_path = os.path.join(os.path.dirname(ftcl), d)
            _verilog_path = os.path.join(d_path, "solution/impl/verilog")
            if os.path.isdir(d_path) and os.path.isdir(_verilog_path) and len(os.listdir(_verilog_path))>0:
                print(d_path, "is done, verilog files detected.")
                _done = True
                break
        if _done:
            success_count += 1
            # print("TOTAL SUCCESS MODULE COUNT:", success_count)
            continue
        # print("working on:", ftcl)
        os.chdir(os.path.join(path, REPO_NAME))
        hls_result = run_one_hls_design(ftcl)
        # print(hls_result)
        total_count +=1
        cmd_all_res.append(hls_result)
        if hls_result.returncode != 0:
            print("ERROR")
            pass
        else:
            print("PASS")
            success_count += 1
        print("TOTAL SUCCESS MODULE COUNT:", success_count)
        print("TOTAL COUNT:",total_count)
    
     # Collect resource metrics
    metrics = collect_resource_metrics(repo_path)
    
    return metrics  # Return the collected metrics

# Main function
def main(json_data, path, target_path):
    results = []
    
    for entry in json_data:
        repo_name = entry['name']
        repo_full_name = entry['full_name']
        repo_url = entry['clone_url']  # Use 'clone_url' to download

        # Define paths
        repo_path = os.path.join(path, repo_name)
        
        # Download the repository
        print(f"Downloading {repo_full_name}...")
        download_repo(repo_url, repo_path)

        # Process the downloaded repository
        print(f"Processing {repo_name}...")
        process_result = process_repo(repo_name, path, target_path)

        # Store the results
        results.append({
            'repo_name': repo_name,
            'result': process_result
        })

        # Clean up: delete the repository after processing
        # print(f"Cleaning up {repo_name}...")
        # shutil.rmtree(repo_path, ignore_errors=True)

    # Define the substring to look for
    substring = 'accepted_repositories_'

    # Extract the part after the substring
    if substring in json_input:
        result = json_input.split(substring, 1)[1]  # Split once and get the second part

    # Save all results to a new JSON file
    output_file = os.path.join(target_path, f'results_{result}')
    save_results(results, output_file)
    print(f"Results saved to {output_file}")

# Load your JSON data
folder_name = os.path.abspath(os.path.dirname(__file__)) + '/process_accepted_batch'
for filename in os.listdir(folder_name):
        # Check if filename starts with 'cpp_repositories' or 'c_repositories'
        if filename.startswith("accepted"):
            file_path = os.path.join(folder_name, filename)
            
            # Check if it's a valid JSON file
            if file_path.endswith(".json"):
                json_input = file_path  # Replace with your actual JSON string
                with open(json_input, 'r') as f:
                    json_data = json.load(f)

                # Define paths
                path = folder_name +"/downloaded_repos"
                target_path = folder_name+ '/vitis_folders'

                # Execute main function
                if __name__ == "__main__":
                    main(json_data, path, target_path)
                    