"""
Unit tests for Phase 5: Benchmark Comparator.
"""

import os
import sys
_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
from evaluation.benchmark_comparison import BenchmarkComparator


def test_benchmark_comparator_smoke(tmp_path):
    out_csv = str(tmp_path / "test_comp.csv")
    comp = BenchmarkComparator(output_csv=out_csv)

    records = comp.run_benchmark(num_episodes=2, test_seeds=[101, 102])

    assert len(records) == 6  # 2 seeds * 3 policies
    assert os.path.exists(out_csv)

    # Scripted baseline should have at least 1 success
    baseline_records = [r for r in records if r["policy_name"] == "Scripted_Baseline"]
    assert any(r["task_success"] for r in baseline_records)
