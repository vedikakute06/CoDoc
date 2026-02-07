"""
GitHub repository analyzer.

This module combines:
- `GitHubFetcher` to pull repository metadata and important files
- `LLMHandler` to generate high-level documentation for the project

The main entry point is `GitHubAnalyzer.analyze_repo(github_url)`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

from backend.github_fetcher import GitHubFetcher
from backend.llm_handler import LLMHandler


load_dotenv()


class GitHubAnalyzer:
    """
    High-level orchestrator that:
    - Fetches repository information and important files
    - Uses LLMHandler to generate project-level documentation pieces
    """

    def __init__(self, llm_handler: LLMHandler | None = None, fetcher: GitHubFetcher | None = None) -> None:
        self.llm = llm_handler or LLMHandler()
        self.fetcher = fetcher or GitHubFetcher()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_repo_context(self, github_url: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
        """
        Fetch repo info, important files, and (if available) README content.

        Returns:
        - repo_info (dict)
        - important_files (list of dicts)
        - readme_text (str, may be empty)
        """
        owner, repo = self.fetcher.parse_url(github_url)
        repo_info = self.fetcher.get_repo_info(owner, repo)
        important_files = self.fetcher.get_important_files(owner, repo)

        readme_text = ""
        # Try to load README.* if present
        for item in important_files:
            path = item["path"]
            filename = path.split("/")[-1].lower()
            if filename.startswith("readme") and item.get("download_url"):
                try:
                    readme_text = self.fetcher.get_file_content(item["download_url"])
                except Exception:
                    readme_text = ""
                break

        return repo_info, important_files, readme_text

    def _llm_section(self, title: str, instruction: str, context: str) -> str:
        """
        Call the LLM to generate a documentation section.

        Uses the same underlying model as `LLMHandler`.
        """
        user_prompt = f"""
You are helping to document an open-source GitHub project.

SECTION: {title}

INSTRUCTION:
{instruction}

CONTEXT (repo info and important files):
{context}

Write the answer in concise, well-structured Markdown.
"""

        # Reuse LLMHandler's internal chat helper for consistency.
        return self.llm._chat(  # type: ignore[attr-defined]
            system_prompt="You are an expert technical writer and software engineer.",
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=1500,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze_repo(self, github_url: str, verbosity: str = "concise") -> Dict[str, Any]:
        """
        Analyze a GitHub repository and generate high-level documentation.

        Makes 5 sequential LLM calls:
        1. Project overview and key features
        2. Tech stack detection
        3. Installation instructions
        4. Usage examples
        5. Contributing guidelines

        Returns:
        {
          "repo_info": {...},
          "analysis": {
             "overview": "...",
             "tech_stack": "...",
             "installation": "...",
             "usage": "...",
             "contributing": "..."
          }
        }
        """
        repo_info, important_files, readme_text = self._get_repo_context(github_url)

        context = {
            "repo_info": repo_info,
            "important_files": important_files,
            "readme_excerpt": readme_text[:4000],  # keep context size reasonable
        }
        context_str = json.dumps(context, indent=2)

        print("[1/5] Generating project overview and key features...")
        if verbosity == "detailed":
            overview_instr = (
                "Provide a clear, high-level description of what this project does and its main "
                "features. Include useful background, motivations, and any notable design choices. "
                "Write in 3-6 short paragraphs suitable for a project's README."
            )
        else:
            overview_instr = (
                "Provide a clear, high-level description of what this project does and "
                "its main features. Keep this concise (150 words max). Use 3–5 bullet points "
                "or short paragraphs that a developer can quickly scan to decide whether "
                "to use or contribute to this repository."
            )

        overview = self._llm_section(
            title="Project Overview and Features",
            instruction=overview_instr,
            context=context_str,
        )

        print("[2/5] Detecting tech stack...")
        if verbosity == "detailed":
            tech_instr = (
                "Identify the main technologies, languages, frameworks, and tools used in this "
                "repository. Provide a categorized list (backend, frontend, database, tooling) with "
                "brief notes about where they are used in the project."
            )
        else:
            tech_instr = (
                "Identify the main technologies, languages, frameworks, and tools used "
                "in this repository. Present them as a short, categorized bullet list (backend, "
                "frontend, database, tooling). Limit to the top 6–10 items overall."
            )

        tech_stack = self._llm_section(
            title="Tech Stack",
            instruction=tech_instr,
            context=context_str,
        )

        print("[3/5] Drafting installation instructions...")
        if verbosity == "detailed":
            install_instr = (
                "Create a step-by-step installation and setup guide including prerequisites, commands, "
                "environment variables, and common troubleshooting tips. Use numbered steps and include "
                "examples where helpful."
            )
        else:
            install_instr = (
                "Provide concise installation steps that a developer can copy-paste. Use a small "
                "numbered list (3–6 steps) with commands and any obvious prerequisites. If you must "
                "assume environment details, mark them as assumptions and keep the guidance short."
            )

        installation = self._llm_section(
            title="Installation",
            instruction=install_instr,
            context=context_str,
        )

        print("[4/5] Creating usage examples...")
        if verbosity == "detailed":
            usage_instr = (
                "Provide usage instructions with multiple examples and brief explanations. Include commands, "
                "code snippets, or API calls as appropriate and show expected outputs where helpful."
            )
        else:
            usage_instr = (
                "Give 1–3 short, concrete usage examples (commands, code snippets, or API calls). "
                "Keep examples minimal and directly runnable; avoid long tutorials. Limit the whole "
                "section to ~200 words."
            )

        usage = self._llm_section(
            title="Usage",
            instruction=usage_instr,
            context=context_str,
        )

        print("[5/5] Summarizing contributing guidelines...")
        if verbosity == "detailed":
            contrib_instr = (
                "Summarize how someone should contribute to this project, including filing issues, creating PRs, "
                "code style, testing, and the review process. Include links to relevant files if present."
            )
        else:
            contrib_instr = (
                "Provide a short contributing summary (4–6 bullet points): how to file issues, "
                "create PRs, coding style expectations, and where to find further guidelines. If "
                "the repo already contains CONTRIBUTING.md, condense it to a 3-line summary."
            )

        contributing = self._llm_section(
            title="Contributing",
            instruction=contrib_instr,
            context=context_str,
        )

        return {
            "repo_info": repo_info,
            "analysis": {
                "overview": overview,
                "tech_stack": tech_stack,
                "installation": installation,
                "usage": usage,
                "contributing": contributing,
            },
        }


if __name__ == "__main__":
    """
    Simple manual test.

    Run from project root:
        python -m backend.analyzers.github_analyzer
    """

    # You can change this to any public GitHub repository you want to test.
    TEST_REPO_URL = "https://github.com/octocat/Hello-World"

    analyzer = GitHubAnalyzer()
    print(f"Analyzing GitHub repository: {TEST_REPO_URL}")

    result = analyzer.analyze_repo(TEST_REPO_URL)

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "github_repo_analysis.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Analysis written to {output_path}")

