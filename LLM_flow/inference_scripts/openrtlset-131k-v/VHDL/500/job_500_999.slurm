#!/bin/bash
#SBATCH --job-name="105kH_500"
#SBATCH --output="log.%j.%N.out"
#SBATCH --partition=gpuA40x4
#SBATCH --mem=48G
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1  # could be 1 for py-torch
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
export 'PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:64'

accelerate launch --num_processes 1 /work/nvme/bcct/lad2025/inference_scripts/deepseek_inference_verilog_only.py \
    --start_idx 500 --end_idx 999 \
    --src_path /work/nvme/bcct/lad2025/datasets/Complete_dataset/VHDL.jsonl \
    --save_path /work/nvme/bcct/lad2025/ds_inference_results/Complete_dataset-v/VHDL/labeled_105k_VHDL_vonly_500_999.jsonl
