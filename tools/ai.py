import os
from typing import Literal, Optional

Provider = Literal["anthropic", "openai"]

SYSTEM_PROMPT = """You are a taskwarrior command parser. Convert natural language task descriptions into valid taskwarrior commands.

Return ONLY the raw taskwarrior arguments (without the leading "task"), nothing else. No explanation, no markdown, no code blocks.

Taskwarrior command syntax:
  add <description> [attributes]      — add a new task
  [filter] mod [attributes]           — modify a task
  [filter] done                       — complete a task
  [filter] delete                     — delete a task

Common attributes:
  due:<date>          — due date (tomorrow, friday, 2024-01-15, 1w, etc.)
  wait:<date>         — hide task until date
  scheduled:<date>    — start date
  priority:H|M|L      — priority (H=High, M=Medium, L=Low)
  project:<name>      — project (use dots for hierarchy: work.meetings)
  +<tag>              — add tag
  recur:<freq>        — recur: daily, weekly, monthly, yearly
  until:<date>        — end date for recurring tasks

Examples:
  Input: buy groceries tomorrow, high priority
  Output: add "buy groceries" due:tomorrow priority:H

  Input: schedule a team meeting every Monday
  Output: add "team meeting" recur:weekly due:monday

  Input: remind me to call John next Friday tagged as work
  Output: add "call John" due:friday +work"""


def _parse_with_anthropic(prompt: str, config_api_key: Optional[str] = None) -> str:
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package not installed. Run: uv add anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY") or config_api_key
    if not api_key:
        raise ValueError(
            "No Anthropic API key found.\n"
            "Set ANTHROPIC_API_KEY env var or add 'anthropic_api_key' to the 'ai' section in TW_CONFIG."
        )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _parse_with_openai(prompt: str, config_api_key: Optional[str] = None) -> str:
    try:
        import openai
    except ImportError:
        raise ImportError("openai package not installed. Run: uv add openai")

    api_key = os.environ.get("OPENAI_API_KEY") or config_api_key
    if not api_key:
        raise ValueError(
            "No OpenAI API key found.\n"
            "Set OPENAI_API_KEY env var or add 'openai_api_key' to the 'ai' section in TW_CONFIG."
        )

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=256,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def parse_nl_to_command(prompt: str, provider: Provider = "anthropic", config_api_key: Optional[str] = None) -> str:
    if provider == "anthropic":
        return _parse_with_anthropic(prompt, config_api_key)
    if provider == "openai":
        return _parse_with_openai(prompt, config_api_key)
    raise ValueError(f"Unknown provider '{provider}'. Use 'anthropic' or 'openai'")
