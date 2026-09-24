import asyncio
import json
import shutil
from pathlib import Path

from pydantic import BaseModel

from mealie.core.config import get_app_settings
from mealie.core.dependencies.dependencies import get_temporary_path
from mealie.core.root_logger import get_logger

logger = get_logger()


class CodexCLIError(Exception):
    pass


def _trim_codex_output(text: str, max_length: int = 4000) -> str:
    text = text.strip()
    return text if len(text) <= max_length else f"{text[:max_length]}... [truncated {len(text) - max_length} chars]"


def _format_codex_error(stdout: bytes, stderr: bytes) -> str:
    if stderr_text := stderr.decode("utf-8", errors="replace").strip():
        return _trim_codex_output(stderr_text)
    stdout_text = stdout.decode("utf-8", errors="replace").strip()
    error_lines = [line for line in stdout_text.splitlines() if "ERROR" in line or '"type": "error"' in line]
    return _trim_codex_output("\n".join(error_lines) if error_lines else stdout_text)


class CodexCLIService:
    @staticmethod
    def is_available() -> bool:
        settings = get_app_settings()
        return settings.CODEX_CLI_ENABLED and shutil.which(settings.CODEX_CLI_BINARY) is not None

    def _build_command(self, schema_path: Path, output_path: Path) -> list[str]:
        settings = get_app_settings()
        command = [
            settings.CODEX_CLI_BINARY,
            "exec",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
        ]
        if settings.CODEX_CLI_MODEL:
            command.extend(["--model", settings.CODEX_CLI_MODEL])
        if settings.CODEX_CLI_PROFILE:
            command.extend(["--profile", settings.CODEX_CLI_PROFILE])
        command.append("-")
        return command

    @staticmethod
    def _build_prompt(raw_content: str, prompt_context: str | None = None) -> str:
        prompt = (
            "Extract one cooking recipe from the supplied source content.\n\n"
            "Return data matching the supplied JSON Schema exactly. Never invent ingredients, quantities, "
            "temperatures, durations, or servings. Preserve original ingredient text. Parse quantity, unit, food, "
            "and note when clear. Use foodId and unitId only for unambiguous entries in the supplied catalog; never "
            "invent IDs. Put distinct actions in separate instructions. Remove promotional text and record source "
            "ambiguities in warnings. If there is no usable recipe, return empty ingredient and instruction arrays "
            "and low confidence."
        )
        if prompt_context:
            prompt += f"\n\nKnown Mealie catalog:\n{prompt_context}"
        return f"{prompt}\n\nSource content:\n{raw_content}"

    async def extract_structured[T: BaseModel](
        self, raw_content: str, schema_model: type[T], prompt_context: str | None = None
    ) -> T:
        settings = get_app_settings()
        with get_temporary_path() as temp_path:
            schema_path = temp_path / "recipe-schema.json"
            output_path = temp_path / "recipe.json"
            schema_path.write_text(
                json.dumps(schema_model.model_json_schema(), separators=(",", ":")), encoding="utf-8"
            )
            try:
                process = await asyncio.create_subprocess_exec(
                    *self._build_command(schema_path, output_path),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except OSError as e:
                raise CodexCLIError(f"Could not start Codex CLI: {e}") from e
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(self._build_prompt(raw_content, prompt_context).encode()),
                    timeout=settings.CODEX_CLI_TIMEOUT,
                )
            except TimeoutError as e:
                process.kill()
                await process.wait()
                raise CodexCLIError("Codex CLI recipe extraction timed out") from e
            if process.returncode != 0:
                error_text = _format_codex_error(stdout, stderr)
                logger.error("Codex CLI failed: %s", error_text)
                raise CodexCLIError(error_text or "Codex CLI recipe extraction failed")
            try:
                return schema_model.model_validate_json(output_path.read_text(encoding="utf-8"))
            except Exception as e:
                raise CodexCLIError("Codex CLI returned invalid recipe JSON") from e
