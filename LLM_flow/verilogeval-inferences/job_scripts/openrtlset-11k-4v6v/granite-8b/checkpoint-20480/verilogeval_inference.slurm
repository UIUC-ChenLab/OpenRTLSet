#!/bin/bash
#SBATCH --job-name="veG8_DRIVE4v6v20480"
#SBATCH --output="log.%j.%N.out"
#SBATCH --partition=gpuA40x4
#SBATCH --mem=160G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16   # spread out to use 1 core per numa, set to 64 if tasks is 1
#SBATCH --gpus-per-node=2
#SBATCH --account=bcct-delta-gpu  # <- match to a "Project" returned by the "accounts" command
#SBATCH --no-requeue
#SBATCH -t 48:00:00

# load conda env 
# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/work/nvme/bcct/jinghua3/programs/miniconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/work/nvme/bcct/jinghua3/programs/miniconda3/etc/profile.d/conda.sh" ]; then
        . "/work/nvme/bcct/jinghua3/programs/miniconda3/etc/profile.d/conda.sh"
    else
        export PATH="/work/nvme/bcct/jinghua3/programs/miniconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<
conda activate iccad_challenge_2024

export CUDA_VISIBLE_DEVICES=0,1,2,3

ckpt_dir=/work/nvme/bcct/lad2025/finetuning/merged_llms/openrtlset-11k-4v6v/granite-8b/checkpoint-20480

export 'PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:64'
accelerate launch --num_processes 1 /work/nvme/bcct/lad2025/verilogeval-inferences/generate_qwen_granite.py \
    --checkpoint_dir $ckpt_dir \
    --model_type "qlora" \
    --base_model $ckpt_dir \
    --max_new_tokens 8192 \
    --temperature 0.7 \
    --desc_file /u/jinghua3/Documents/LLM4HWDesign_Starting_Toolkit/verilog-eval/descriptions/VerilogDescription_Machine.jsonl \
    --desc_key "detail_description" \
    --prompt_type "baseline" \
    --eval_file /u/jinghua3/Documents/LLM4HWDesign_Starting_Toolkit/verilog-eval/data/VerilogEval_Machine.jsonl \
    --output_file /work/nvme/bcct/lad2025/verilogeval-inferences/inference_results/openrtlset-11k-4v6v/granite-8b/ck-20480_data.jsonl \
    --fp16 \
    --sample_k 20 \
    --result_name Test \
    --batch_size 1 \
    --num_machines 1 \
    --num_processes 1
