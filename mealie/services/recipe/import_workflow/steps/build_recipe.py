from mealie.core.root_logger import get_logger
from mealie.schema.codex import SocialRecipe
from mealie.schema.openai.recipe import OpenAIRecipe
from mealie.services.codex_cli import CodexCLIError
from mealie.services.scraper import cleaner

from ..base import WorkflowStep
from ..codex_conversion import build_catalog_context
from ..codex_conversion import to_recipe as codex_to_recipe
from ..context import WorkflowContext
from ..exceptions import NoRecipeDataError
from ..recipe_conversion import to_recipe

BUILD_RECIPE_PROMPT = "recipes.build-recipe"
logger = get_logger()


class BuildRecipeStep(WorkflowStep):
    """Turns the Compiled Source Document into a draft recipe."""

    name = "build-recipe"
    progress_key = "recipe.create-progress.creating-recipe"

    def _build_message(self, ctx: WorkflowContext) -> str:
        compiled = ctx.compiled_source
        if not compiled:
            raise NoRecipeDataError(ctx.translator.t("recipe.import-errors.unreadable-source"))

        return f"Below is the transcribed recipe source.\n\n{compiled.content}"

    async def run(self, ctx: WorkflowContext) -> None:
        if ctx.codex:
            try:
                response = await ctx.codex.extract_structured(
                    self._build_message(ctx),
                    SocialRecipe,
                    prompt_context=build_catalog_context(ctx),
                )
                if response.confidence == "low" and not (response.ingredients or response.instructions):
                    raise NoRecipeDataError(
                        "; ".join(response.warnings) or ctx.translator.t("recipe.import-errors.no-recipe-found")
                    )
                recipe = codex_to_recipe(ctx, response)
                structured_ingredients = recipe.recipe_ingredient
                recipe = cleaner.clean(recipe, ctx.translator)
                recipe.recipe_ingredient = structured_ingredients
                ctx.draft_recipe = recipe
                return
            except CodexCLIError:
                if not (ctx.ai.provider_settings and ctx.ai.provider_settings.ai_enabled):
                    raise
                logger.exception("Codex extraction failed; falling back to the configured AI provider")

        response = await ctx.ai.get_response(
            ctx.ai.get_prompt(BUILD_RECIPE_PROMPT),
            self._build_message(ctx),
            response_schema=OpenAIRecipe,
        )

        if not response:
            raise NoRecipeDataError(ctx.translator.t("recipe.import-errors.provider-returned-nothing"))

        if not (response.ingredients or response.instructions):
            raise NoRecipeDataError(ctx.translator.t("recipe.import-errors.no-recipe-found"))

        ctx.draft_recipe = cleaner.clean(to_recipe(ctx, response), ctx.translator)
