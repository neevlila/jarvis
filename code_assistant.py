from providers.provider_manager import ProviderManager

def generate_code_llama(prompt: str, language: str, is_api_call: bool = True) -> str:
    """
    Calls meta/llama-3.3-70b-instruct to generate code.
    If is_api_call is True, returns a structured JSON string matching {"code": "..."}.
    If is_api_call is False, returns pure code text.
    """
    return ProviderManager.code(prompt, language, is_api_call)

def explain_and_debug_code(code: str, output: str, language: str, prompt: str) -> str:
    """
    Calls meta/llama-3.3-70b-instruct to analyze code + console output and answer the prompt.
    """
    system_prompt = (
        "You are J.A.R.V.I.S., a premium developer assistant integrated into a code execution terminal console.\n"
        "Analyze the user's current code, the console output (from compilation or execution), and the user's question.\n"
        "Provide a clear, brief explanation of the problem, and suggest optimized, clean code fixes where relevant.\n"
        "Format any corrected code in standard markdown code blocks (e.g., ```python ... ``` or ```javascript ... ```).\n"
        "Be direct, highly technical, and concise in your explanation. Focus on resolving the issue quickly.\n\n"
        "CRITICAL ENVIRONMENT CONSTRAINTS:\n"
        "1. The terminal execution environment is strictly NON-INTERACTIVE. The code runs in a subprocess, meaning standard input (stdin) reads like `input()` or `sys.stdin.read()` will block indefinitely and trigger a 10-second timeout.\n"
        "   - Suggest using hardcoded test variables, default values, or command line arguments (e.g., `sys.argv`) instead of interactive input.\n"
        "2. The environment runs on Windows. DO NOT suggest using `select.select` on `sys.stdin` or other file descriptors, because on Windows, `select.select` only works on network sockets (throwing WinError 10093 / WSAStartup failed otherwise)."
    )

    user_prompt = (
        f"Target Language: {language}\n\n"
        f"--- CURRENT CODE ---\n{code}\n\n"
        f"--- TERMINAL OUTPUT ---\n{output}\n\n"
        f"--- USER QUESTION ---\n{prompt}"
    )

    return ProviderManager.chat(
        system_prompt=system_prompt,
        messages_history=[],
        user_prompt=user_prompt
    )
