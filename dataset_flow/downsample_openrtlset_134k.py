#!/usr/bin/env python3
"""
OpenRTLSet 131k Dataset Downsampling and Post-processing Script

Features:
1. Downsample three dataset files
2. Ensure 4v and 4cv sample the same records
3. Generate two output files: 4v+6v and 4cv+6v
4. Code cleaning and deduplication
5. Remove cpp_code field
6. Generate statistics report
"""

import json
import random
import re
import os
from datetime import datetime
from typing import Dict, List, Set, Optional

# ============================================================================
# Configuration Parameters
# ============================================================================

# Random seed to ensure reproducible results
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# Input file paths
INPUT_DIR = "/work/nvme/becn/lad2025/ds_inference_results/openrtlset_2025-11-27/post_labeling_2025-12-08"
INPUT_FILES = {
    "4v": os.path.join(INPUT_DIR, "openrtlset_131k_4v_2025-12-09.jsonl"),
    "4cv": os.path.join(INPUT_DIR, "openrtlset_131k_4cv_2025-12-09.jsonl"),  # 4cv has different NL labels than 4v, needs separate sampling
    "6v": os.path.join(INPUT_DIR, "openrtlset_131k_6v_2025-12-09.jsonl"),
}

# Output directory
OUTPUT_DIR = "/work/nvme/becn/lad2025/ds_inference_results/11k_our_Label"

# Sampling configuration - weighted sampling based on token length
# Short code has high sampling rate, long code has low sampling rate
# Note: 4v and 4cv use the same sampling configuration but need separate sampling (because NL labels differ)
# Total target: 11434 records (after deduplication)
# Ratio: cv:v = 40:60 (cv source from 4v/4cv, v source from 6v)
SAMPLING_CONFIG = {
    "4v": {  # 4v uses this configuration (cv source: 40%)
        "target_count": 5500,       # Target sampling count (increased to account for deduplication, ensure 11434 after dedup)
        "min_rate": 0.15,           # Minimum sampling rate for long code
        "max_rate": 0.90,           # Maximum sampling rate for short code
    },
    "4cv": {  # 4cv uses same configuration but samples separately (NL labels differ)
        "target_count": 5500,       # Target sampling count (increased to account for deduplication, ensure 11434 after dedup)
        "min_rate": 0.15,           # Minimum sampling rate for long code
        "max_rate": 0.90,           # Maximum sampling rate for short code
    },
    "6v": {  # v source: 60%
        "target_count": 8300,       # Target sampling count (increased to account for deduplication, ensure 11434 after dedup)
        "min_rate": 0.02,           # Minimum sampling rate for long code
        "max_rate": 0.12,           # Maximum sampling rate for short code
    }
}

# Total target count (after deduplication)
TARGET_TOTAL_COUNT = 11434

# cv:v target counts (exact values)
TARGET_CV_COUNT = 4458   # Exact count for 4cv portion
TARGET_V_COUNT = 6976    # Exact count for 6v portion (11434 - 4458 = 6976)

# Token length thresholds (character count) - for adjusting sampling weights
TOKEN_LENGTH_THRESHOLDS = {
    "short": 500,      # < 500 chars: short code, high sampling rate
    "medium": 2000,    # 500-2000 chars: medium code, medium sampling rate
    "long": 5000,      # 2000-5000 chars: long code, low sampling rate
    # > 5000 chars: very long code, lowest sampling rate
}

# Field filtering configuration
# Only cpp_code needs to be removed, all other fields are kept
REMOVE_CPP_CODE = True  # Whether to remove cpp_code field

# Whether to perform code deduplication
ENABLE_DEDUPLICATION = True


# ============================================================================
# Code Cleaning Functions (referenced from comp_in_4k.py and comp_open_source.py)
# ============================================================================

def clean_code(code: str) -> str:
    """
    Clean Verilog code for deduplication comparison
    
    Processing steps:
    1. Remove comments
    2. Remove preprocessor directives
    3. Remove compiler/vendor-specific pragmas and attributes
    4. Expand line continuation characters
    5. Remove parameter blocks
    6. Remove empty parentheses
    7. Normalize whitespace
    8. Remove spaces around punctuation
    """
    if not code:
        return ""
    
    # 1) Remove single-line comments
    code = re.sub(r'//.*', '', code)
    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

    # 2) Remove preprocessor directives
    code = re.sub(
        r'^\s*`(?:include|define|timescale|default_nettype|resetall)\b.*$',
        '', code, flags=re.MULTILINE
    )

    # 3) Remove compiler/vendor pragmas and attributes
    code = re.sub(r'^\s*//\s*synthesis.*$', '', code,
                  flags=re.IGNORECASE | re.MULTILINE)
    code = re.sub(r'\(\*\s*.*?\s*\*\)', '', code, flags=re.DOTALL)

    # 4) Expand line continuation characters
    code = code.replace('\\\n', ' ')

    # 5) Remove parameter blocks in instantiations
    code = re.sub(r'#\s*\([^)]*\)', '', code)

    # 6) Remove empty parentheses
    code = re.sub(r'\(\s*\)', '', code)

    # 7) Normalize whitespace - remove empty lines, strip each line
    lines = [ln.strip() for ln in code.splitlines() if ln.strip()]
    code = '\n'.join(lines)
    code = re.sub(r'\s+', ' ', code)

    # 8) Remove spaces around punctuation
    code = re.sub(r'\s*([\[\]\(\)\{\},;:=<>])\s*', r'\1', code)

    return code.strip()


# ============================================================================
# Token Length Calculation and Sampling Weight Functions
# ============================================================================

def estimate_token_length(record: Dict) -> int:
    """
    Estimate token length of a record (using character count of verilog_code)
    
    Args:
        record: Data record
    
    Returns:
        Estimated token length (character count)
    """
    verilog_code = record.get("verilog_code", "")
    return len(verilog_code)


def calculate_sampling_probability(token_length: int, min_rate: float, max_rate: float) -> float:
    """
    Calculate sampling probability based on token length
    Short code has high probability, long code has low probability
    
    Args:
        token_length: Token length (character count)
        min_rate: Minimum sampling rate
        max_rate: Maximum sampling rate
    
    Returns:
        Sampling probability
    """
    thresholds = TOKEN_LENGTH_THRESHOLDS
    
    if token_length < thresholds["short"]:
        # Short code: maximum sampling rate
        return max_rate
    elif token_length < thresholds["medium"]:
        # Medium-short code: linear interpolation (max_rate -> medium)
        ratio = (token_length - thresholds["short"]) / (thresholds["medium"] - thresholds["short"])
        mid_rate = (max_rate + min_rate) / 2
        return max_rate - ratio * (max_rate - mid_rate)
    elif token_length < thresholds["long"]:
        # Medium-long code: linear interpolation (medium -> min_rate)
        ratio = (token_length - thresholds["medium"]) / (thresholds["long"] - thresholds["medium"])
        mid_rate = (max_rate + min_rate) / 2
        return mid_rate - ratio * (mid_rate - min_rate)
    else:
        # Very long code: minimum sampling rate
        return min_rate


# ============================================================================
# Downsampling Functions - Weighted Sampling Based on Token Length
# ============================================================================

def downsample_jsonl_weighted(input_file: str, config: Dict, return_indices: bool = False) -> tuple[List[Dict], Dict, Optional[List[int]]]:
    """
    Perform weighted sampling from JSONL file based on token length
    Short code prioritized, long code has low sampling rate
    
    Args:
        input_file: Input JSONL file path
        config: Sampling configuration (contains target_count, min_rate, max_rate)
        return_indices: Whether to return sampling indices
    
    Returns:
        (List of sampled records, statistics dictionary, sampling indices list (if return_indices=True))
    """
    print(f"  Reading: {os.path.basename(input_file)}")
    
    # First pass: read all records and calculate token length
    all_records = []
    length_stats = {
        "short": 0,
        "medium": 0, 
        "long": 0,
        "very_long": 0
    }
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line)
                token_len = estimate_token_length(record)
                record['_token_length'] = token_len  # Temporary field
                all_records.append(record)
                
                # Statistics for length distribution
                if token_len < TOKEN_LENGTH_THRESHOLDS["short"]:
                    length_stats["short"] += 1
                elif token_len < TOKEN_LENGTH_THRESHOLDS["medium"]:
                    length_stats["medium"] += 1
                elif token_len < TOKEN_LENGTH_THRESHOLDS["long"]:
                    length_stats["long"] += 1
                else:
                    length_stats["very_long"] += 1
                    
            except json.JSONDecodeError as e:
                print(f"    Warning: Skipping invalid JSON line (line {line_num}): {e}")
                continue
    
    total_count = len(all_records)
    min_rate = config["min_rate"]
    max_rate = config["max_rate"]
    target_count = config["target_count"]
    
    print(f"  Original entries: {total_count}")
    print(f"  Length distribution: short({length_stats['short']}) | "
          f"medium({length_stats['medium']}) | "
          f"long({length_stats['long']}) | "
          f"very_long({length_stats['very_long']})")
    
    # Second pass: weighted sampling
    sampled = []
    sampled_indices = []  # Record sampled indices
    sampling_stats = {
        "short": {"total": 0, "sampled": 0},
        "medium": {"total": 0, "sampled": 0},
        "long": {"total": 0, "sampled": 0},
        "very_long": {"total": 0, "sampled": 0},
    }
    
    for idx, record in enumerate(all_records):
        token_len = record['_token_length']
        sampling_prob = calculate_sampling_probability(token_len, min_rate, max_rate)
        
        # Record statistics
        if token_len < TOKEN_LENGTH_THRESHOLDS["short"]:
            category = "short"
        elif token_len < TOKEN_LENGTH_THRESHOLDS["medium"]:
            category = "medium"
        elif token_len < TOKEN_LENGTH_THRESHOLDS["long"]:
            category = "long"
        else:
            category = "very_long"
        
        sampling_stats[category]["total"] += 1
        
        # Weighted random sampling
        if random.random() < sampling_prob:
            # Delete temporary field
            del record['_token_length']
            sampled.append(record)
            sampled_indices.append(idx)
            sampling_stats[category]["sampled"] += 1
        else:
            del record['_token_length']
    
    # If sampling count is insufficient, supplement from short code
    if len(sampled) < target_count:
        print(f"  Note: Initial sampling {len(sampled)} records, target {target_count} records, supplementing from short code...")
        # Create index-record pairs, sorted by token length
        indexed_records = [(idx, record) for idx, record in enumerate(all_records) if idx not in sampled_indices]
        indexed_records.sort(key=lambda x: estimate_token_length(x[1]))
        
        for idx, record in indexed_records:
            if len(sampled) >= target_count:
                break
            # Delete temporary field (if still exists)
            if '_token_length' in record:
                del record['_token_length']
            sampled.append(record)
            sampled_indices.append(idx)
    
    # If sampling count exceeds target, prioritize keeping short code
    if len(sampled) > target_count:
        print(f"  Note: Sampling {len(sampled)} records exceeds target {target_count} records, prioritizing short code...")
        # Create index-record pairs, sorted by token length
        indexed_sampled = list(zip(sampled_indices, sampled))
        indexed_sampled.sort(key=lambda x: estimate_token_length(x[1]))
        indexed_sampled = indexed_sampled[:target_count]
        sampled = [record for _, record in indexed_sampled]
        sampled_indices = [idx for idx, _ in indexed_sampled]
    
    print(f"  Sampling result: {len(sampled)} records")
    print(f"  Sampling by category: short({sampling_stats['short']['sampled']}/{sampling_stats['short']['total']}) | "
          f"medium({sampling_stats['medium']['sampled']}/{sampling_stats['medium']['total']}) | "
          f"long({sampling_stats['long']['sampled']}/{sampling_stats['long']['total']}) | "
          f"very_long({sampling_stats['very_long']['sampled']}/{sampling_stats['very_long']['total']})")
    
    stats_info = {
        "total_count": total_count,
        "sampled_count": len(sampled),
        "length_distribution": length_stats,
        "sampling_by_category": sampling_stats,
        "sampling_config": config
    }
    
    if return_indices:
        return sampled, stats_info, sampled_indices
    else:
        return sampled, stats_info, None


# ============================================================================
# Extract Records by Indices Function
# ============================================================================

def extract_records_by_indices(input_file: str, indices: List[int]) -> List[Dict]:
    """
    Extract corresponding records from JSONL file based on index list
    
    Args:
        input_file: Input JSONL file path
        indices: List of record indices to extract (maintains order)
    
    Returns:
        List of extracted records (in the order of indices)
    """
    print(f"  Extracting by indices: {os.path.basename(input_file)} ({len(indices)} indices)")
    
    # Convert indices to set for fast lookup, create index-to-record mapping
    indices_set = set(indices)
    index_to_record = {}
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            if idx in indices_set:
                try:
                    record = json.loads(line.strip())
                    index_to_record[idx] = record
                except json.JSONDecodeError as e:
                    print(f"    Warning: Skipping invalid JSON line (index {idx}): {e}")
                    continue
    
    # Extract records in original index order
    extracted = [index_to_record[idx] for idx in indices if idx in index_to_record]
    
    print(f"  Extraction result: {len(extracted)} records")
    return extracted


# ============================================================================
# Field Filtering Function
# ============================================================================

def filter_fields(records: List[Dict], file_type: str) -> List[Dict]:
    """
    Filter fields according to configuration
    Only remove cpp_code, keep all other fields
    
    Args:
        records: List of records
        file_type: File type (4cv, 4v, 6v)
    
    Returns:
        Filtered list of records
    """
    filtered = []
    
    for record in records:
        new_record = record.copy()
        
        # Remove cpp_code field (if exists)
        if REMOVE_CPP_CODE and "cpp_code" in new_record:
            del new_record["cpp_code"]
        
        filtered.append(new_record)
    
    return filtered


# ============================================================================
# Deduplication Function
# ============================================================================

def deduplicate_by_code(records: List[Dict]) -> tuple[List[Dict], int]:
    """
    Deduplicate based on cleaned verilog_code and repo_url
    Only consider duplicates when both verilog_code and repo_url are the same
    If verilog_code is the same but repo_url differs, keep both records
    
    Args:
        records: List of records
    
    Returns:
        (Deduplicated list of records, duplicate count)
    """
    seen_keys: Set[tuple] = set()  # Use (code, repo_url) as unique key
    deduplicated = []
    dup_count = 0
    
    for record in records:
        verilog_code = record.get("verilog_code", "")
        repo_url = record.get("Repo_url", "")  # Note: field name is Repo_url
        cleaned_code = clean_code(verilog_code)
        
        # Use (code, repo_url) as unique key
        unique_key = (cleaned_code, repo_url)
        
        if cleaned_code and unique_key not in seen_keys:
            seen_keys.add(unique_key)
            deduplicated.append(record)
        else:
            dup_count += 1
    
    return deduplicated, dup_count


# ============================================================================
# Output Function
# ============================================================================

def write_jsonl(records: List[Dict], output_file: str):
    """
    Write list of records to JSONL file
    
    Args:
        records: List of records
        output_file: Output file path
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"  Saved: {output_file} ({len(records)} records)")


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main processing workflow"""
    print("=" * 80)
    print("OpenRTLSet 131k Dataset Downsampling - Generate two files: 4v+6v and 4cv+6v")
    print("=" * 80)
    print(f"Total target: {TARGET_TOTAL_COUNT} records (after deduplication)")
    print(f"Target counts: cv source (4cv) = {TARGET_CV_COUNT} records | v source (6v) = {TARGET_V_COUNT} records | Total = {TARGET_TOTAL_COUNT} records")
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Code deduplication: {'Enabled' if ENABLE_DEDUPLICATION else 'Disabled'}")
    print(f"Sampling strategy: high probability for short code, low probability for long code")
    print(f"Token length thresholds: short<{TOKEN_LENGTH_THRESHOLDS['short']} | "
          f"medium<{TOKEN_LENGTH_THRESHOLDS['medium']} | "
          f"long<{TOKEN_LENGTH_THRESHOLDS['long']} | very_long>={TOKEN_LENGTH_THRESHOLDS['long']}")
    print(f"Note: 4v and 4cv use the same sampling indices (matched by index), but keep their respective NL labels")
    print()
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Statistics
    stats = {
        "timestamp": timestamp,
        "files": {}
    }
    
    # 1. Sample 4v, get sampling indices
    print(f"\nProcessing 4v (sampling and recording indices)")
    print("-" * 80)
    
    if not os.path.exists(INPUT_FILES["4v"]):
        print(f"  Error: File does not exist - {INPUT_FILES['4v']}")
        return
    
    config_4v = SAMPLING_CONFIG["4v"]
    sampled_4v, stats_4v, sampled_indices = downsample_jsonl_weighted(INPUT_FILES["4v"], config_4v, return_indices=True)
    sampled_4v = filter_fields(sampled_4v, "4v")
    
    stats["files"]["4v"] = {
        "input_file": os.path.basename(INPUT_FILES["4v"]),
        "sampling_stats": stats_4v,
        "sampled_count": len(sampled_4v),
    }
    
    # 2. Extract corresponding records from 4cv using 4v's sampling indices (preserve 4cv's NL labels)
    print(f"\nProcessing 4cv (using 4v's sampling indices)")
    print("-" * 80)
    
    if not os.path.exists(INPUT_FILES["4cv"]):
        print(f"  Error: File does not exist - {INPUT_FILES['4cv']}")
        return
    
    # Extract records from 4cv using 4v's sampling indices
    sampled_4cv = extract_records_by_indices(INPUT_FILES["4cv"], sampled_indices)
    sampled_4cv = filter_fields(sampled_4cv, "4cv")
    
    stats["files"]["4cv"] = {
        "input_file": os.path.basename(INPUT_FILES["4cv"]),
        "sampling_stats": stats_4v,  # Use 4v's statistics (because sampling logic is the same)
        "sampled_count": len(sampled_4cv),
        "note": "Extracted using 4v's sampling indices"
    }
    
    # 3. Sample 6v
    print(f"\nProcessing 6v")
    print("-" * 80)
    
    if not os.path.exists(INPUT_FILES["6v"]):
        print(f"  Error: File does not exist - {INPUT_FILES['6v']}")
        return
    
    config_6v = SAMPLING_CONFIG["6v"]
    sampled_6v, stats_6v, _ = downsample_jsonl_weighted(INPUT_FILES["6v"], config_6v)
    sampled_6v = filter_fields(sampled_6v, "6v")
    
    stats["files"]["6v"] = {
        "input_file": os.path.basename(INPUT_FILES["6v"]),
        "sampling_stats": stats_6v,
        "sampled_count": len(sampled_6v),
    }
    
    # 4. Create two merged files
    print("\n" + "=" * 80)
    print("Creating merged files")
    print("=" * 80)
    
    # Merge 1: 4v + 6v
    merged_4v_6v = sampled_4v + sampled_6v
    print(f"\n4v + 6v merge:")
    print(f"  4v: {len(sampled_4v)} records")
    print(f"  6v: {len(sampled_6v)} records")
    print(f"  Before merge: {len(merged_4v_6v)} records")
    
    if ENABLE_DEDUPLICATION:
        print("  Performing deduplication...")
        merged_4v_6v, dup_count_4v = deduplicate_by_code(merged_4v_6v)
        print(f"  Removed duplicates: {dup_count_4v} records")
        print(f"  After deduplication: {len(merged_4v_6v)} records")
        
        # Recalculate cv and v counts after deduplication
        # Use set to identify which are from 4v and which are from 6v
        sampled_4v_indices = {id(x) for x in sampled_4v}
        cv_count_after_dedup = sum(1 for x in merged_4v_6v if id(x) in sampled_4v_indices)
        v_count_after_dedup = len(merged_4v_6v) - cv_count_after_dedup
        
        print(f"  Ratio after deduplication: cv source {cv_count_after_dedup} records ({cv_count_after_dedup/len(merged_4v_6v)*100:.1f}%) | "
              f"v source {v_count_after_dedup} records ({v_count_after_dedup/len(merged_4v_6v)*100:.1f}%)")
        
        # Separate cv source and v source records
        cv_records = [x for x in merged_4v_6v if id(x) in sampled_4v_indices]
        v_records = [x for x in merged_4v_6v if id(x) not in sampled_4v_indices]
        
        # Check if adjustment to target count is needed while maintaining 4:6 ratio
        if len(merged_4v_6v) > TARGET_TOTAL_COUNT:
            print(f"  Adjusting to target count: {TARGET_TOTAL_COUNT} records (4cv: {TARGET_CV_COUNT} records, 6v: {TARGET_V_COUNT} records, prioritizing short code)")
            # Sort by token length
            cv_records.sort(key=lambda x: estimate_token_length(x))
            v_records.sort(key=lambda x: estimate_token_length(x))
            
            # Allocate by exact counts
            target_cv = TARGET_CV_COUNT  # 4458 records
            target_v = TARGET_V_COUNT     # 6976 records
            
            # If one source is insufficient, supplement from the other
            if len(cv_records) < target_cv:
                target_cv = len(cv_records)
                target_v = TARGET_TOTAL_COUNT - target_cv
            elif len(v_records) < target_v:
                target_v = len(v_records)
                target_cv = TARGET_TOTAL_COUNT - target_v
            
            # Select records
            merged_4v_6v = cv_records[:target_cv] + v_records[:target_v]
            print(f"  Final: {len(merged_4v_6v)} records (cv source: {target_cv} records, v source: {target_v} records)")
        elif len(merged_4v_6v) < TARGET_TOTAL_COUNT:
            print(f"  Warning: Count after deduplication ({len(merged_4v_6v)}) is less than target ({TARGET_TOTAL_COUNT})")
            print(f"  Suggest increasing sampling rate or checking input data")
            # Even if insufficient, try to maintain ratio
            target_cv = min(TARGET_CV_COUNT, len(cv_records))
            target_v = min(TARGET_V_COUNT, len(v_records))
            if target_cv + target_v < len(merged_4v_6v):
                # If proportional allocation results in fewer total, allocate by actual ratio
                ratio_cv = len(cv_records) / len(merged_4v_6v)
                target_cv = int(len(merged_4v_6v) * 0.4)
                target_v = len(merged_4v_6v) - target_cv
            merged_4v_6v = cv_records[:target_cv] + v_records[:target_v]
            print(f"  After proportional adjustment: {len(merged_4v_6v)} records (cv source: {target_cv} records, v source: {target_v} records)")
        
        # Recalculate final ratio
        sampled_4v_indices_final = {id(x) for x in sampled_4v}
        cv_count_final = sum(1 for x in merged_4v_6v if id(x) in sampled_4v_indices_final)
        v_count_final = len(merged_4v_6v) - cv_count_final
        
        stats["deduplication_4v6v"] = {
            "enabled": True,
            "duplicates_removed": dup_count_4v,
            "final_count": len(merged_4v_6v),
            "target_count": TARGET_TOTAL_COUNT,
            "cv_count": cv_count_final,
            "v_count": v_count_final
        }
    
    output_4v_6v = os.path.join(OUTPUT_DIR, f"openrtlset_4v6v_sampled_{timestamp}.jsonl")
    write_jsonl(merged_4v_6v, output_4v_6v)
    
    # Merge 2: 4cv + 6v (using separately sampled 4cv data)
    merged_4cv_6v = sampled_4cv + sampled_6v
    print(f"\n4cv + 6v merge:")
    print(f"  4cv: {len(sampled_4cv)} records")
    print(f"  6v: {len(sampled_6v)} records")
    print(f"  Before merge: {len(merged_4cv_6v)} records")
    
    if ENABLE_DEDUPLICATION:
        print("  Performing deduplication...")
        merged_4cv_6v, dup_count_4cv = deduplicate_by_code(merged_4cv_6v)
        print(f"  Removed duplicates: {dup_count_4cv} records")
        print(f"  After deduplication: {len(merged_4cv_6v)} records")
        
        # Recalculate cv and v counts after deduplication
        sampled_4cv_indices = {id(x) for x in sampled_4cv}
        cv_count_after_dedup = sum(1 for x in merged_4cv_6v if id(x) in sampled_4cv_indices)
        v_count_after_dedup = len(merged_4cv_6v) - cv_count_after_dedup
        
        print(f"  Ratio after deduplication: cv source {cv_count_after_dedup} records ({cv_count_after_dedup/len(merged_4cv_6v)*100:.1f}%) | "
              f"v source {v_count_after_dedup} records ({v_count_after_dedup/len(merged_4cv_6v)*100:.1f}%)")
        
        # Separate cv source and v source records
        cv_records = [x for x in merged_4cv_6v if id(x) in sampled_4cv_indices]
        v_records = [x for x in merged_4cv_6v if id(x) not in sampled_4cv_indices]
        
        # Check if adjustment to target count is needed while maintaining 4:6 ratio
        if len(merged_4cv_6v) > TARGET_TOTAL_COUNT:
            print(f"  Adjusting to target count: {TARGET_TOTAL_COUNT} records (4cv: {TARGET_CV_COUNT} records, 6v: {TARGET_V_COUNT} records, prioritizing short code)")
            # Sort by token length
            cv_records.sort(key=lambda x: estimate_token_length(x))
            v_records.sort(key=lambda x: estimate_token_length(x))
            
            # Allocate by exact counts
            target_cv = TARGET_CV_COUNT  # 4458 records
            target_v = TARGET_V_COUNT     # 6976 records
            
            # If one source is insufficient, supplement from the other
            if len(cv_records) < target_cv:
                target_cv = len(cv_records)
                target_v = TARGET_TOTAL_COUNT - target_cv
            elif len(v_records) < target_v:
                target_v = len(v_records)
                target_cv = TARGET_TOTAL_COUNT - target_v
            
            # Select records
            merged_4cv_6v = cv_records[:target_cv] + v_records[:target_v]
            print(f"  Final: {len(merged_4cv_6v)} records (cv source: {target_cv} records, v source: {target_v} records)")
        elif len(merged_4cv_6v) < TARGET_TOTAL_COUNT:
            print(f"  Warning: Count after deduplication ({len(merged_4cv_6v)}) is less than target ({TARGET_TOTAL_COUNT})")
            print(f"  Suggest increasing sampling rate or checking input data")
            # Even if insufficient, try to maintain ratio
            target_cv = min(TARGET_CV_COUNT, len(cv_records))
            target_v = min(TARGET_V_COUNT, len(v_records))
            if target_cv + target_v < len(merged_4cv_6v):
                # If proportional allocation results in fewer total, allocate by actual ratio
                ratio_cv = len(cv_records) / len(merged_4cv_6v)
                target_cv = int(len(merged_4cv_6v) * 0.4)
                target_v = len(merged_4cv_6v) - target_cv
            merged_4cv_6v = cv_records[:target_cv] + v_records[:target_v]
            print(f"  After proportional adjustment: {len(merged_4cv_6v)} records (cv source: {target_cv} records, v source: {target_v} records)")
        
        # Recalculate final ratio
        sampled_4cv_indices_final = {id(x) for x in sampled_4cv}
        cv_count_final = sum(1 for x in merged_4cv_6v if id(x) in sampled_4cv_indices_final)
        v_count_final = len(merged_4cv_6v) - cv_count_final
        
        stats["deduplication_4cv6v"] = {
            "enabled": True,
            "duplicates_removed": dup_count_4cv,
            "final_count": len(merged_4cv_6v),
            "target_count": TARGET_TOTAL_COUNT,
            "cv_count": cv_count_final,
            "v_count": v_count_final
        }
    
    output_4cv_6v = os.path.join(OUTPUT_DIR, f"openrtlset_4cv6v_sampled_{timestamp}.jsonl")
    write_jsonl(merged_4cv_6v, output_4cv_6v)
    
    # 4. Save statistics
    stats_file = os.path.join(OUTPUT_DIR, f"sampling_stats_{timestamp}.json")
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"\nStatistics saved: {stats_file}")
    
    # 5. Print final statistics
    print("\n" + "=" * 80)
    print("Processing complete!")
    print("=" * 80)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"\nOutput files:")
    print(f"  1. {os.path.basename(output_4v_6v)} ({len(merged_4v_6v)} records)")
    print(f"  2. {os.path.basename(output_4cv_6v)} ({len(merged_4cv_6v)} records)")
    
    print(f"\nSampling statistics by part:")
    for file_type in ["4v", "4cv", "6v"]:
        if file_type in stats["files"]:
            file_stats = stats["files"][file_type]
            total = file_stats['sampling_stats']['total_count']
            sampled = file_stats['sampled_count']
            rate = (sampled / total * 100) if total > 0 else 0
            print(f"  {file_type:4s}: {sampled:5d} records / {total:6d} total (sampling rate {rate:5.2f}%)")
    
    if ENABLE_DEDUPLICATION:
        # 4v+6v statistics
        print(f"\n4v+6v deduplication and ratio statistics:")
        print(f"  Before merge: {len(sampled_4v) + len(sampled_6v)} records")
        if "deduplication_4v6v" in stats:
            print(f"  Removed duplicates: {stats['deduplication_4v6v']['duplicates_removed']} records")
            print(f"  Final: {len(merged_4v_6v)} records")
            print(f"  Target: {TARGET_TOTAL_COUNT} records")
            
            diff = len(merged_4v_6v) - TARGET_TOTAL_COUNT
            if diff > 0:
                print(f"  ✓ Target reached (adjusted {diff} records)")
            elif diff == 0:
                print(f"  ✓ Perfectly reached target!")
            else:
                print(f"  ⚠ {abs(diff)} records short of target")
            
            cv_count = stats['deduplication_4v6v']['cv_count']
            v_count = stats['deduplication_4v6v']['v_count']
            cv_ratio = cv_count / len(merged_4v_6v) * 100 if len(merged_4v_6v) > 0 else 0
            v_ratio = v_count / len(merged_4v_6v) * 100 if len(merged_4v_6v) > 0 else 0
            
            print(f"\n  Final ratio:")
            print(f"    cv source (4v): {cv_count:5d} records ({cv_ratio:5.1f}%) [target: {TARGET_CV_COUNT} records]")
            print(f"    v source (6v):  {v_count:5d} records ({v_ratio:5.1f}%) [target: {TARGET_V_COUNT} records]")
        
        # 4cv+6v statistics
        print(f"\n4cv+6v deduplication and ratio statistics:")
        print(f"  Before merge: {len(sampled_4cv) + len(sampled_6v)} records")
        if "deduplication_4cv6v" in stats:
            print(f"  Removed duplicates: {stats['deduplication_4cv6v']['duplicates_removed']} records")
            print(f"  Final: {len(merged_4cv_6v)} records")
            print(f"  Target: {TARGET_TOTAL_COUNT} records")
            
            diff = len(merged_4cv_6v) - TARGET_TOTAL_COUNT
            if diff > 0:
                print(f"  ✓ Target reached (adjusted {diff} records)")
            elif diff == 0:
                print(f"  ✓ Perfectly reached target!")
            else:
                print(f"  ⚠ {abs(diff)} records short of target")
            
            cv_count = stats['deduplication_4cv6v']['cv_count']
            v_count = stats['deduplication_4cv6v']['v_count']
            cv_ratio = cv_count / len(merged_4cv_6v) * 100 if len(merged_4cv_6v) > 0 else 0
            v_ratio = v_count / len(merged_4cv_6v) * 100 if len(merged_4cv_6v) > 0 else 0
            
            print(f"\n  Final ratio:")
            print(f"    cv source (4cv): {cv_count:5d} records ({cv_ratio:5.1f}%) [target: {TARGET_CV_COUNT} records]")
            print(f"    v source (6v):   {v_count:5d} records ({v_ratio:5.1f}%) [target: {TARGET_V_COUNT} records]")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

