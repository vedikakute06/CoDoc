"""
Gradio frontend for the Code Documentation Generator.

Provides two main tools:
- Code Analyzer
- GitHub README Generator
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr

from backend.analyzers.leetcode_analyzer import LeetcodeAnalyzer
from backend.analyzers.github_analyzer import GitHubAnalyzer
from backend.doc_generator import DocGenerator


doc_generator = DocGenerator()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def _load_file_content(file_obj: Any) -> str:
    """Read uploaded file content as text, if provided."""
    if not file_obj:
        return ""
    try:
        # Gradio's File component provides an object with a `.name` attribute.
        path = Path(getattr(file_obj, "name", str(file_obj)))
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _detect_language_from_filename(path: Path) -> Optional[str]:
    """Best-effort language detection from file extension."""
    ext = path.suffix.lower()
    mapping = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".java": "Java",
        ".cpp": "C++",
        ".cc": "C++",
        ".cxx": "C++",
        ".go": "Go",
    }
    return mapping.get(ext)


def _validate_github_url(url: str) -> Tuple[bool, str]:
    """Return (is_valid, message)."""
    if not url:
        return False, "Please enter a GitHub repository URL."
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or "github.com" not in (parsed.netloc or ""):
        return False, "URL must start with https://github.com/owner/repo"
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return False, "GitHub URL must include both owner and repository, e.g. https://github.com/octocat/Hello-World"
    return True, ""


# ------------------------------- Code tab logic --------------------------------
def analyze_code_solution(
    code: str,
    language: str,
    file: Any,
    progress: gr.Progress = gr.Progress(track_tqdm=True),
) -> tuple[str, str, str, Dict[str, Any], str]:
    """
    Run the Code analyzer and generate a DOCX report.

    Returns:
    - analysis_markdown
    - optimized_markdown
    - alternatives_markdown
    - raw_analysis_dict (for state)
    - docx_path (for download)
    """
    try:
        progress(0.05, desc="Validating input...")

        if file is not None:
            file_code = _load_file_content(file)
            if file_code.strip():
                code_to_use = file_code
            else:
                code_to_use = code
        else:
            code_to_use = code

        if not code_to_use.strip():
            raise ValueError("Please provide code in the text area or upload a file.")

        # Instantiate analyzer only when needed so we can surface API-key errors nicely.
        try:
            analyzer = LeetcodeAnalyzer()
        except RuntimeError as key_err:
            gr.Warning(
                f"Code analysis is not configured. Please check your API keys (.env): {key_err}"
            )
            return "", "", "", {}, ""

        gr.Info("Running Code analysis...")
        progress(0.2, desc="Step 1/3: Analyzing code...")

        analysis_dict = analyzer.analyze_solution(code_to_use, language)

        # Build human-friendly markdown for display
        analysis = analysis_dict.get("analysis", {}) or {}
        optimized = analysis_dict.get("optimized_version", {}) or {}
        alternatives = analysis_dict.get("alternatives", {}) or {}

        desc = analysis.get("description") or "N/A"
        tc = analysis.get("time_complexity") or "N/A"
        sc = analysis.get("space_complexity") or "N/A"
        score = analysis.get("code_quality_score")
        issues = analysis.get("issues") or []
        suggestions = analysis.get("improvement_suggestions") or []

        analysis_md_lines = [
            "### What the code does",
            "",
            str(desc),
            "",
            "### Complexity",
            "",
            f"- **Time Complexity**: {tc}",
            f"- **Space Complexity**: {sc}",
            "",
            "### Code Quality",
            "",
            f"- **Score (1–10)**: {score if score is not None else 'N/A'}",
            "",
            "### Issues / Potential Bugs",
            "",
        ]
        if issues:
            analysis_md_lines.extend([f"- {i}" for i in issues])
        else:
            analysis_md_lines.append("No major issues identified or not provided.")

        analysis_md_lines.extend(
            [
                "",
                "### Improvement Suggestions",
                "",
            ]
        )
        if suggestions:
            analysis_md_lines.extend([f"- {s}" for s in suggestions])
        else:
            analysis_md_lines.append("No specific suggestions provided.")

        analysis_md = "\n".join(analysis_md_lines)

        progress(0.6, desc="Step 2/3: Preparing optimized code...")

        # Optimized version
        opt_code_raw = optimized.get("optimized_code") or optimized.get("raw") or ""
        # Extract code string from dict if needed
        if isinstance(opt_code_raw, dict):
            opt_code = opt_code_raw.get("code") or opt_code_raw.get("content") or str(opt_code_raw)
        else:
            opt_code = str(opt_code_raw)
        
        opt_explanation = optimized.get("explanation") or ""
        optimized_md_lines = ["### Optimized Code", ""]
        if opt_code and opt_code != "{}":
            optimized_md_lines.append("```")
            optimized_md_lines.append(opt_code.strip())
            optimized_md_lines.append("```")
        else:
            optimized_md_lines.append("_No optimized version provided._")

        if opt_explanation:
            optimized_md_lines.extend(["", "### Explanation", "", str(opt_explanation)])

        optimized_md = "\n".join(optimized_md_lines)

        # Alternatives
        approaches = alternatives.get("approaches") or []
        alternatives_md_lines = ["### Alternative Approaches", ""]
        if approaches:
            for idx, approach in enumerate(approaches, start=1):
                name = approach.get("name") or f"Approach {idx}"
                alternatives_md_lines.extend(
                    [
                        f"#### {name}",
                        "",
                        f"- **Description**: {approach.get('description') or 'N/A'}",
                        f"- **Time Complexity**: {approach.get('time_complexity') or 'N/A'}",
                        f"- **When to Use**: {approach.get('when_to_use') or 'N/A'}",
                        "",
                    ]
                )
        else:
            alternatives_md_lines.append("_No alternative approaches provided._")

        alternatives_md = "\n".join(alternatives_md_lines)

        progress(0.85, desc="Step 3/3: Generating DOCX report...")

        # Ensure output directory exists and overwrite the previous report
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = doc_generator.generate_leetcode_report(
            analysis_dict, str(output_dir / "leetcode_report.docx")
        )

        progress(1.0, desc="Done")
        gr.Success("Code analysis complete.")
        return analysis_md, optimized_md, alternatives_md, analysis_dict, str(report_path)

    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        gr.Warning(f"Error during Code analysis: {exc}")
        return "", "", "", {}, ""


# --------------------------- GitHub tab logic -------------------------------
def analyze_github_repo(
    github_url: str,
    verbosity: str = "Concise",
    progress: gr.Progress = gr.Progress(track_tqdm=True),
) -> tuple[str, str, str, str, Dict[str, Any], str]:
    """
    Analyze a GitHub repository and generate a README.

    Returns:
    - repo_stats_markdown
    - overview_markdown
    - readme_preview_markdown
    - raw_readme_path (for download)
    - raw_analysis_dict (for state)
    - repo_name (for display)  # not strictly needed but can be useful
    """
    try:
        url = github_url.strip()
        is_valid, msg = _validate_github_url(url)
        if not is_valid:
            raise ValueError(msg)

        # Instantiate analyzer lazily to handle API key problems nicely.
        try:
            analyzer = GitHubAnalyzer()
        except RuntimeError as key_err:
            gr.Warning(
                f"GitHub analysis is not configured. Please check your API keys (.env): {key_err}"
            )
            return "", "", "", "", {}, ""

        gr.Info("Analyzing GitHub repository...")
        progress(0.15, desc="Step 1/5: Fetching repository metadata...")

        # Pass verbosity choice to analyzer (convert UI label to lowercase key)
        verbosity_key = (verbosity or "Concise").strip().lower()
        result = analyzer.analyze_repo(url, verbosity=verbosity_key)
        repo_info = result.get("repo_info", {}) or {}
        analysis = result.get("analysis", {}) or {}

        # Repo stats
        name = repo_info.get("name", "Unknown Repo")
        description = repo_info.get("description", "") or ""
        stars = repo_info.get("stars", 0)
        forks = repo_info.get("forks", 0)
        language = repo_info.get("language") or "Unknown"
        topics = repo_info.get("topics") or []

        stats_lines = [
            f"### {name}",
            "",
            description,
            "",
            f"- **Stars**: {stars}",
            f"- **Forks**: {forks}",
            f"- **Primary Language**: {language}",
        ]
        if topics:
            stats_lines.append(f"- **Topics**: {', '.join(str(t) for t in topics)}")

        repo_stats_md = "\n".join(stats_lines)

        progress(0.4, desc="Step 2/5: Summarizing overview...")

        # Overview snippet
        overview = analysis.get("overview", "") or ""
        overview_md = "### Overview\n\n" + overview if overview else ""

        progress(0.7, desc="Step 3/5: Drafting README content...")

        # Build README content via DocGenerator
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        readme_path = doc_generator.generate_readme(
            analysis_data=analysis,
            repo_info=repo_info,
            output_path=str(output_dir / "generated_README.md"),
        )
        readme_content = Path(readme_path).read_text(encoding="utf-8")

        progress(1.0, desc="Done")
        gr.Success("GitHub repository analysis complete.")
        return repo_stats_md, overview_md, readme_content, str(readme_path), result, name

    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        gr.Warning(f"Error during GitHub analysis: {exc}")
        return "", "", "", "", {}, ""


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

custom_css = """
body {
  background: radial-gradient(circle at top left, #6366f1 0, #8b5cf6 40%, #020617 100%);
}
.gradio-container {
  max-width: 1100px !important;
  margin: 0 auto !important;
  border-radius: 1.5rem;
  overflow: hidden;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.65);
}
.gr-block, .gr-panel, .gr-accordion, .gr-tab {
    border-radius: 1rem !important;
    background: rgba(255,255,255,0.03);
    padding: 1rem;
    color: #e5e7eb;
}
button {
    border-radius: 999px !important;
    font-weight: 600;
    padding: 0.6rem 1.2rem;
}

/* Slightly larger, more readable primary buttons */
.gr-button-primary {
    font-size: 0.95rem;
}
/* Improve contrast for code/editor area */
.gr-code {
    background: rgba(0,0,0,0.45) !important;
    color: #f8fafc !important;
}
"""


with gr.Blocks() as demo:
    gr.Markdown(
        """
        <div style="text-align: center; padding: 1rem 0;">
            <h1 style="color: white; margin-bottom: .25rem;">CoDoc</h1>
            <p style="color: #e5e7eb; font-size: 0.95rem;">
                CoDoc — analyze code solutions and generate professional documentation for projects.
            </p>
        </div>
        """
    )

    with gr.Tabs() as tabs:
        # ----------------------- TAB 0: Cover Page -----------------------
        with gr.Tab("Home"):
                        gr.Markdown(
                                """
                                <div style="text-align: center; padding: 3rem 1rem;">
                                    <h2 style="color: white; margin-bottom: 1rem; font-size: 2rem;">Welcome to CoDoc</h2>
                                    <p style="color: #d1d5db; margin-bottom: 1rem; font-size: 1.05rem;">
                                        CoDoc helps developers document and improve code quickly.
                                    </p>
                                    <div style="color: #cbd5e1; text-align: left; display: inline-block; max-width: 760px;">
                                        <ul>
                                            <li><strong>Code Analysis</strong>: Get complexity, issues, and optimized versions for code snippets.</li>
                                            <li><strong>README Generation</strong>: Draft polished README files for GitHub repositories automatically.</li>
                                            <li><strong>Exports</strong>: Download DOCX reports and Markdown READMEs for sharing.</li>
                                        </ul>
                                    </div>
                                    <p style="color: #94a3b8; margin-top: 1.5rem;">Use the tabs above to open the Code Analyzer or the README Generator.</p>
                                </div>
                                """
                        )

        # ----------------------- TAB 1: Code Analyzer -----------------------
        with gr.Tab("Code Analyzer"):
            with gr.Row():
                with gr.Column(scale=3):
                    code_input = gr.Code(
                        label="Paste your code solution",
                        language="python",
                        value="",
                    )
                    language_dd = gr.Dropdown(
                        label="Language",
                        choices=["Python", "Java", "C++", "JavaScript", "TypeScript", "Go"],
                        value="Python",
                    )
                    gr.Markdown("Select the language of your solution. It may be auto-detected from uploaded files.")
                    gr.Markdown("Upload a source file; the code editor will be auto-populated.")
                    file_input = gr.File(
                        label="Or upload a code file",
                        file_types=[".py", ".js", ".ts", ".java", ".cpp", ".txt"],
                    )

                    code_counter = gr.Markdown(
                        value="Characters: 0",
                        elem_id="code-char-counter",
                    )

                    gr.Markdown("**Examples**")
                    with gr.Row():
                        btn_two_sum = gr.Button("Two Sum", variant="secondary")
                        btn_reverse = gr.Button("Reverse String", variant="secondary")
                        btn_valid_paren = gr.Button(
                            "Valid Parentheses", variant="secondary"
                        )

                    analyze_btn = gr.Button(
                        "Analyze Solution",
                        variant="primary",
                    )

                with gr.Column(scale=4):
                    with gr.Accordion("Analysis", open=True):
                        analysis_out = gr.Markdown("")
                    with gr.Accordion("Optimized Version", open=False):
                        optimized_out = gr.Markdown("")
                    with gr.Accordion("Alternative Approaches", open=False):
                        alternatives_out = gr.Markdown("")

                    # State to hold last analysis dict and report path
                    code_state = gr.State({})
                    code_docx_path = gr.State("")

                    gr.Markdown("Download a polished Word report for this solution.")
                    download_docx = gr.DownloadButton(
                        "Download DOCX Report",
                        variant="secondary",
                    )

            # Example callbacks
            def _example_two_sum() -> tuple[str, str]:
                code = """def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []"""
                return code, "Python"

            def _example_reverse_string() -> tuple[str, str]:
                code = """def reverse_string(s: str) -> str:
    return s[::-1]"""
                return code, "Python"

            def _example_valid_parentheses() -> tuple[str, str]:
                code = """def is_valid(s: str) -> bool:
    stack = []
    mapping = {')': '(', ']': '[', '}': '{'}
    for ch in s:
        if ch in mapping.values():
            stack.append(ch)
        elif ch in mapping:
            if not stack or stack[-1] != mapping[ch]:
                return False
            stack.pop()
    return not stack"""
                return code, "Python"

            btn_two_sum.click(
                _example_two_sum,
                inputs=None,
                outputs=[code_input, language_dd],
            )
            btn_reverse.click(
                _example_reverse_string,
                inputs=None,
                outputs=[code_input, language_dd],
            )
            btn_valid_paren.click(
                _example_valid_parentheses,
                inputs=None,
                outputs=[code_input, language_dd],
            )

            # Auto-populate code editor & language when a file is uploaded
            def _on_file_upload(file: Any) -> tuple[str, str]:
                if not file:
                    return "", "Python"
                text = _load_file_content(file)
                detected = _detect_language_from_filename(
                    Path(getattr(file, "name", "uploaded"))
                )
                return text, (detected or "Python")

            file_input.change(
                _on_file_upload,
                inputs=file_input,
                outputs=[code_input, language_dd],
            )

            # Character counter for code input
            def _update_char_count(text: str) -> str:
                length = len(text or "")
                return f"Characters: {length}"

            code_input.change(
                _update_char_count,
                inputs=code_input,
                outputs=code_counter,
            )

            # Analyze button wiring
            analyze_btn.click(
                analyze_code_solution,
                inputs=[code_input, language_dd, file_input],
                outputs=[
                    analysis_out,
                    optimized_out,
                    alternatives_out,
                    code_state,
                    code_docx_path,
                ],
                show_progress=True,
            )

            # Download uses the generated path
            def _update_code_report(path: str) -> str:
                return path or ""

            code_docx_path.change(
                _update_code_report,
                inputs=code_docx_path,
                outputs=download_docx,
            )

        # ---------------------- TAB 2: GitHub README -----------------------
        with gr.Tab("GitHub README Generator"):
            with gr.Row():
                with gr.Column(scale=3):
                    github_url_in = gr.Textbox(
                        label="GitHub Repository URL",
                        placeholder="https://github.com/owner/repository",
                    )

                    # Verbosity option for README generation
                    verbosity_radio = gr.Radio(
                        label="README Verbosity",
                        choices=["Concise", "Detailed"],
                        value="Concise",
                        info="Choose Concise for short READMEs or Detailed for a fuller README",
                    )

                    gr.Markdown("**Examples**")
                    with gr.Row():
                        ex1_btn = gr.Button(
                            "octocat/Hello-World",
                            variant="secondary",
                        )
                        ex2_btn = gr.Button(
                            "gradio-app/gradio",
                            variant="secondary",
                        )

                    generate_btn = gr.Button(
                        "Generate README",
                        variant="primary",
                    )

                with gr.Column(scale=4):
                    repo_stats_out = gr.Markdown(label="Repository Stats")
                    overview_out = gr.Markdown(label="Overview")
                    readme_preview = gr.Markdown(label="Generated README Preview")

                    github_state = gr.State({})
                    github_readme_path = gr.State("")

                    gr.Markdown("Download the generated README as a Markdown file.")
                    download_readme = gr.DownloadButton(
                        "Download README.md",
                        variant="secondary",
                    )

            def _example_github_1() -> str:
                return "https://github.com/octocat/Hello-World"

            def _example_github_2() -> str:
                return "https://github.com/gradio-app/gradio"

            ex1_btn.click(_example_github_1, inputs=None, outputs=github_url_in)
            ex2_btn.click(_example_github_2, inputs=None, outputs=github_url_in)

            generate_btn.click(
                analyze_github_repo,
                inputs=[github_url_in, verbosity_radio],
                outputs=[
                    repo_stats_out,
                    overview_out,
                    readme_preview,
                    github_readme_path,
                    github_state,
                    gr.State(),  # ignore repo_name in UI for now
                ],
                show_progress=True,
            )

            def _update_github_readme(path: str) -> str:
                return path or ""

            github_readme_path.change(
                _update_github_readme,
                inputs=github_readme_path,
                outputs=download_readme,
            )


if __name__ == "__main__":
    demo.queue().launch(
        theme=gr.themes.Soft(),
        css=custom_css
    )