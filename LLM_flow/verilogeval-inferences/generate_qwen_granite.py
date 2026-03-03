import json
import os
import sys
import time
from pathlib import Path
from typing import Tuple

import fire
import torch
import numpy as np
import math
from datetime import timedelta


from transformers import AutoTokenizer, CodeGenForCausalLM, GenerationConfig, AutoModelForCausalLM, DataCollatorForLanguageModeling
import pandas as pd

import jsonlines

#only support https://github.com/NVlabs/verilog-eval/tree/release/1.0.0 
#pay attention to the "verilog-eval" or "verilog_eval" which is used in mg-verilog's own midified VerilogEval
# sys.path.append("../verilog_eval/verilog_eval")
sys.path.append("/u/jinghua3/Documents/LLM4HWDesign_Starting_Toolkit/verilog-eval/verilog_eval")
from evaluation import evaluate_functional_correctness
from datetime import datetime
from tqdm import tqdm

from accelerate import PartialState, Accelerator, DeepSpeedPlugin
from accelerate.utils import InitProcessGroupKwargs
import torch.distributed as dist
import torch.multiprocessing as mp

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    set_seed,
    Seq2SeqTrainer,
    BitsAndBytesConfig,
)
from tokenizers import AddedToken

import warnings
from packaging import version
from packaging.version import parse

from transformers import LlamaForCausalLM, LlamaConfig
from accelerate import init_empty_weights, load_checkpoint_and_dispatch


# llama2_prompt_without_memory ="""
#     <s>[INST] <<SYS>>
#     {system_message}
#     <</SYS>>

#     {human_input} [/INST]
# """

# llama2_prompt_without_memory_without_sys ="""
# <s>[INST] {human_input} [/INST]
# """

# llama2_pompt_with_memory_without_sys ="""
# <s>[INST] {chat_history} {human_input} [/INST]
# """

baseline_system_prompt = "You only complete chats with syntax correct Verilog code. End the Verilog module code completion with 'endmodule'. Do not include module, input and output definitions."
baseline_question_prompt = "Implement the Verilog module based on the following description. Assume that signals are positive clock/clk edge triggered unless otherwise stated."
baseline_problem_description = "\n\n{description}\n\nModule header:\n\n{module_header}\n"
# PROMPT_BASELINE = llama2_prompt_without_memory.format(system_message = system_prompt, human_input = question_prompt + problem_description)

# system_prompt = "You only expand the high level summary of a Verilog code module design to block level summaries."
# question_prompt = "Come up with correct functional blocks for to implement the Verilog module in the high level summary, and expand the high level summary to block level summaries."
# problem_description = "\n Here is the high level summary:\n\n {description} \n\n\n Here is the Verilog module header:\n\n {module_header} \n\n" 
# LLM1_PROMPT = llama2_prompt_without_memory.format(system_message = system_prompt, human_input = question_prompt + problem_description)

# system_prompt = "You only complete chats with syntax correct Verilog code. End the Verilog module code completion with 'endmodule'. Do not include module, input and output definitions."
# question_prompt = "Implement the Verilog module based on the following block level summaries. Assume that signals are positive clock/clk edge triggered unless otherwise stated."
# problem_description = "\nHere are block level summaries:\n\n {description} \n\n Module header:\n\n {module_header} \n"
# LLM2_BLOCK_TO_CODE_PROMPT = llama2_prompt_without_memory.format(system_message = system_prompt, human_input = question_prompt + problem_description)

# system_prompt = "You only complete chats with syntax correct Verilog code. End the Verilog module code completion with 'endmodule'. Do not include module, input and output definitions."
# question_prompt = "Implement the Verilog module based on the following block level summaries. Assume that signals are positive clock/clk edge triggered unless otherwise stated."
# problem_description = "{description}  \n\n Module header:\n\n {module_header} \n"
# LLM2_BLOCK_GLOBAL_TO_CODE_PROMPT = llama2_prompt_without_memory.format(system_message = system_prompt, human_input = question_prompt + problem_description)

def mem():
    # print("torch.cuda.memory_allocated: %fGB"%(torch.cuda.memory_allocated(0)/1024/1024/1024))
    # print("torch.cuda.memory_reserved: %fGB"%(torch.cuda.memory_reserved(0)/1024/1024/1024))
    # print("torch.cuda.max_memory_reserved: %fGB"%(torch.cuda.max_memory_reserved(0)/1024/1024/1024))
    return torch.cuda.memory_allocated(0)/1024/1024/1024

def timestamp():
    return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"

import importlib
from peft import (
    prepare_model_for_kbit_training,
    LoraConfig,
    get_peft_model,
    PeftModel
)
from peft.tuners.lora import LoraLayer
from os.path import exists, join, isdir


def is_ipex_available():
    def get_major_and_minor_from_version(full_version):
        return str(version.parse(full_version).major) + "." + str(version.parse(full_version).minor)

    _torch_version = importlib.metadata.version("torch")
    if importlib.util.find_spec("intel_extension_for_pytorch") is None:
        return False
    _ipex_version = "N/A"
    try:
        _ipex_version = importlib.metadata.version("intel_extension_for_pytorch")
    except importlib.metadata.PackageNotFoundError:
        return False
    torch_major_and_minor = get_major_and_minor_from_version(_torch_version)
    ipex_major_and_minor = get_major_and_minor_from_version(_ipex_version)
    if torch_major_and_minor != ipex_major_and_minor:
        warnings.warn(
            f"Intel Extension for PyTorch {ipex_major_and_minor} needs to work with PyTorch {ipex_major_and_minor}.*,"
            f" but PyTorch {_torch_version} is found. Please switch to the matching version and run again."
        )
        return False
    return True


def smart_tokenizer_and_embedding_resize(
    special_tokens_dict,
    tokenizer,
    model,
):
    """Resize tokenizer and embedding.

    Note: This is the unoptimized version that may make your embedding size not be divisible by 64.
    """
    if "codellama" in model.name_or_path:
        for key, value in special_tokens_dict.items():
            special_tokens_dict[key] = AddedToken(value, lstrip=True, rstrip=True, normalized=False)

    num_new_tokens = tokenizer.add_special_tokens(special_tokens_dict)
    model.resize_token_embeddings(len(tokenizer))
    
    if num_new_tokens > 0:
        input_embeddings_data = model.get_input_embeddings().weight.data
        output_embeddings_data = model.get_output_embeddings().weight.data

        input_embeddings_avg = input_embeddings_data[:-num_new_tokens].mean(dim=0, keepdim=True)
        output_embeddings_avg = output_embeddings_data[:-num_new_tokens].mean(dim=0, keepdim=True)

        input_embeddings_data[-num_new_tokens:] = input_embeddings_avg
        output_embeddings_data[-num_new_tokens:] = output_embeddings_avg

def get_accelerate_model(model_name, tokenizer_type, checkpoint, bf16, fp16, cache_dir, hf_token=None):
    if torch.cuda.is_available():
        n_gpus = torch.cuda.device_count()
    if is_ipex_available() and torch.xpu.is_available():
        n_gpus = torch.xpu.device_count()
    
    max_memory = f'{38000}MB'
    max_memory = {i: max_memory for i in range(n_gpus)}
    # device_map = "auto"
    device_map = "balanced"

    # if we are in a distributed setting, we need to set the device map and max memory per device
    if os.environ.get('LOCAL_RANK') is not None:
        local_rank = int(os.environ.get('LOCAL_RANK', '0'))
        print("distributed", local_rank)
        device_map = {'': local_rank}
        max_memory = {'': max_memory[local_rank]}

    compute_dtype = (torch.float16 if fp16 else (torch.bfloat16 if bf16 else torch.float32))

    model = AutoModelForCausalLM.from_pretrained(
        model_name, 
        # use_cache=False,
        # cache_dir=checkpoint,
        device_map=device_map,
        max_memory= max_memory,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            load_in_8bit=False,
            llm_int8_threshold=6.0,
            llm_int8_has_fp16_weight=False,
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
            # bnb_4bit_quant_type="nf4",
        ),
        torch_dtype=(torch.float32 if fp16 else (torch.bfloat16 if bf16 else torch.float32)),
        # trust_remote_code=True,
        # low_cpu_mem_usage=False,
    )

    setattr(model, 'model_parallel', True)
    setattr(model, 'is_parallelizable', True)

    model.config.torch_dtype=(torch.float32 if fp16 else (torch.bfloat16 if bf16 else torch.float32))

    # Tokenizer
    print(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    for name, module in model.named_modules():
        if isinstance(module, LoraLayer):
            if bf16:
                module = module.to(torch.bfloat16)
        if 'norm' in name:
            module = module.to(torch.float32)
        if 'lm_head' in name or 'embed_tokens' in name:
            if hasattr(module, 'weight'):
                if bf16 and module.weight.dtype == torch.float32:
                    module = module.to(torch.bfloat16)
    return model, tokenizer

def load(
    checkpoint_dir: str,
    tokenizer_type: str = "code_llama",
    model_type: str = "hf",
    base_model: str = None,
    bf16: bool = False,
    fp16: bool = False,
    cache_dir: str = "/home/user_name/HF_cache/",
    hf_token: str = "your_hf_token_if_you_want_to_use_it",
    dev: str=None
):
    start_time = time.time()
    print("Loading base model", base_model, "Checkpoint", checkpoint_dir)
    model, tokenizer = get_accelerate_model(base_model, tokenizer_type, checkpoint_dir, bf16, fp16, cache_dir, hf_token=hf_token)
    print(f"Loaded in {time.time() - start_time:.2f} seconds")
    return model, tokenizer

class VerilogDataset(torch.utils.data.Dataset):
  def __init__(self, descriptions, headers, tokenizer, device, prompt_type= "baseline", desc_key = "detail_description", k=20):
    self.device = device
    self.tokenizer = tokenizer
    self.prompt_type = prompt_type

    self.prompts = []
    for desc in descriptions:
      for i in range(k):
        self.prompts.append({
          "task_id": desc["task_id"],
          "description": desc[desc_key],
          "module_header": headers[desc["task_id"]]
        })

  def __len__(self):
    return len(self.prompts)

  def __getitem__(self, index):
    if self.prompt_type == "baseline":
        PROMPT = self.tokenizer.apply_chat_template(
                    [
                        {"role": "system", "content": baseline_system_prompt},
                        {"role": "user", "content": baseline_question_prompt+baseline_problem_description},
                    ], 
                    tokenize=False, add_generation_prompt=True
                )
    # elif self.prompt_type == "llm1":
    #     PROMPT = LLM1_PROMPT
    # elif self.prompt_type == "llm2_block_to_code":
    #     PROMPT = LLM2_BLOCK_TO_CODE_PROMPT
    # elif self.prompt_type == "llm2_block_global_to_code":
    #     PROMPT = LLM2_BLOCK_GLOBAL_TO_CODE_PROMPT
    # else:
    #     raise Exception("Invalid prompt type.")
    prompt = PROMPT.format_map(self.prompts[index])
    return torch.tensor(self.tokenizer(prompt).input_ids).to(self.device)

def main(
    checkpoint_dir: str,
    model_type: str = "hf",
    tokenizer_type="code_llama",
    base_model: str = None,
    bf16: bool = False,
    fp16: bool = False,
    cache_dir: str = "/home/user_name/HF_cache/",
    hf_token: str = "your_hf_token_if_you_want_to_use_it",
    max_new_tokens: int = 1024,
    temperature = None,
    top_p = None,
    top_k = None,
    repetition_penalty = None,
    sample_k: int = 1,
    desc_file: str = "../verilog-eval/descriptions/VerilogDescription_Machine.jsonl",
    desc_key: str = "detail_description",
    prompt_type: str = "baseline",
    eval_file: str = "../verilog-eval/data/VerilogEval_Machine.jsonl",
    output_file: str = "./data/gen.jsonl",
    result_name: str = None,
    batch_size: int = 1,
    skip_iverilog: bool = False
):
    with torch.no_grad():
        # deepspeed_plugin = DeepSpeedPlugin(zero_stage=3, gradient_accumulation_steps=2)
        # accel = Accelerator(deepspeed_plugin=deepspeed_plugin)
        kwargs = InitProcessGroupKwargs(timeout=timedelta(seconds=3600))
        accel = Accelerator(kwargs_handlers=[kwargs])
        accel.print("Starting at", timestamp())

        accel.print("Loading model...")
        device = accel.device
        model, tokenizer = load(checkpoint_dir, tokenizer_type, model_type, base_model=base_model, bf16=bf16, fp16=fp16, cache_dir=cache_dir, hf_token=hf_token)
        model.eval()

        accel.print("Loading descriptions...")
        tasks = pd.read_json(path_or_buf=desc_file, lines=True)

        headers = {}
        with jsonlines.open(eval_file) as file:
            for obj in file:
                headers[obj["task_id"]] = obj["prompt"]

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        # clear temp file
        with open(output_file, "w") as file:
            pass

        outputs = []
        accel.print("Starting...")

        with accel.split_between_processes(tasks.to_dict(orient="records")) as prompts:
            # print("Distr", len(prompt), [r["task_id"] for r in prompt])
            tasks = prompts

        # create new dataset for each process to help with prompt batch balancing
        task_ids = [t["task_id"] for t in tasks]
        dataset = VerilogDataset(tasks, headers, tokenizer, device, desc_key=desc_key, prompt_type=prompt_type, k=sample_k)
        collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, collate_fn=collator)

        accel.print("Starting generation...")

        for i, prompts in enumerate(tqdm(dataloader, total=len(dataloader), desc="Process " + str(accel.process_index))):
            prompts = prompts["input_ids"]
            prompts = prompts.to(model.device)
            output = model.generate(
                inputs=prompts,
                # max_new_tokens=max_new_tokens,
                max_length=8192,
                do_sample=True,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                pad_token_id=tokenizer.pad_token_id
            )

            strings = tokenizer.batch_decode(output[:, prompts.shape[1]:], skip_special_tokens=True)
            full_responses = tokenizer.batch_decode(output, skip_special_tokens=True)
            prompt_strings = tokenizer.batch_decode(prompts[:, 30:], skip_special_tokens=True)

            for j, comp in enumerate(strings):
                tid = (i * batch_size + j) // sample_k
                obj = {
                    "process": accel.process_index,
                    "task_id": task_ids[tid],
                    "completion": comp,
                    "prompt": prompt_strings[j],
                    "full_response": full_responses[j],
                }
                outputs.append(obj)

        with jsonlines.open(output_file, mode="a") as writer:
            print(timestamp(), "starting write", accel.process_index, "length", len(outputs))
            writer.write_all(outputs)
            print(timestamp(), "done writing", accel.process_index)

        # evaluate
        accel.wait_for_everyone()

        # if accel.is_main_process and not skip_iverilog:
        #     accel.print("running eval")
        #     res = evaluate_functional_correctness(output_file, problem_file=eval_file, k=[1,5,10])
        #     accel.print("Eval Results:", res)
        #     with open("./data/results.txt", mode="a") as f:
        #         ts = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{' | ' + result_name if result_name is not None else ''}] "
        #         f.write(ts + str(res) + "temperature:{}".format(temperature) + "top_p:{}".format(top_p) + "top_k:{}".format(top_k) + "repetition_penalty:{}".format(repetition_penalty) + "\n")

if __name__ == "__main__":
    fire.Fire(main)
