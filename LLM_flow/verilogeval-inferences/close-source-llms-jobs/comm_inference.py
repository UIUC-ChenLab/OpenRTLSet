#!/usr/bin/env python
import os
import time
from datetime import datetime

import fire
import openai
import anthropic
import pandas as pd
import jsonlines
from tqdm import tqdm

# Define the baseline prompt components.
baseline_system_prompt = (
    "You only complete chats with syntax correct Verilog code. "
    "End the Verilog module code completion with 'endmodule'. "
    "Do not include module, input and output definitions."
)
baseline_question_prompt = (
    "Implement the Verilog module based on the following description. "
    "Assume that signals are positive clock/clk edge triggered unless otherwise stated."
)
baseline_problem_description = "\n\n{description}\n\nModule header:\n\n{module_header}\n"


def get_completion_from_openai(user_prompt, system_prompt, max_tokens=1024, temperature=0.7, model="gpt-3.5-turbo"):
    """
    Calls OpenAI's API using the updated v1.0+ client library interface.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    
    client = openai.OpenAI(api_key=openai_api_key)

    try:
        if model == "o3-mini": # o3-mini does not support max tokens
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                # max_tokens=max_tokens,
                # temperature=temperature,
            )
        else:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return ""


def get_completion_from_claude(user_prompt, system_prompt, max_tokens=1024, temperature=0.7, model="claude-3-opus-20240229"):
    """
    Calls Anthropic's Claude API using the current Messages API format.
    """
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    if not claude_api_key:
        raise ValueError("CLAUDE_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=claude_api_key)
    try:
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error during Claude API call: {e}")
        return ""


def main(
    # llm: str = "gpt",  # set to "gpt" or "claude"
    # desc_file: str = "./verilog-eval/descriptions/VerilogDescription_Machine.jsonl",
    # eval_file: str = "./verilog-eval/data/VerilogEval_Machine.jsonl",
    desc_file: str = "./verilog-eval/descriptions/VerilogDescription_Human.jsonl",
    eval_file: str = "./verilog-eval/data/VerilogEval_Human.jsonl",
    # output_file: str = "./data/gen——4omini_10.jsonl",
    sample_k: int = 10,
    max_new_tokens: int = 2048,
    # temperature: float = 0.2,
    # model: str = "gpt-4o-mini"  # applicable only for GPT
):
    """
    This script reads a set of Verilog design descriptions and module headers,
    builds a prompt for each task, calls either GPT or Claude for code completion,
    and writes out the completions to a jsonl file.
    """

    # Parameters Setting
    llm = "gpt"
    # llm = "claude"

    if llm == "gpt":
        model = "o3-mini"
    elif llm == "claude":
        # model = "claude-3-opus-20240229" # testing claude API
        model = "claude-3-7-sonnet-20250219" # claude 3.7-sonnet
    temperature = 0.7
    # temperature = 0.8

    # Create descriptive output filename based on parameters
    output_file = f"./data/gen_{llm}_{model.replace('-', '_')}_{temperature}_{sample_k}_{max_new_tokens}.jsonl"

    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting generation using {llm.upper()} API...")

    # Load descriptions.
    try:
        tasks = pd.read_json(path_or_buf=desc_file, lines=True)
    except Exception as e:
        print(f"Error reading desc_file: {e}")
        return

    # Load evaluation file to extract headers.
    headers = {}
    try:
        with jsonlines.open(eval_file) as reader:
            for obj in reader:
                headers[obj["task_id"]] = obj["prompt"]
    except Exception as e:
        print(f"Error reading eval_file: {e}")
        return

    # Build prompts.
    prompts = []
    for _, task in tasks.iterrows():
        # Use the "detail_description" field; adjust the key if needed.
        description = task.get("detail_description", "")
        task_id = task.get("task_id", "unknown")
        module_header = headers.get(task_id, "")
        
        # Construct the prompt.
        user_prompt = (
            baseline_question_prompt +
            baseline_problem_description.format(
                description=description,
                module_header=module_header
            )
        )
        
        # Create sample_k copies for each task.
        for _ in range(sample_k):
            prompts.append({
                "task_id": task_id,
                "prompt": user_prompt,
                "system_prompt": baseline_system_prompt,
                "description": description,
                "module_header": module_header
            })

    outputs = []
    # Iterate over prompts and call the selected API.
    for item in tqdm(prompts, desc="Generating completions"):
        task_id = item["task_id"]
        system_prompt = item["system_prompt"]
        user_prompt = item["prompt"]
        
        # Combine for saving in the output
        full_prompt = system_prompt + "\n" + user_prompt

        if llm.lower() == "claude":
            # For Claude, we need to format the prompt differently
            # Note: Might need to update this if using a newer Claude API version
            claude_prompt = f"{anthropic.HUMAN_PROMPT} {user_prompt} {anthropic.AI_PROMPT}"
            completion = get_completion_from_claude(user_prompt=user_prompt, system_prompt=system_prompt, max_tokens=max_new_tokens, temperature=temperature, model=model)
        else:
            completion = get_completion_from_openai(user_prompt, system_prompt, max_tokens=max_new_tokens, temperature=temperature, model=model)
        
        outputs.append({
            "task_id": task_id,
            "prompt": full_prompt,
            "completion": completion,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        # Optional: add a short delay to avoid hitting API rate limits.
        time.sleep(0.5)

    # Ensure output directory exists.
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    try:
        with jsonlines.open(output_file, mode="w") as writer:
            writer.write_all(outputs)
    except Exception as e:
        print(f"Error writing output_file: {e}")
        return

    elapsed = time.time() - start_time
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Generation complete. {len(outputs)} completions saved to {output_file}.")
    print(f"Elapsed time: {elapsed:.2f} seconds.")


if __name__ == "__main__":
    fire.Fire(main)