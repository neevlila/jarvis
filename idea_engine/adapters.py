"""
Platform Adaptation Layer for J.A.R.V.I.S. Master Build Prompts.

Adapts universal master build specifications to specific AI coding platforms
(Antigravity, Cursor, Claude Code, Lovable, v0, Bolt) without altering
the underlying product requirements or architecture.
"""

from idea_engine.models import TargetPlatform


class PlatformAdapters:
    """
    Applies environment-specific workflow directives and tool conventions
    to the universal master build prompt.
    """

    @classmethod
    def adapt(cls, universal_markdown: str, platform: TargetPlatform, project_title: str) -> str:
        """
        Decorates or formats the master prompt with platform-specific execution directives.
        """
        if platform == TargetPlatform.UNIVERSAL or platform == TargetPlatform.OTHER:
            return universal_markdown

        if platform == TargetPlatform.ANTIGRAVITY:
            antigravity_header = f"""<!-- ANTIGRAVITY AGENT WORKFLOW DIRECTIVE -->
<antigravity_execution_rules>
You are an autonomous AI coding agent operating inside the Google DeepMind Antigravity IDE.
Execute the following master project specification for "{project_title}".

WORKFLOW PROTOCOL:
1. PLANNING MODE: First create a detailed `implementation_plan.md` artifact outlining architecture, files, and tests. Wait for user feedback if required.
2. INCREMENTAL EXECUTION: Implement files cleanly using `write_to_file` and `replace_file_content`. Preserve existing working code.
3. QUALITY GATES: Run automated tests in terminal via `run_command` to verify functionality.
4. WALKTHROUGH: Create a `walkthrough.md` artifact summarizing implementation, screenshots, and test results upon completion.
</antigravity_execution_rules>

"""
            return antigravity_header + universal_markdown

        elif platform == TargetPlatform.CURSOR:
            cursor_header = f"""# .cursorrules & COMPOSER INSTRUCTIONS FOR {project_title.upper()}

```text
You are an expert full-stack engineer working in Cursor IDE (Composer / Agent Mode).
Follow the master project specification below.

CURSOR-SPECIFIC RULES:
- Read the entire codebase hierarchy before making edits.
- Use multi-file edits cleanly and maintain strict TypeScript / Python types.
- Never delete existing functional utilities or overwrite entire files without reading them first.
- Keep components modular under `components/`, `lib/`, `services/`, and `hooks/`.
```

---

"""
            return cursor_header + universal_markdown

        elif platform == TargetPlatform.CLAUDE_CODE:
            claude_header = f"""# CLAUDE.md / PROJECT SPECIFICATION FOR {project_title.upper()}

> **Claude Code Execution Directives:**
> 1. Execute using test-driven development (write unit tests for core services first).
> 2. Avoid monolithic files; enforce clean single-responsibility module boundaries.
> 3. Verify all bash/terminal commands for cross-platform compatibility.
> 4. Keep git commits atomic with clear conventional commit messages.

---

"""
            return claude_header + universal_markdown

        elif platform in [TargetPlatform.LOVABLE, TargetPlatform.V0, TargetPlatform.BOLT]:
            platform_name = platform.value
            web_ide_header = f"""# {platform_name.upper()} RAPID SCAFFOLDING SPECIFICATION: {project_title.upper()}

> **{platform_name} Build Guidelines:**
> - Implement a complete, fully interactive single-repo full-stack application.
> - Leverage Tailwind CSS, Lucide icons, and modern glassmorphic / dark-mode UI design.
> - Include rich interactive mock state, responsive mobile views, and instant visual feedback for all buttons and inputs.
> - Ensure all components render without runtime React errors.

---

"""
            return web_ide_header + universal_markdown

        return universal_markdown
