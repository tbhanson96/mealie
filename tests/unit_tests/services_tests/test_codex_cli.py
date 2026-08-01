from pathlib import Path

from mealie.schema.codex.social_recipe import SocialRecipe
from mealie.services.codex_cli import CodexCLIService, _format_codex_error


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


def test_codex_recipe_schema_uses_supported_id_formats():
    schema = SocialRecipe.model_json_schema()

    assert "uuid4" not in str(schema)


def test_codex_error_prefers_stderr():
    assert _format_codex_error(b"stdout failure", b"stderr failure") == "stderr failure"


def test_codex_error_filters_noisy_stdout_to_error_lines():
    noisy_stdout = "\n".join(
        [
            "OpenAI Codex v0.142.5",
            '{"foods":[' + ("x" * 50_000) + "]}",
            'ERROR: { "code": "invalid_json_schema" }',
            'ERROR: { "message": "uuid4 is not a valid format" }',
        ]
    ).encode()

    error_text = _format_codex_error(noisy_stdout, b"")

    assert "OpenAI Codex" not in error_text
    assert '"foods"' not in error_text
    assert "invalid_json_schema" in error_text
    assert "uuid4 is not a valid format" in error_text
