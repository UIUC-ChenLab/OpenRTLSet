#!/bin/bash
#SBATCH --job-name="3EV_G8ft"
#SBATCH --output="log.%j.%N.out"
#SBATCH --partition=ghx4
#SBATCH --mem=50G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16   # spread out to use 1 core per numa, set to 64 if tasks is 1
#SBATCH --gpus-per-node=2
#SBATCH --account=becn-dtai-gh  # <- match to a "Project" returned by the "accounts" command
#SBATCH --no-requeue
#SBATCH -t 24:00:00

# load conda env 
# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/u/jinghua3/programs/miniconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/u/jinghua3/programs/miniconda3/etc/profile.d/conda.sh" ]; then
        . "/u/jinghua3/programs/miniconda3/etc/profile.d/conda.sh"
    else
        export PATH="/u/jinghua3/programs/miniconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<
conda activate ds124

# export OMP_NUM_THREADS=8
# export PYTORCH_CUDA_ALLOC_CONF=garbage_collection_threshold:0.8,max_split_size_mb:1024
accelerate launch --config_file /work/nvme/bcct/lad2025/finetuning/job_scripts/deepseek-pft-src/configs/config_7-14b.yaml /work/nvme/bcct/lad2025/finetuning/job_scripts/deepseek-pft-src/python_scripts/train_iccad_challenge_2024.py \
--train_dataset_path "/work/nvme/bcct/lad2025/finetuning/datasets/mgverilog-3EV/granite-8b/train" \
--valid_dataset_path "/work/nvme/bcct/lad2025/finetuning/datasets/mgverilog-3EV/granite-8b/validation" \
--model_path "/work/nvme/bcct/lad2025/llm_models/granite-8b-code-instruct-hf" \
--max_seq_len 8192 \
--bf16 True \
--logging_steps 51200 \
--eval_steps 51200 \
--save_steps 2048 \
--output_dir "/work/nvme/bcct/lad2025/finetuning/llm_ckpts/mgverilog-3EV/granite-8b" \
--per_device_train_batch_size 1 \
--gradient_accumulation_steps 1 \
--lr_scheduler_type "cosine" \
--learning_rate 4e-4 \
--weight_decay 0.0001 \
--warmup_ratio 0 \
--max_grad_norm 0.3 \
--use_gradient_checkpointing True \
--target_eval_loss 0.925 \
--use_peft_lora True \
--lora_r 16 \
--lora_alpha 32 \
--lora_dropout 0.1 \
--max_steps 51200 \
--seed 100 \
--lora_target_modules "qkv_proj,o_proj"
