"""
LLM handler for the Code Documentation Generator.

This module wraps the Groq API (llama-3.1-8b-instant) and exposes
high-level methods to analyze and improve source code.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq
from groq._exceptions import GroqError  # type: ignore[import]


load_dotenv()


class LLMHandler:
    """
    High-level wrapper around Groq's chat completion API.

    Uses the `llama-3.1-8b-instant` model and expects the Groq API key
    to be available as the `GROQ_API_KEY` environment variable.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-8b-instant") -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Please add it to your environment or .env file."
            )

        self.client = Groq(api_key=self.api_key)
        self.model = model

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """
        Low-level helper to call the Groq chat completion API.

        Returns the raw text content of the first choice.
        Raises RuntimeError on API or network issues.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except GroqError as exc:  # noqa: PERF203 - explicit exception type is clearer
            raise RuntimeError(f"Groq API error: {exc}") from exc
        except Exception as exc:  # Fallback for unexpected errors
            raise RuntimeError(f"Unexpected error while calling Groq API: {exc}") from exc

        try:
            return response.choices[0].message.content  # type: ignore[no-any-return]
        except (AttributeError, IndexError, KeyError) as exc:
            raise RuntimeError(f"Unexpected response format from Groq API: {response}") from exc

    @staticmethod
    def _safe_json_loads(text: str) -> Any:
        """
        Try to parse JSON from `text`. If it fails, fall back to the raw text.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_response": text}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """
        Analyze the given code and return a structured summary.

        Returns a dict with the following keys:
        - description: What the code does
        - time_complexity: Big-O time complexity
        - space_complexity: Big-O space complexity
        - code_quality_score: Integer score 1–10
        - issues: List of issues or potential bugs
        - improvement_suggestions: List of suggestions
        """
        user_prompt = f"""
You are an expert {language} code reviewer.

Analyze the following {language} code and respond ONLY with valid JSON
matching this schema:
{{
  "description": "short explanation of what the code does",
  "time_complexity": "Big-O time complexity (e.g., O(n^2))",
  "space_complexity": "Big-O space complexity (e.g., O(n))",
  "code_quality_score": 7,
  "issues": ["issue 1", "issue 2"],
  "improvement_suggestions": ["suggestion 1", "suggestion 2"]
}}

Code:
```{language}
{code}
```
"""

        raw = self._chat(
            system_prompt="You are an expert software engineer and code reviewer.",
            user_prompt=user_prompt,
            temperature=0.2,
        )

        data = self._safe_json_loads(raw)

        # Ensure all keys exist with reasonable defaults
        return {
            "description": data.get("description") if isinstance(data, dict) else None,
            "time_complexity": data.get("time_complexity") if isinstance(data, dict) else None,
            "space_complexity": data.get("space_complexity") if isinstance(data, dict) else None,
            "code_quality_score": data.get("code_quality_score") if isinstance(data, dict) else None,
            "issues": data.get("issues") if isinstance(data, dict) else None,
            "improvement_suggestions": data.get("improvement_suggestions") if isinstance(data, dict) else None,
            "raw": raw,
        }

    def get_optimized_version(self, code: str, language: str) -> Dict[str, Any]:
        """
        Return an optimized version of the code and an explanation.

        Returns a dict with:
        - optimized_code: The improved code
        - explanation: Text explaining the changes and trade-offs
        """
        user_prompt = f"""
You are an expert {language} performance engineer.

Given the following {language} code, return ONLY valid JSON of the form:
{{
  "optimized_code": "code block here",
  "explanation": "what you changed and why"
}}

Code:
```{language}
{code}
```
"""

        raw = self._chat(
            system_prompt="You are an expert code optimizer focused on clarity and performance.",
            user_prompt=user_prompt,
            temperature=0.3,
        )

        data = self._safe_json_loads(raw)

        return {
            "optimized_code": data.get("optimized_code") if isinstance(data, dict) else None,
            "explanation": data.get("explanation") if isinstance(data, dict) else None,
            "raw": raw,
        }

    def get_alternative_approaches(self, code: str, language: str) -> Dict[str, Any]:
        """
        Return 2–3 alternative ways to solve the same problem.

        Returns a dict:
        - approaches: List of 2–3 approaches, each with:
            - name
            - description
            - time_complexity
            - when_to_use
        """
        user_prompt = f"""
You are an expert algorithms engineer.

Based on the following {language} code, infer the underlying problem
and propose 2–3 alternative solution approaches.

Respond ONLY with valid JSON of the form:
{{
  "approaches": [
    {{
      "name": "Descriptive name",
      "description": "Short explanation of the idea",
      "time_complexity": "Big-O time complexity",
      "when_to_use": "When this approach is preferable"
    }}
  ]
}}

Code:
```{language}
{code}
```
"""

        raw = self._chat(
            system_prompt="You are an expert problem solver and algorithms instructor.",
            user_prompt=user_prompt,
            temperature=0.5,
        )

        data = self._safe_json_loads(raw)
        approaches: List[Dict[str, Any]] = []

        if isinstance(data, dict) and isinstance(data.get("approaches"), list):
            for item in data["approaches"]:
                if isinstance(item, dict):
                    approaches.append(
                        {
                            "name": item.get("name"),
                            "description": item.get("description"),
                            "time_complexity": item.get("time_complexity"),
                            "when_to_use": item.get("when_to_use"),
                        }
                    )

        return {
            "approaches": approaches,
            "raw": raw,
        }


if __name__ == "__main__":
    """
    Simple manual test using a classic two_sum implementation.

    Run:
        python -m backend.llm_handler
    (from the project root, with a valid GROQ_API_KEY set).
    """

    sample_code = """
def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""

    handler = LLMHandler()

    print("=== analyze_code ===")
    analysis = handler.analyze_code(sample_code, "Python")
    print(json.dumps(analysis, indent=2))

    print("\n=== get_optimized_version ===")
    optimized = handler.get_optimized_version(sample_code, "Python")
    print(json.dumps(optimized, indent=2))

    print("\n=== get_alternative_approaches ===")
    alternatives = handler.get_alternative_approaches(sample_code, "Python")
    print(json.dumps(alternatives, indent=2))