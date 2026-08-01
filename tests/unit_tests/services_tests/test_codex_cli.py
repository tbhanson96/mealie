from pathlib import Path

from mealie.services.codex_cli import CodexCLIService


def test_codex_prompt_context_is_passed_through_stdin_not_argv():
    service = CodexCLIService()
    schema_path = Path("/tmp/schema.json")
    output_path = Path("/tmp/output.json")
    large_catalog = "x" * 200_000

    command = service._build_command(schema_path, output_path)
    prompt = service._build_prompt("recipe content", large_catalog)

    assert command[-1] == "-"
    assert large_catalog not in command
    assert large_catalog in prompt
    assert "recipe content" in prompt
