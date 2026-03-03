import sys, os
import torch
import argparse
from transformers import AutoTokenizer, LlamaTokenizer, AutoModelForCausalLM
from peft import PeftModel, AutoPeftModelForCausalLM

def merge_llm_ckpt(base_model_dir, peft_saved_path, merged_model_output_dir):
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_dir,
        device_map=None,
        use_cache=False,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        max_position_embeddings=8192,
    )
    # base_model.load_adapter(peft_saved_path)
    model_to_merge = PeftModel.from_pretrained(model=base_model, model_id=peft_saved_path)
    merged_model = model_to_merge.merge_and_unload()
    merged_model.save_pretrained(merged_model_output_dir)
    tokenizer = AutoTokenizer.from_pretrained(base_model_dir)
    tokenizer.save_pretrained(merged_model_output_dir)

# CKPTS = [10240*1, 10240*2, 10240*3, 10240*4, 10240*5]
CKPTS = [10240*1, 10240*2, 10240*3, 10240*4, 10240*5, 10240*6, 10240*7, 10240*8, 10240*9, 10240*10]

TARGET_LLMS = [
    {"name": "granite-8b",  "path": "/work/nvme/bcct/lad2025/llm_models/granite-8b-code-instruct-hf"},
    {"name": "granite-34b", "path": "/work/nvme/bcct/lad2025/llm_models/granite-34b-code-instruct-hf"},
    {"name": "qwen2.5-7b",  "path": "/work/nvme/bcct/lad2025/llm_models/qwen2.5-coder-7b-instruct-hf"},
    {"name": "qwen2.5-32b", "path": "/work/nvme/bcct/lad2025/llm_models/qwen2.5-coder-32b-instruct-hf"}
]

def parse_args():
    parser = argparse.ArgumentParser(description="Process Verilog files using a range of entries.")
    parser.add_argument('--peft_src_dir', type=str, default="", help='Input LLM PEFT LORA checkpoints dir.')
    parser.add_argument('--llm_target_dir', type=str, default="", help='Output folder of merged full LLM models.')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    PEFT_SRC_DIR = args.peft_src_dir
    LLM_TARGET_DIR = args.llm_target_dir
    assert PEFT_SRC_DIR != ""
    assert LLM_TARGET_DIR != ""
    print("Processing LLMs merging from:", PEFT_SRC_DIR)
    for llm in TARGET_LLMS:
        for ck in CKPTS:
            print("\nWorking on:", llm['name'], 'at checkpoint', ck)
            _peft_src_path = os.path.join(PEFT_SRC_DIR, llm['name'], "checkpoint-"+str(ck))
            _output_dir = os.path.join(LLM_TARGET_DIR, llm['name'], "checkpoint-"+str(ck))
            if os.path.isdir(_output_dir) and len(os.listdir(_output_dir)) > 0:
                safetensors_generated = False
                task_done = False
                for _f in os.listdir(_output_dir):
                    if ".safetensors" in _f:
                        safetensors_generated = True
                        break
                    if _f == "DONE":
                        task_done = True
                        break
                if safetensors_generated:
                    print("LLM already merged.")
                    print()
                    continue
                if task_done:
                    print("LLM task already done.")
                    print()
                    continue
            if not os.path.isdir(_peft_src_path):
                print("LLM SRC path does not exist, job haven't finished...")
                print()
                continue
            os.makedirs(os.path.dirname(_output_dir), exist_ok=True)
            merge_llm_ckpt(base_model_dir=llm['path'], peft_saved_path=_peft_src_path, merged_model_output_dir=_output_dir)
            print()