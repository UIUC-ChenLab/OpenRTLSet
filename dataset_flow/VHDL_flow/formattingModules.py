import re
import os
import json
import nltk 
from nltk.tokenize import word_tokenize
import chardet
import pandas as pd
import shutil
from collections import Counter

github_scrape_folder = ''  # Adjust this path

# Function to clean the Verilog file (remove blank lines and comments)
def formatData(fileName):
    with open(fileName, 'r', encoding='latin-1') as file:
        text = file.read()
    no_blank = [line for line in text.splitlines() if line.strip()]
    no_blank_no_comment = []
    for line in no_blank:
        if '//' in line:
            no_blank_no_comment.append(line[:line.find('//')])
        else:
            no_blank_no_comment.append(line)
    no_blank_no_comment = [line for line in no_blank_no_comment if line.strip()]
    newText = "\n".join(no_blank_no_comment)

    with open(fileName, 'w', encoding='latin-1') as file:
        file.write(newText)


def separate_io_header(verilog_code):
    # Regular expression to match the module header
    module_header_regex = re.compile(r'(module\s+\w+\s*\([^;]*?\))', re.DOTALL)
    
    # Find the module header
    header_match = module_header_regex.search(verilog_code)
    
    if header_match:
        io_header = header_match.group(1)
        rest_of_module = verilog_code[header_match.end()+1:].strip()
        return io_header, rest_of_module
    else:
        return None, verilog_code 


def checkVerilogUnique():
    directory_path = github_scrape_folder   # Replace with the path to your folder

    output_file_path = 'matching_modules.txt'

    output_file_json = 'matching_modules.json'

    # Regular expression pattern to match Verilog module declarations
    module_pattern = r'\bmodule\s+([a-zA-Z_]\w*)'

        # Function to extract the module name and the content after the header
    def get_module_info(content):
        # Find the module header (including module name)
        match = re.search(module_pattern, content, flags=re.DOTALL)
        
        if match:
            # Extract the module name
            module_name = match.group(1)
            # Remove the header to get the remaining content (the body)
            body = re.sub(module_pattern, '', content, flags=re.DOTALL)
            body = re.sub(r'\s+', '', body)
            return module_name, body.strip()
        return None, None

    # Dictionary to store the content (excluding header) by module name
    module_bodies = {}

    matching_modules = {}

    # Iterate through all Verilog files in the directory and compare content after the module header
    for root, dirs, files in os.walk(github_scrape_folder):
        for file in files:
            if file.endswith('.v'):
        # Check if the file is a Verilog file
                file_path = os.path.join(root, file)
            
                # Read the file content
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                    # Extract the module name and content after the header
                    module_name, verilog_body = get_module_info(content)
                    
                    # If a valid module is found, store the module body for comparison
                    if module_name:
                        if verilog_body in module_bodies.values():
                            # Find the module name that has the same body
                            for name, body in module_bodies.items():
                                if body == verilog_body:
                                    if name not in matching_modules:
                                        matching_modules[name] = []
                                    matching_modules[name].append(module_name)
                        module_bodies[module_name] = verilog_body

    # Write the matching module names to a file
    with open(output_file_path, 'w') as output_file:
        if matching_modules:
            for module_name, similar_modules in matching_modules.items():
                for similar_module in similar_modules:
                    output_file.write(f"Module '{module_name}' has the same content as '{similar_module}'\n")
            print(f"Matching modules have been written to {output_file_path}.")
        else:
            output_file.write("No modules with identical content found.\n")
            print(f"No modules with identical content found. Output written to {output_file_path}.")


    with open(output_file_json, 'w') as output_file:
        if matching_modules:
            json.dump(matching_modules, output_file, indent=4)
            print(f"Matching modules have been written to {output_file_json}.")
        else:
            json.dump({"message": "No modules with identical content found."}, output_file, indent=4)
            print(f"No modules with identical content found. Output written to {output_file_json}.")

# checkVerilogUnique()  

# JSONL output file path
output_jsonl = 'output_modules.jsonl'

# Process all .v files and write JSONL
with open(output_jsonl, 'w', encoding='utf-8') as jsonl_file:
    for root, dirs, files in os.walk(github_scrape_folder):
        for file in files:
            if file.endswith('.v'):
                file_path = os.path.join(root, file)

                # Format the Verilog file before reading
                formatData(file_path)

                # Read and process the formatted Verilog file
                with open(file_path, 'r', encoding='latin-1') as f:
                    data = f.read()

                # Extract module header and code
                io_header, code = separate_io_header(data)

                if io_header:
                    module_data = {
                        "header": io_header,
                        "code": code
                    }

                    # Write each module as a separate JSON object
                    json.dump(module_data, jsonl_file)
                    jsonl_file.write("\n")

