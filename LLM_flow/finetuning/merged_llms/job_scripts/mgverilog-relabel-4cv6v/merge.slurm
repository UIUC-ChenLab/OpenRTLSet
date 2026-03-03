#!/bin/bash
#SBATCH --job-name="merge4v6vint4"
#SBATCH --output="log.%j.%N.out"
#SBATCH --partition=ghx4-interactive
#SBATCH --mem=400G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=32   # spread out to use 1 core per numa, set to 64 if tasks is 1
#SBATCH --gpus-per-node=1
#SBATCH --account=becn-dtai-gh  # <- match to a "Project" returned by the "accounts" command
#SBATCH --no-requeue
#SBATCH -t 1:00:00

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

python -u /work/nvme/bcct/lad2025/finetuning/merged_llms/merge-llm-job.py \
    --peft_src_dir /work/nvme/bcct/lad2025/finetuning/llm_ckpts/mgverilog-relabel-4cv6v \
    --llm_target_dir /work/nvme/bcct/lad2025/finetuning/merged_llms/mgverilog-relabel-4cv6v