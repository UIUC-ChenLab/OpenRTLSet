import os
import json

# Define the paths to your folders
folder_1 = ''  # Folder containing JSON files
folder_2 = ''  # Folder containing the Verilog/CPP files

# Function to extract file content
def extract_file_content(file_path):
    with open(file_path, 'r') as f:
        return f.read()

# Function to process each JSON file in folder_1
def process_json_files():
    # Open the output file in write mode
    with open('output_batch.jsonl', 'w') as output_file:
        # Iterate through all JSON files in folder_1
        for json_file in os.listdir(folder_1):
            if json_file.endswith('.json'):
                with open(os.path.join(folder_1, json_file), 'r') as f:
                    repo_data_list = json.load(f)  # This is a list of repositories

                # Iterate through all entries in the JSON file (repo entries)
                for repo_data in repo_data_list:
                    repo_name = repo_data.get('name')
                    repo_html_url = repo_data.get('html_url')

                    # Extract license information (if available)
                    license_info = repo_data.get("license", {})
                    license_name = license_info.get("name", "No License")

                    # Check if the folder with the same name exists in folder_2
                    repo_folder = os.path.join(folder_2, repo_name)
                    # repo_folder = os.path.join(folder_2, repo_name)

                    if os.path.isdir(repo_folder):
                        # Search for Verilog and corresponding CPP files in the repo folder
                        for root, dirs, files in os.walk(repo_folder):
                            for file in files:
                                if file.endswith('.v'):
                                    verilog_code = extract_file_content(os.path.join(root, file))
                                    
                                    # Check if a corresponding CPP file exists with the same name
                                    cpp_file_path = os.path.join(root, file.replace('.v', '.cpp'))
                                    cpp_code = extract_file_content(cpp_file_path) if os.path.isfile(cpp_file_path) else None

                                    # Construct and write the JSON object immediately
                                    json_line = {
                                        "code": verilog_code,
                                        "cpp_code": cpp_code,
                                        "repo_name": repo_name,
                                        "repo_url": repo_html_url,
                                        "license": {
                                            "name": license_name,
                                        }
                                    }
                                    output_file.write(json.dumps(json_line) + "\n")

# Run the processing function
process_json_files()