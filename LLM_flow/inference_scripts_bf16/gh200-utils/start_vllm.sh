#!/bin/bash

# 1.7x
vllm serve /projects/becn/llm_models/deepseek-r1-70b-hf --api-key token-abc123 --reasoning-parser deepseek_r1 --rope-scaling '{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}' --max-model-len 51200 --tensor-parallel-size 4 --gpu_memory_utilization 0.9