#!/bin/bash
#SBATCH --job-name="3EV_G34ft"
#SBATCH --output="log.%j.%N.out"
#SBATCH --partition=ghx4
#SBATCH --mem=650G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=64   # spread out to use 1 core per numa, set to 64 if tasks is 1
#SBATCH --gpus-per-node=0
#SBATCH --account=becn-dtai-gh  # <- match to a "Project" returned by the "accounts" command
#SBATCH --no-requeue
#SBATCH -t 48:00:00

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
python -u /work/nvme/bcct/lad2025/finetuning/gen_token_dataset_scripts/openrtlset-131k/gen_tokenized_dataset.py
