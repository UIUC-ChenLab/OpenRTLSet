#!/bin/bash
#SBATCH --job-name="oic_0"
#SBATCH --output="log.%j.%N.out"
#SBATCH --mem=240g
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --ntasks-per-socket=1
#SBATCH --cpus-per-task=32
#SBATCH --gpus-per-node=4
#SBATCH --partition=ghx4
#SBATCH --account=becn-dtai-gh
#SBATCH --no-requeue
#SBATCH --time=6:00:00


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
conda activate gh200vllm

(   
    python3 -u /work/nvme/becn/lad2025/inference_scripts/gh200-utils/wait_for_vllm.py --vllm_host 127.0.0.1 --vllm_port 8000 && \
    (
    
        python3 -u /work/nvme/becn/lad2025/inference_scripts/DS_GH200_vllm_serial.py \
            --prompt_type VERILOG_AND_VITIS_CPP \
            --start_idx 0 --end_idx 46 \
            --src_path /work/nvme/becn/lad2025/datasets/openrtlset_2025-11-27/vitis/openrtlset_vitis_2025-12-04.jsonl \
            --save_path /work/nvme/becn/lad2025/ds_inference_results/openrtlset_2025-11-27/vitis_with_cpp_bf16/labelled_oic_0_46.jsonl & \
        wait || true
    ) && \
    python3 -u /work/nvme/becn/lad2025/inference_scripts/gh200-utils/run_vllm_shutdown.py) & (apptainer run --nv --bind /projects,/work,/u /work/nvme/becn/lad2025/env/apptainer_images/vllm_gh200_v0.10.0.sif bash /work/nvme/becn/lad2025/inference_scripts/gh200-utils/start_vllm.sh > /dev/null
)
