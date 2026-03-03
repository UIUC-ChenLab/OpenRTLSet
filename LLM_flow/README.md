# LLM_flow:
Note: Before running scripts in `LLM_flow` folder, please look carefully and change the file paths in scripts (LLM paths, dataset paths, etc.) to your corresponding settings.
All SLURM scripts can be executed by running `sbatch XXX.slurm` on a SLURM GPU cluster, but you need to change your GPU account settings (GPU amount, GPU types, etc.) according to your SLURM cluster.
- `conda_env`: conda environment yaml files for running the GPU-accelerated LLM inference & finetuning scripts in other sub-folders of `LLM_flow`.

  For example, to install conda environment using existing `Anaconda` or `Miniconda` executable on GH200 hardware nodes, run (other node hardware like A40 GPU nodes are also provided in separate `.yml` file):
  ```
  conda create -f LLM_flow/conda_env/gh200-llm-env.yml
  conda activate gh200env
  ```
- `inference_scripts`: Python and SLURM scripts for running the Verilog module labeling jobs. `deepseek_inference_verilog_*.py` are the main Python scripts. Multiple folders containing customized SLURM jobs are provided for running Python scripts in various configurations for labeling various types of datasets. Input datasets are Code only (Verilog, optionally with C++), output datasets are Code + English descriptions.

  For example, to run a DeepSeek labeling job for one subset of OpenRTLSet 131k (GitHub Downloaded Verilog Code with no Verilator C++ pairing code during labeling, first 500 modules), run:
  ```
  cd LLM_flow/inference_scripts/openrtlset-131k/github_nocpp/0
  sbatch job_0_499.slurm
  ```
  To generate Verilog code with closed-source LLMs (OpenAI GPT, Anthropic Claude) and evaluate Pass@k:
  ```
  cd LLM_flow/verilogeval-inferences/close-source-llms-jobs

  # 1) Generate completions (update paths & set OPENAI_API_KEY/CLAUDE_API_KEY)
  python comm_inference.py \
    --desc_file ../verilog-eval/descriptions/VerilogDescription_Human.jsonl \
    --eval_file ../verilog-eval/data/VerilogEval_Human.jsonl \
    --sample_k 10 \
    --max_new_tokens 2048

  # 2) Compute Pass@k with VerilogEval
  python eval_verilog_jsonl.py \
    --gen_file ./data/gen_gpt_o3_mini_0.7_10_2048.jsonl \
    --problem_file ../verilog-eval/data/VerilogEval_Human.jsonl \
    --k [1,5,10]
  ```
  Note: a similar set of scripts for DeepSeek R1 70B LLM-based dataset labeling with vLLM on GH200 (16-bit full precision) is provided in `inference_scripts_bf16` folder. These scripts are in Beta, please use at your own risk. The corrsponding OpenAI API client-side conda environment for these Beta scripts can be found at `conda_env/gh200vllm-env.yaml`. You also need to select a arm64 vLLM docker image to run this flow (we selected an image from dockerhub and converted it into an apptainer image in our script because our slurm cluster only has apptainer).
- `finetuning` :
   - `gen_token_dataset_scripts` : Given the `.jsonl` datasets as results of running scripts in `LLM_flow/inference_scripts`, convert dataset from text format to LLM-specific tokenized dataset format.
 
     For example, to run tokenized dataset generation for downsampled 11k OpenRTLSet (labeled in Verilog & C++), run:
     ```
     cd LLM_flow/finetuning/gen_token_dataset_scripts/openrtlset-11k-4cv6v
     python -u gen_tokenized_dataset.py
     ``` 
   - `job_scripts` : Run DeepSpeed multi-GPU LLM PEFT LoRA finetuning in various configurations for various types of datasets.

     For example, to run Qwen 2.5 Code 32B LLM finetuning on 131k OpenRTLSet, run:
     ```
     cd LLM_flow/finetuning/job_scripts/openrtlset-131k/qwen2.5-32b
     sbatch run_ft_qwen2.5-32b.slurm
     ```
   - `merged_llms` : Run Python/SLURM scripts to merge LLMs from PEFT LoRA checkpoints to full LLMs.
 
     For example, to merge all LLMs finetuned on the relabeled MG-Verilog (Verilog only settings), run:
     ```
     cd LLM_flow/finetuning/merged_llms/job_scripts/mgverilog-relabel-4v6v
     sbatch merge.slurm
     ```
- `verilogeval-inferences` : Run VerilogEval (both Machine and Human) using the merged full LLMs finetuned using scripts in `LLM_flow/finetuning` and get pass@k results.

  For example, to evaluate Granite Code 8B LLM finetuned 10k steps on downsampled 11k OpenRTLSet (Verilog-only) on VerilogEval-Machine Benchmark, run:
  ```
  cd LLM_flow/verilogeval-inferences/job_scripts/openrtlset-11k-4v6v/granite-8b/checkpoint-10240
  sbatch verilogeval_inference.slurm
  ```
