import json
from uuid import UUID

from mealie.schema.codex import SocialRecipe, SocialRecipeIngredient
from mealie.schema.openai.organizers import OpenAIOrganizers
from mealie.schema.recipe.recipe import Recipe
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient
from mealie.schema.recipe.recipe_notes import RecipeNote
from mealie.schema.recipe.recipe_step import RecipeStep
from mealie.services.parser_services._base import DataMatcher

from .context import WorkflowContext
from .recipe_conversion import resolve_name_and_slug


def _catalog_names(item) -> list[str]:
    return [name for name in [item.name, item.plural_name, *(alias.name for alias in (item.aliases or []))] if name]


def build_catalog_context(ctx: WorkflowContext) -> str:
    matcher = DataMatcher(ctx.repos)
    foods = [{"id": str(food.id), "names": _catalog_names(food)} for food in matcher.foods_by_id.values()]
    units = [
        {
            "id": str(unit.id),
            "names": [
                name
                for name in [
                    unit.name,
                    unit.plural_name,
                    unit.abbreviation,
                    unit.plural_abbreviation,
                    *(alias.name for alias in (unit.aliases or [])),
                ]
                if name
            ],
        }
        for unit in matcher.units_by_id.values()
    ]
    return json.dumps({"foods": foods, "units": units}, separators=(",", ":"))


def _catalog_item(items_by_id: dict, item_id: str | None):
    if not item_id:
        return None
    try:
        return items_by_id.get(UUID(item_id))
    except TypeError, ValueError:
        return None


def _ingredient(ingredient: SocialRecipeIngredient, matcher: DataMatcher) -> RecipeIngredient:
    unit = _catalog_item(matcher.units_by_id, ingredient.unitId)
    food = _catalog_item(matcher.foods_by_id, ingredient.foodId)
    if not unit and ingredient.unit:
        unit = matcher.find_unit_match(ingredient.unit)
    if not food and ingredient.food:
        food = matcher.find_food_match(ingredient.food)

    unmatched = []
    if ingredient.unit and not unit:
        unmatched.append(ingredient.unit)
    if ingredient.food and not food:
        unmatched.append(ingredient.food)
    if ingredient.note:
        unmatched.append(ingredient.note)

    return RecipeIngredient(
        quantity=ingredient.quantity or 0,
        unit=unit,
        food=food,
        note=" ".join(unmatched),
        original_text=ingredient.originalText,
    )


def _minutes(minutes: int | None) -> str | None:
    if minutes is None:
        return None
    return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"


def _yield(servings: float | None) -> str | None:
    if servings is None:
        return None
    value = int(servings) if float(servings).is_integer() else servings
    return f"{value} serving" if servings == 1 else f"{value} servings"


def to_recipe(ctx: WorkflowContext, response: SocialRecipe) -> Recipe:
    matcher = DataMatcher(ctx.repos)
    name, slug = resolve_name_and_slug(ctx, response.name)
    owner = (
        {"user_id": ctx.user.id, "group_id": ctx.user.group_id, "household_id": ctx.household.id}
        if ctx.user and ctx.household
        else {}
    )
    ctx.organizer_names = OpenAIOrganizers(tags=response.tags, categories=[], tools=[])
    return Recipe(
        **owner,
        name=name,
        slug=slug,
        description=response.description,
        recipe_yield=_yield(response.servings),
        total_time=_minutes(response.totalTimeMinutes),
        prep_time=_minutes(response.prepTimeMinutes),
        perform_time=_minutes(response.cookTimeMinutes),
        recipe_ingredient=[_ingredient(item, matcher) for item in response.ingredients if item.originalText],
        recipe_instructions=[
            RecipeStep(title=instruction.title, text=instruction.text)
            for instruction in response.instructions
            if instruction.text
        ],
        notes=[RecipeNote(title="Import warning", text=warning) for warning in response.warnings],
        image=(
            None if ctx.input.images else response.imageUrl or (ctx.compiled_source and ctx.compiled_source.image_url)
        ),
        org_url=response.sourceUrl or ctx.input.url,
    )
