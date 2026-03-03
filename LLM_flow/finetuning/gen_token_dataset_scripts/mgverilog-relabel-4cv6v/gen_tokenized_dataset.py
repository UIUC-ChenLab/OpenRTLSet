from functools import partial
from itertools import chain
import os
import torch
import jsonlines
from datasets import load_dataset, Dataset
from peft import LoraConfig, get_peft_model
from peft.tuners.lora import LoraLayer
from transformers import AutoModelForCausalLM, AutoTokenizer
import argparse

SRC_DATASET_PATH = "/work/nvme/bcct/lad2025/ds_inference_results/mgverilog_relabel/matched_cv.jsonl"
TARGET_DATASET_FOLDER_PATH = "/work/nvme/bcct/lad2025/finetuning/datasets/mgverilog-relabel-4cv6v"

TARGET_LLMS = [
    {"name": "granite-8b",  "path": "/work/nvme/bcct/lad2025/llm_models/granite-8b-code-instruct-hf"},
    {"name": "granite-34b", "path": "/work/nvme/bcct/lad2025/llm_models/granite-34b-code-instruct-hf"},
    {"name": "qwen2.5-7b",  "path": "/work/nvme/bcct/lad2025/llm_models/qwen2.5-coder-7b-instruct-hf"},
    {"name": "qwen2.5-32b", "path": "/work/nvme/bcct/lad2025/llm_models/qwen2.5-coder-32b-instruct-hf"}
]
MAX_SEQ_LENGTH = 8192
TRAIN_FOLDER_NAME = "train"
VALIDATION_FOLDER_NAME = "validation"
SYS_STRING = '''You only complete chats with syntax correct Verilog code. End the Verilog module code completion with 'endmodule'. Do not include module, input and output definitions.'''
USER_PREFIX_STRING = '''Implement the Verilog module based on the following description. Assume that signals are positive clock/clk edge triggered unless otherwise stated.\n\n'''
MODULE_HEADER_STRING = "\n\nModule header:\n\n"


def extract_description_from_deepseek_response(input_str):
    think_end_str = "</think>"
    assert think_end_str in input_str
    desc_str_idx = input_str.rfind(think_end_str)
    desc_str = input_str[desc_str_idx+len(think_end_str):]
    return desc_str.strip()

def group_texts(examples, block_size):
    # Concatenate all texts.
    concatenated_examples = {k: list(chain(*examples[k])) for k in examples.keys()}
    total_length = len(concatenated_examples[list(examples.keys())[0]])
    # We drop the small remainder, and if the total_length < block_size  we exclude this batch and return an empty dict.
    # We could add padding if the model supported it instead of this drop, you can customize this part to your needs.
    total_length = (total_length // block_size) * block_size
    # Split by chunks of max_len.
    result = {
        k: [t[i : i + block_size] for i in range(0, total_length, block_size)]
        for k, t in concatenated_examples.items()
    }
    if "labels" not in result:
        result["labels"] = result["input_ids"].copy()
    return result


def tokenize_function(example, eval=False):
    output_texts = []
    mask_labels_sizes = []
    for i in range(len(example['conversation'])):
        _conversation_str = example['conversation'][i]
        _description_str = extract_description_from_deepseek_response(_conversation_str)
        assert _description_str != ""
        _ioheader_str = example['ioheader'][i]
        _verilog_body_str = example['verilog_code'][i]
        _user_str = USER_PREFIX_STRING + _description_str + MODULE_HEADER_STRING + _ioheader_str
        _user_str = _user_str.strip()
        output_texts.append(
                tokenizer.apply_chat_template(
                    [
                        {"role": "system", "content": SYS_STRING},
                        {"role": "user", "content": _user_str},
                        {"role": "assistant", "content": _verilog_body_str},
                    ], 
                    tokenize=False, add_generation_prompt=False
                ).rstrip() + tokenizer.pad_token
        )
        if eval:
            mask_labels_sizes.append(
                tokenizer.apply_chat_template(
                    [
                        {"role": "system", "content": SYS_STRING},
                        {"role": "user", "content": _user_str},
                    ], 
                    tokenize=False, add_generation_prompt=True
                )
            )
    tokenized = tokenizer(output_texts)
    input_ids = tokenized.input_ids
    # input_attn_mask = tokenized.attention_mask
    if eval:
        mask_labels_tokenized = tokenizer(mask_labels_sizes)
        labels_ids = mask_labels_tokenized.input_ids
        # labels_attn_mask = mask_labels_tokenized.attention_masks
        masked_labels = []
        for out, lb in zip(input_ids, labels_ids):
            ml = out.copy()
            ml[: len(lb)] = [-100] * len(lb)
            ml[-1] = -100
            masked_labels.append(ml)
        # return {"input_ids": input_ids, "input_attention_mask": input_attn_mask,  "labels": masked_labels}
        return {"input_ids": input_ids, "labels": masked_labels}
    else:
        return {"input_ids": input_ids, "labels": input_ids}



def filter_function(example):
    to_keep = []
    for i in range(len(example["input_ids"])):
        if len(example["input_ids"][i]) > MAX_SEQ_LENGTH:
            # raise RuntimeError("found a sample with index:"+str(i)+" with sequence length too long with length: "+str(len(example["input_ids"][i])))
            to_keep.append(False)
        else:
            to_keep.append(True)
    return to_keep


def create_datasets(dataset, tokenizer):
    # train_dataset = dataset["train"]
    # valid_dataset = dataset["validation"]
    train_dataset = dataset
    valid_dataset = dataset
    column_names = train_dataset.features
    # tokenize
    train_dataset = train_dataset.map(
        tokenize_function,
        batched=True,
        num_proc=1,
        remove_columns=column_names,
    )
    valid_dataset = valid_dataset.map(
        partial(tokenize_function, eval=True),
        batched=True,
        num_proc=1,
        remove_columns=column_names,
    )
    # filter, remove samples that are too long
    train_dataset = train_dataset.filter(
        filter_function,
        batched=True,
        # with_indices=True,
        num_proc=1,
        # remove_columns=column_names,
    )
    valid_dataset = valid_dataset.filter(
        filter_function,
        batched=True,
        # with_indices=True,
        num_proc=1,
        # remove_columns=column_names,
    )
    # print(
    #     f"Before packing, Size of the train set: {len(train_dataset)}. Size of the validation set: {len(valid_dataset)}"
    # )
    # # Packing
    # packing_method = partial(group_texts, block_size=MAX_SEQ_LENGTH)
    # train_dataset = train_dataset.map(packing_method, batched=True, num_proc=1)
    # valid_dataset = valid_dataset.map(packing_method, batched=True, num_proc=1)
    print(
        f"Size of the train set: {len(train_dataset)}. Size of the validation set: {len(valid_dataset)}"
    )
    return train_dataset, valid_dataset


if __name__ == "__main__":
    # process dataset for all four LLMs
    for llm_info in TARGET_LLMS:
        print("generating dataset for LLM:", llm_info['name'])
        # load src dataset from jsonl
        data = []
        with jsonlines.open(SRC_DATASET_PATH) as reader:
            for obj in reader:
                data.append(obj)
        src_dataset = Dataset.from_list(data)
        # load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(llm_info['path'])
        # create tokenized datasets 
        train_dataset, valid_dataset = create_datasets(dataset=src_dataset, tokenizer=tokenizer)
        # save tokenized datasets
        train_dataset.save_to_disk(os.path.join(TARGET_DATASET_FOLDER_PATH, llm_info['name'], TRAIN_FOLDER_NAME))
        valid_dataset.save_to_disk(os.path.join(TARGET_DATASET_FOLDER_PATH, llm_info['name'], VALIDATION_FOLDER_NAME))
