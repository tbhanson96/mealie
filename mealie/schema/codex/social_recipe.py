from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SocialRecipeIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    originalText: str = Field(..., description="The ingredient exactly as it appeared in the source.")
    quantity: float | None = Field(..., description="Parsed numeric quantity, or null when absent.")
    unit: str | None = Field(..., description="Parsed measurement unit, or null when absent.")
    food: str | None = Field(..., description="Parsed food name with quantity and unit removed.")
    foodId: str | None = Field(..., description="ID from the supplied Mealie foods catalog, or null.")
    unitId: str | None = Field(..., description="ID from the supplied Mealie units catalog, or null.")
    note: str | None = Field(..., description="Preparation or ingredient detail not represented elsewhere.")


class SocialRecipeInstruction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None
    text: str


class SocialRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None
    sourceUrl: str | None
    imageUrl: str | None
    servings: float | None
    totalTimeMinutes: int | None
    prepTimeMinutes: int | None
    cookTimeMinutes: int | None
    ingredients: list[SocialRecipeIngredient]
    instructions: list[SocialRecipeInstruction]
    tags: list[str]
    warnings: list[str]
    confidence: Literal["high", "medium", "low"]
