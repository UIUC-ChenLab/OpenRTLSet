# import json
# import os

# folder_path = "/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label"  # Change this to your actual folder path
# output_file = "/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label/labelled_11k_our_400k_merged.jsonl"

# with open(output_file, "w") as outfile:
#     for filename in os.listdir(folder_path):
#         if filename.startswith("labelled_11k4v_our_") and filename.endswith(".jsonl"):
#             file_path = os.path.join(folder_path, filename)
#             print(file_path)
#             with open(file_path, "r") as infile:
#                 for line in infile:
#                     obj = json.loads(line)
                    
#                     # Remove the full_code key if it exists
#                     obj.pop("full_code", None)
                    
#                     outfile.write(json.dumps(obj) + "\n")

# print(f"Merged JSONL file saved as {output_file}")


# import json
# import os
# import re

# def extract_io_header(verilog_code):
#     """Extract IO header from Verilog code and return it separately."""
#     match = re.search(r"(module\s.*?;)", verilog_code, re.DOTALL)
#     if match:
#         io_header = match.group(1)
#         verilog_code = verilog_code.replace(io_header, "").strip()  # Remove IO header from Verilog code
#         return io_header, verilog_code
#     return "", verilog_code

# def remove_comments(verilog_code):
#     """Remove single-line and multi-line comments from Verilog code."""
#     verilog_code = re.sub(r"//.*?\n", "\n", verilog_code)  # Remove single-line comments
#     verilog_code = re.sub(r"/\*.*?\*/", "", verilog_code, flags=re.DOTALL)  # Remove multi-line comments
#     return verilog_code.strip()

# folder_path = "/work/nvme/bcct/lad2025/ds_inference_results/vhdl_dataset"  # Change this to your actual folder path
# output_file = "/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label/merged_vhdl.jsonl"

# with open(output_file, "w") as outfile:
#     for filename in os.listdir(folder_path):
#         if filename.startswith("vhdl") and filename.endswith(".jsonl"):
#             file_path = os.path.join(folder_path, filename)
#             with open(file_path, "r") as infile:
#                 for line in infile:
#                     obj = json.loads(line)

#                     # Remove the full_code key if it exists
#                     obj.pop("full_code", None)

#                     # Extract and update IO header
#                     if "verilog_code" in obj:
#                         clean = remove_comments(obj["verilog_code"])
#                         if ("ioheader" not in obj or not obj["ioheader"].strip()):
#                             obj["ioheader"], obj["verilog_code"] = extract_io_header(clean)
#                         else:
#                             empty_io , obj["verilog_code"] = extract_io_header(clean)

#                     # Filter out objects with empty or invalid conversation
#                     conversation = obj.get("conversation", "").strip()
#                     if not conversation or "</think>" in conversation and not conversation.split("</think>", 1)[1].strip():
#                         continue  # Skip this object

#                     outfile.write(json.dumps(obj) + "\n")

# print(f"Merged JSONL file saved as {output_file}")


# import json
# import os
# import re

# def extract_io_header(verilog_code):
#     """Extract IO header from Verilog code and return it separately."""
#     match = re.search(r"(module\s.*?;)", verilog_code, re.DOTALL)
#     if match:
#         io_header = match.group(1)
#         verilog_code = verilog_code.replace(io_header, "").strip()  # Remove IO header from Verilog code
#         return io_header.strip(), verilog_code.strip()
#     return "", verilog_code.strip()

# def remove_comments(verilog_code):
#     """Remove single-line and multi-line comments from Verilog code."""
#     verilog_code = re.sub(r"//.*?\n", "\n", verilog_code)  # Remove single-line comments
#     verilog_code = re.sub(r"/\*.*?\*/", "", verilog_code, flags=re.DOTALL)  # Remove multi-line comments
#     return verilog_code.strip()

# # Update these paths as needed
# input_folder = "/work/nvme/bcct/lad2025/datasets/Intermediate/jsonl_sanjana"
# output_file = "/work/nvme/bcct/lad2025/datasets/Full_dataset/sanjana_full.jsonl"

# with open(output_file, "w") as outfile:
#     for filename in os.listdir(input_folder):
#         if filename.startswith("vhdl") and filename.endswith(".jsonl"):
#             file_path = os.path.join(input_folder, filename)
#             with open(file_path, "r") as infile:
#                 for line in infile:
#                     obj = json.loads(line)

#                     # Process index: prepend 999
#                     if "index" in obj and isinstance(obj["index"], int):
#                         obj["index"] = int(f"999{obj['index']}")
#                     obj.pop("code", None)
#                     # Remove comments from full_code
#                     if "full_code" in obj:
#                         cleaned_code = remove_comments(obj["full_code"])
#                         ioheader, verilog_code = extract_io_header(cleaned_code)
#                         obj["verilog_code"] = verilog_code
#                         obj["ioheader"] = ioheader
#                         del obj["full_code"]  # Remove original full_code if no longer needed

#                     # Write modified object
#                     outfile.write(json.dumps(obj) + "\n")

# print(f"Merged JSONL file saved as {output_file}")



# import json

# input_file = "/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label/merged_vhdl.jsonl"  # Change this to your actual file
# output_file = "/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label/merged_vhdl2.jsonl"

# with open(input_file, "r") as infile, open(output_file, "w") as outfile:
#     for line in infile:
#         obj = json.loads(line)

#         # Prefix "v" to the index value if it exists
#         if "index" in obj:
#             obj["index"] = f"v{obj['index']}"

#         outfile.write(json.dumps(obj) + "\n")

# print(f"Updated JSONL file saved as {output_file}")


# import json
# import re

# input_file = "/work/nvme/bcct/lad2025/datasets/Full_dataset/vhdl_full_clean.jsonl"  # Change this to your actual file
# output_file = "/work/nvme/bcct/lad2025/datasets/Full_dataset/vhdl_full_clean2.jsonl"

# # Regex pattern to match (* x_core_info = <some_text> *)
# core_info_pattern = r"\(\* x_core_info\s*=\s*[^*]*\*\)"

# with open(input_file, "r") as infile, open(output_file, "w") as outfile:
#     for line in infile:
#         obj = json.loads(line)

#         # Remove the pattern from verilog_code if it exists
#         if "verilog_code" in obj:
#             obj["verilog_code"] = re.sub(core_info_pattern, "", obj["verilog_code"]).strip()

#         outfile.write(json.dumps(obj) + "\n")

# print(f"Cleaned JSONL file saved as {output_file}")


# import json
# import re

# input_file = "/work/nvme/bcct/lad2025/datasets/Full_dataset/vhdl_full.jsonl"  # Change this to your actual file

# # Regex pattern to match (* x_core_info = <some_text> *)
# core_info_pattern = r"\(\* X_CORE_INFO\s*=\s*[^*]*\*\)"

# # Read and clean the data
# with open(input_file, "r") as infile:
#     lines = infile.readlines()

# cleaned_lines = []
# for line in lines:
#     obj = json.loads(line)
    
#     # Remove the pattern from verilog_code if it exists
#     if "verilog_code" in obj:
#         obj["verilog_code"] = re.sub(core_info_pattern, "", obj["verilog_code"]).strip()
    
#     cleaned_lines.append(json.dumps(obj) + "\n")

# # Write back to the same file
# with open(input_file, "w") as outfile:
#     outfile.writelines(cleaned_lines)

# print(f"Cleaned JSONL file saved back to {input_file}")



# import json

# input_file = "/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label/400v_with_conversation.jsonl"  # Replace with your actual input file name
# output_file = "/work/nvme/bcct/lad2025/datasets/Full_dataset/400v.jsonl"  # Replace with your desired output file name

# with open(input_file, "r") as infile, open(output_file, "w") as outfile:
#     for line in infile:
#         obj = json.loads(line)
#         new_obj = {
#             "index": obj["index"],
#             "ioheader": obj["ioheader"],
#             "verilog_code": obj["verilog_code"],
#             "full_code": obj["ioheader"] + obj["verilog_code"]
#         }
#         json.dump(new_obj, outfile)
#         outfile.write("\n")

# print("Processed JSONL file has been saved as", output_file)


import json
import os
import re

def extract_io_header(verilog_code):
    """Extract IO header from Verilog code and return it separately."""
    match = re.search(r"(module\s.*?;)", verilog_code, re.DOTALL)
    if match:
        io_header = match.group(1)
        verilog_code = verilog_code.replace(io_header, "").strip()
        return io_header.strip(), verilog_code.strip()
    return "", verilog_code.strip()

def remove_comments(verilog_code):
    """Remove single-line and multi-line comments from Verilog code."""
    verilog_code = re.sub(r"//.*?\n", "\n", verilog_code)
    verilog_code = re.sub(r"/\*.*?\*/", "", verilog_code, flags=re.DOTALL)
    return verilog_code.strip()

# === INPUT AND OUTPUT PATHS ===
input_folder = "/work/nvme/bcct/lad2025/datasets/Intermediate/jsonl_sanjana"
output_file = "/work/nvme/bcct/lad2025/datasets/Full_dataset/sanjana_full.jsonl"

# Counter for assigning index if missing
missing_index_counter = 0

with open(output_file, "w") as outfile:
    for filename in os.listdir(input_folder):
        if filename.startswith("output") and filename.endswith(".jsonl"):
            file_path = os.path.join(input_folder, filename)
            with open(file_path, "r") as infile:
                for line in infile:
                    obj = json.loads(line)

                    # Add index if missing, or prepend 999 if it exists
                    if "index" not in obj:
                        obj["index"] = missing_index_counter
                        missing_index_counter += 1
                    elif isinstance(obj["index"], int):
                        obj["index"] = int(f"8888{obj['index']}")

                    # Flatten the license field if needed
                    if isinstance(obj.get("license"), dict) and "name" in obj["license"]:
                        obj["license"] = obj["license"]["name"]

                    # Remove "code" key if it exists
                    # obj.pop("code", None)

                    # Process full_code
                    if "code" in obj:
                        cleaned_code = remove_comments(obj["code"])
                        ioheader, verilog_code = extract_io_header(cleaned_code)
                        obj["verilog_code"] = verilog_code
                        obj["ioheader"] = ioheader
                        del obj["code"]

                    # Reorder keys
                    reordered_obj = {
                        "index": obj.get("index"),
                        "verilog_code": obj.get("verilog_code", ""),
                        "ioheader": obj.get("ioheader", ""),
                        "cpp_code": obj.get("cpp_code", ""),
                        "repo_url" : obj.get("repo_url", ""),
                        "repo_name" : obj.get("repo_name","")
                    }

                    # Append license if it exists
                    if "license" in obj:
                        reordered_obj["license"] = obj["license"]

                    outfile.write(json.dumps(reordered_obj) + "\n")

print(f"Merged JSONL file saved as {output_file}")

