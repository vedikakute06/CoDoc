"""
LeetCode-style solution analyzer.

This module provides a thin wrapper around `LLMHandler` to:
- Analyze a solution
- Get an optimized version
- Get alternative approaches

Results are packaged into a single dictionary and can be saved as JSON.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

from backend.llm_handler import LLMHandler


@dataclass
class LeetcodeAnalysisResult:
    """Container for LeetCode analysis results."""

    original_code: str
    language: str
    analysis: Dict[str, Any]
    optimized_version: Dict[str, Any]
    alternatives: Dict[str, Any]


class LeetcodeAnalyzer:
    """
    High-level helper that orchestrates multiple LLM calls for a single solution.
    """

    def __init__(self, llm_handler: LLMHandler | None = None) -> None:
        self.llm = llm_handler or LLMHandler()

    def analyze_solution(self, code: str, language: str) -> Dict[str, Any]:
        """
        Analyze a LeetCode-style solution using three sequential LLM calls.

        Returns a dict with:
        - original_code
        - language
        - analysis
        - optimized_version
        - alternatives
        """
        print("[1/3] Running detailed analysis...")
        analysis = self.llm.analyze_code(code, language)

        print("[2/3] Getting optimized version...")
        optimized = self.llm.get_optimized_version(code, language)

        print("[3/3] Collecting alternative approaches...")
        alternatives = self.llm.get_alternative_approaches(code, language)

        result = LeetcodeAnalysisResult(
            original_code=code,
            language=language,
            analysis=analysis,
            optimized_version=optimized,
            alternatives=alternatives,
        )

        # Return as a plain dict for easier downstream use / JSON-ification
        return asdict(result)

    def save_analysis(self, result: Dict[str, Any], filename: str) -> Path:
        """
        Save the analysis result to a JSON file.

        `filename` can be a bare name (e.g., "two_sum_analysis.json")
        or a relative/absolute path. Parent directories are created
        automatically if needed.

        Returns the `Path` to the written file.
        """
        path = Path(filename)
        if not path.suffix:
            path = path.with_suffix(".json")

        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"Analysis saved to: {path}")
        return path


if __name__ == "__main__":
    """
    Simple manual test.

    Run (from project root):
        python -m backend.analyzers.leetcode_analyzer
    """

    sample_code = """
def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""

    analyzer = LeetcodeAnalyzer()
    print("Starting LeetCode solution analysis for `two_sum`...")

    result_dict = analyzer.analyze_solution(sample_code, "Python")

    # Save into the default output directory for convenience
    output_path = Path("output") / "two_sum_analysis.json"
    analyzer.save_analysis(result_dict, str(output_path))

    print("Done.")

