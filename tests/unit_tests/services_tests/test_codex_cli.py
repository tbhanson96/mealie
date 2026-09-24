from pathlib import Path

from mealie.schema.codex import SocialRecipe
from mealie.services.codex_cli import CodexCLIService, _format_codex_error


def test_codex_prompt_context_is_passed_through_stdin_not_argv():
    service = CodexCLIService()
    command = service._build_command(Path("/tmp/schema.json"), Path("/tmp/output.json"))
    catalog = "x" * 200_000
    prompt = service._build_prompt("recipe content", catalog)

    assert command[-1] == "-"
    assert catalog not in command
    assert catalog in prompt
    assert "recipe content" in prompt


def test_codex_recipe_schema_uses_supported_id_formats():
    assert "uuid4" not in str(SocialRecipe.model_json_schema())


def test_codex_error_prefers_stderr():
    assert _format_codex_error(b"stdout failure", b"stderr failure") == "stderr failure"


def test_codex_error_filters_noisy_stdout_to_error_lines():
    noisy_stdout = "\n".join(
        [
            "OpenAI Codex",
            '{"foods":[' + ("x" * 50_000) + "]}",
            'ERROR: {"code":"invalid_json_schema"}',
        ]
    ).encode()
    error_text = _format_codex_error(noisy_stdout, b"")
    assert "OpenAI Codex" not in error_text
    assert '"foods"' not in error_text
    assert "invalid_json_schema" in error_text
