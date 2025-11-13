from pydantic import BaseModel
from typing import List, Optional

# сам по себе ингредиент имеет только название. Этот класс описывает любой ингридиент
class IngredientBase(BaseModel):
    ingredient_name: str

# класс копия IngredientBase, ввел для понятного нейминга при создании объектов
class IngredientCreate(IngredientBase):
    pass

# класс для того, чтобы кидать в бдшку
class Ingredient(IngredientBase):
    id: int
    class Config:
        orm_mode = True

# этот класс уже для рецепта. Ингридиент как единица имеет только название, но в рецепте у него появляется еще
# 2 характеристики: количество и единицы измерения
class IngredientInRecipe(IngredientBase):
    ingredient_quantity: str
    ingredient_unit: str

# для остальных классов в этом файле аналогично: класс базы, класс для создания (копия базы), класс для бдшки

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    class Config:
        orm_mode = True

class RecipeBase(BaseModel):
    recipe_name: str
    number_of_servings: Optional[int] = None
    cooking_time: Optional[int] = None
    description: Optional[str] = None

class RecipeCreate(RecipeBase):
    ingredients: List[IngredientInRecipe]
    categories: List[str]  # список названий категорий

class RecipeUpdate(BaseModel):
    recipe_name: Optional[str] = None
    number_of_servings: Optional[int] = None
    cooking_time: Optional[int] = None
    description: Optional[str] = None
    ingredients: Optional[List[IngredientInRecipe]] = None
    categories: Optional[List[str]] = None

class Recipe(RecipeBase):
    id: int
    ingredients: List[IngredientInRecipe]
    categories: List[Category]
    
    class Config:
        orm_mode = True