import argparse
import ast
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
VERILOG_EVAL_DIR = SCRIPT_DIR / "verilog-eval"
sys.path.append(str(VERILOG_EVAL_DIR))


def parse_k_values(raw_k: str) -> list[int]:
    """Parse k from either '[1,5,10]' or '1,5,10'."""
    try:
        parsed = ast.literal_eval(raw_k)
        if isinstance(parsed, (list, tuple)):
            return [int(x) for x in parsed]
    except (SyntaxError, ValueError):
        pass
    return [int(x.strip()) for x in raw_k.split(",") if x.strip()]


def evaluate_generations(gen_file: str, problem_file: str, k: list[int]) -> None:
    """Evaluate functional correctness of generated Verilog code."""
    try:
        from verilog_eval.evaluation import evaluate_functional_correctness
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Cannot import 'verilog_eval'. Make sure 'verilog-eval' is present under "
            f"{VERILOG_EVAL_DIR}."
        ) from exc

    results = evaluate_functional_correctness(
        gen_file,
        problem_file=problem_file,
        k=k,
    )
    print("\nEvaluation Results:")
    for k_value, score in results.items():
        print(f"Pass@{k_value}: {score:.3f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate generated Verilog code with VerilogEval."
    )
    parser.add_argument(
        "--gen_file",
        required=True,
        help="Path to generated Verilog JSONL file.",
    )
    parser.add_argument(
        "--problem_file",
        default=str(VERILOG_EVAL_DIR / "data" / "VerilogEval_Human.jsonl"),
        help="Path to VerilogEval problem file.",
    )
    parser.add_argument(
        "--k",
        default="[1,5,10]",
        help="Pass@k values, e.g. '[1,5,10]' or '1,5,10'.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    gen_file = Path(args.gen_file)
    problem_file = Path(args.problem_file)

    if not gen_file.is_file():
        raise FileNotFoundError(f"Generated file not found: {gen_file}")
    if not problem_file.is_file():
        raise FileNotFoundError(f"Problem file not found: {problem_file}")

    evaluate_generations(
        gen_file=str(gen_file),
        problem_file=str(problem_file),
        k=parse_k_values(args.k),
    )
