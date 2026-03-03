# import json
# import random
# import tiktoken  # OpenAI tokenizer (install using `pip install tiktoken`)

# # Initialize tokenizer
# tokenizer = tiktoken.get_encoding("cl100k_base")  # OpenAI tokenizer (GPT-4/GPT-3.5)

# def count_tokens(text):
#     """Returns the token count of a given text."""
#     return len(tokenizer.encode(text))

# def sample_jsonl(input_file, output_file, sample_size=4458, min_tokens=30, max_tokens=7500):
#     filtered_objects = []

#     # Read and filter objects based on token length constraints
#     with open(input_file, 'r', encoding='utf-8') as infile:
#         for line in infile:
#             obj = json.loads(line.strip())  # Load JSON object
            
#             # Check token length of full_code (must be between min_tokens and max_tokens)
#             token_length = count_tokens(obj["verilog_code"])
#             if min_tokens <= token_length <= max_tokens:
#                 filtered_objects.append(obj)

#     # Ensure we have enough valid objects before sampling
#     if len(filtered_objects) < sample_size:
#         raise ValueError(f"Not enough valid objects. Found only {len(filtered_objects)}, need {sample_size}.")

#     # Randomly sample required number of objects
#     sampled_objects = random.sample(filtered_objects, sample_size)

#     # Remove 'cpp_code' key before writing to output file
#     with open(output_file, 'w', encoding='utf-8') as outfile:
#         for obj in sampled_objects:
#             obj.pop("cpp_code", None)  # Remove 'cpp_code' key if it exists
#             outfile.write(json.dumps(obj) + "\n")

# # Example usage
# sample_jsonl("/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label/merged_vhdl2.jsonl", "/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label/sampled_vhdl.jsonl")


import json
import random
import tiktoken  # OpenAI tokenizer (install using `pip install tiktoken`)

# Initialize tokenizer
tokenizer = tiktoken.get_encoding("cl100k_base")  # OpenAI tokenizer (GPT-4/GPT-3.5)

def count_tokens(text):
    """Returns the token count of a given text."""
    return len(tokenizer.encode(text)) if text else 0

def get_existing_indices(existing_file):
    """Extracts index values from an existing JSONL file."""
    existing_indices = set()
    with open(existing_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            obj = json.loads(line.strip())
            if "index" in obj:
                existing_indices.add(obj["index"])
    return existing_indices

def sample_jsonl(input_file, output_file, existing_file, sample_size=4, min_tokens=30, max_tokens=6000):
    filtered_objects = []
    existing_indices = get_existing_indices(existing_file)

    # Read and filter objects based on token length constraints
    with open(input_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            obj = json.loads(line.strip())  # Load JSON object
            
            # Ensure unique index
            if "index" in obj and obj["index"] in existing_indices:
                continue
            
            # Extract relevant text
            verilog_tokens = count_tokens(obj.get("verilog_code", ""))
            ioheader_tokens = count_tokens(obj.get("ioheader", ""))
            
            # Extract conversation length after `</think>`
            conversation = obj.get("conversation", "").strip()
            if "</think>" in conversation:
                conversation = conversation.split("</think>", 1)[-1].strip()
            conversation_tokens = count_tokens(conversation)

            # Total token count
            total_tokens = verilog_tokens + ioheader_tokens + conversation_tokens
            
            # Apply token length filter
            if min_tokens <= total_tokens <= max_tokens:
                filtered_objects.append(obj)

    # Ensure we have enough valid objects before sampling
    if len(filtered_objects) < sample_size:
        raise ValueError(f"Not enough valid objects. Found only {len(filtered_objects)}, need {sample_size}.")

    # Randomly sample required number of objects
    sampled_objects = random.sample(filtered_objects, sample_size)

    # Remove 'cpp_code' key before writing to output file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for obj in sampled_objects:
            obj.pop("cpp_code", None)  # Remove 'cpp_code' key if it exists
            outfile.write(json.dumps(obj) + "\n")

# Example usage
sample_jsonl(
    "/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label/merged_vhdl_final2.jsonl",
    "/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label/sampled_vhdl.jsonl",
    "/work/nvme/bcct/lad2025/ds_inference_results/11k_our_Label/final_11k_final.jsonl"
)

