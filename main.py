from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, func
from typing import List, Dict, Optional
import random
from models import Base, Ingredient, Recipe, Category, recipe_category, recipe_ingredient
from database import engine, session_local
from schemas import IngredientCreate, CategoryCreate, RecipeCreate, Ingredient as db_ingr, Recipe as db_recipe
from typing import Dict, List, Callable, Any
from dataclasses import dataclass

from parsing import (
    RecipeParser,
    get_all_categories, get_all_recipes, get_all_ingredients,
    get_categories_and_recipe_db_table, get_ingredients_and_recipe_db_table
)

app = FastAPI()

# Подключаем статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)


def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ручка для добавления ингридиента
@app.post("/ingredients/", response_model=db_ingr)
async def create_ingredient(ingredient: IngredientCreate, db: Session = Depends(get_db)):
    try:
        # Проверяем, существует ли уже такой ингредиент
        existing_ingredient = db.query(Ingredient).filter(
            Ingredient.ingredient_name == ingredient.ingredient_name
        ).first()

        if existing_ingredient:
            raise HTTPException(status_code=400, detail="Ингредиент уже существует")

        db_ingredient = Ingredient(ingredient_name=ingredient.ingredient_name)
        db.add(db_ingredient)
        db.commit()
        db.refresh(db_ingredient)
        return db_ingredient
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании ингредиента: {str(e)}")


# ручка для перезаполнения БД (допустим захотели получить актуальную информацию или расширить базу рецептов)
@app.post("/refill_database/")
async def refill_database(count: int, db: Session = Depends(get_db)):
    try:
        print(f"Начало обновления базы данных. Количество рецептов: {count}")

        # 1. Очищаем БД
        clear_database(db)

        # 2. Парсим рецепты
        print("Начало парсинга рецептов...")
        parser = RecipeParser("https://www.russianfood.com/recipes/recipe.php")
        parsed_recipes = parser.parsing(count)

        if not parsed_recipes:
            raise HTTPException(status_code=500, detail="Не удалось спарсить рецепты")

        print(f"Успешно спарсили {len(parsed_recipes)} рецептов")

        # 3. Заполняем БД
        fill_database(db, parsed_recipes)

        return {
            "message": f"База данных успешно обновлена!",
            "parsed_recipes": len(parsed_recipes),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении базы данных: {str(e)}")


def clear_database(db: Session):
    try:
        metadata = Base.metadata
        # Очищаем связующие таблицы первыми (из-за внешних ключей)
        if 'recipe_ingredient' in metadata.tables:
            db.execute(text("DELETE FROM recipe_ingredient"))
        if 'recipe_category' in metadata.tables:
            db.execute(text("DELETE FROM recipe_category"))

        # Очищаем основные таблицы
        db.execute(text("DELETE FROM recipes"))
        db.execute(text("DELETE FROM ingredients"))
        db.execute(text("DELETE FROM categories"))

        # Сбрасываем автоинкрементные счетчики для SQLite
        try:
            db.execute(text("DELETE FROM sqlite_sequence"))
        except Exception as e:
            print(f"Таблица sqlite_sequence не существует или недоступна: {e}")

        db.commit()
        print("База данных успешно очищена")

    except Exception as e:
        db.rollback()
        print(f"Ошибка при очистке базы данных: {e}")
        raise


def fill_database(db: Session, parsed_recipes: List):
    try:
        # 1. Добавляем категории (с проверкой на существование)
        categories_set = get_all_categories(parsed_recipes)
        category_map = {}

        for category_name in categories_set:
            # Проверяем, существует ли категория
            existing_category = db.query(Category).filter(Category.name == category_name).first()
            if existing_category:
                category_map[category_name] = existing_category.id
            else:
                db_category = Category(name=category_name)
                db.add(db_category)
                db.flush()
                category_map[category_name] = db_category.id

        # 2. Добавляем ингредиенты (с проверкой на существование)
        ingredients_set = get_all_ingredients(parsed_recipes)
        ingredient_map = {}

        for ingredient_name in ingredients_set:
            # Проверяем, существует ли ингредиент
            existing_ingredient = db.query(Ingredient).filter(Ingredient.ingredient_name == ingredient_name).first()
            if existing_ingredient:
                ingredient_map[ingredient_name] = existing_ingredient.id
            else:
                db_ingredient = Ingredient(ingredient_name=ingredient_name)
                db.add(db_ingredient)
                db.flush()
                ingredient_map[ingredient_name] = db_ingredient.id

        # 3. Добавляем рецепты
        recipes_data = get_all_recipes(parsed_recipes)
        recipe_map = {}

        for recipe_data in recipes_data:
            db_recipe = Recipe(
                recipe_name=recipe_data['recipe_name'],
                number_of_servings=recipe_data['number_of_servings'],
                cooking_time=recipe_data['cooking_time'],
                description=recipe_data['description']
            )
            db.add(db_recipe)
        db.flush()  # Получаем ID для всех рецептов

        # Получаем ID добавленных рецептов
        for recipe in db.query(Recipe).all():
            recipe_map[recipe.recipe_name] = recipe.id

        # 4. Добавляем связи рецепт-ингредиент
        recipe_ingr_data = get_ingredients_and_recipe_db_table(parsed_recipes)
        for row in recipe_ingr_data:
            # Получаем реальные ID из наших словарей
            recipe_names = list(recipe_map.keys())
            ingredient_names = list(ingredient_map.keys())

            if (row['recipe_id'] <= len(recipe_names) and
                    row['ingredient_id'] <= len(ingredient_names)):

                recipe_name = recipe_names[row['recipe_id'] - 1]
                ingredient_name = ingredient_names[row['ingredient_id'] - 1]

                # Проверяем, существует ли уже такая связь
                existing_link = db.execute(
                    text(
                        "SELECT 1 FROM recipe_ingredient WHERE recipe_id = :recipe_id AND ingredient_id = :ingredient_id"),
                    {"recipe_id": recipe_map[recipe_name], "ingredient_id": ingredient_map[ingredient_name]}
                ).first()

                if not existing_link:
                    stmt = recipe_ingredient.insert().values(
                        recipe_id=recipe_map[recipe_name],
                        ingredient_id=ingredient_map[ingredient_name],
                        quantity=row['quantity'],
                        unit=row['unit']
                    )
                    db.execute(stmt)

        # 5. Добавляем связи рецепт-категория  
        recipe_category_data = get_categories_and_recipe_db_table(parsed_recipes)
        for row in recipe_category_data:
            recipe_names = list(recipe_map.keys())
            category_names = list(category_map.keys())

            if (row['recipe_id'] <= len(recipe_names) and
                    row['category_id'] <= len(category_names)):

                recipe_name = recipe_names[row['recipe_id'] - 1]
                category_name = category_names[row['category_id'] - 1]

                # Проверяем, существует ли уже такая связь
                existing_link = db.execute(
                    text("SELECT 1 FROM recipe_category WHERE recipe_id = :recipe_id AND category_id = :category_id"),
                    {"recipe_id": recipe_map[recipe_name], "category_id": category_map[category_name]}
                ).first()

                if not existing_link:
                    stmt = recipe_category.insert().values(
                        recipe_id=recipe_map[recipe_name],
                        category_id=category_map[category_name]
                    )
                    db.execute(stmt)

        db.commit()
        print("База данных успешно заполнена")

    except Exception as e:
        db.rollback()
        print(f"Ошибка при заполнении базы данных: {e}")
        raise


@dataclass
class FilterConfig:
    name: str
    filter_func: Callable
    requires_db: bool = False


class RecipeFilter:
    def __init__(self):
        self.filters = {
            'cooking_time': FilterConfig(
                name='cooking_time',
                filter_func=self._filter_cooking_time,
                requires_db=False
            ),
            'meal_type': FilterConfig(
                name='meal_type',
                filter_func=self._filter_meal_type,
                requires_db=True
            ),
            'difficulty': FilterConfig(
                name='difficulty',
                filter_func=self._filter_difficulty,
                requires_db=True
            )
        }

        self._cooking_time_map = {
            'быстро': ['15', '20', '25', '30', 'мин'],
            'средне': ['40', '45', '50', '55', '60', 'час'],
            'долго': ['1.5', '2', '3', 'час']
        }

        self._meal_type_map = {
            'завтрак': ['завтрак', 'breakfast', 'утро'],
            'обед': ['обед', 'lunch', 'первое', 'второе'],
            'ужин': ['ужин', 'dinner', 'вечер']
        }

        self._difficulty_map = {
            'легко': ('<=', 5),
            'тяжело': ('>', 8)
        }

    def apply_filters(self, query, db: Session, answers: Dict[str, str]):
        """Применяет все активные фильтры"""
        for filter_key, filter_config in self.filters.items():
            if filter_key in answers and answers[filter_key]:
                query = filter_config.filter_func(
                    query,
                    db if filter_config.requires_db else None,
                    answers[filter_key]
                )
        return query

    def _filter_cooking_time(self, query, db: Optional[Session], cooking_time: str):
        if cooking_time in self._cooking_time_map:
            filters = [Recipe.cooking_time.contains(term)
                       for term in self._cooking_time_map[cooking_time]]
            return query.filter(or_(*filters))
        return query

    def _filter_meal_type(self, query, db: Session, meal_type: str):
        if meal_type in self._meal_type_map:
            category_filters = self._meal_type_map[meal_type]
            meal_recipe_ids = db.query(Recipe.id) \
                .join(recipe_category) \
                .join(Category) \
                .filter(or_(*[Category.name.ilike(f'%{cat}%') for cat in category_filters])) \
                .distinct() \
                .subquery()
            return query.filter(Recipe.id.in_(meal_recipe_ids))
        return query

    def _filter_difficulty(self, query, db: Session, difficulty: str):
        if difficulty in self._difficulty_map:
            operator, threshold = self._difficulty_map[difficulty]
            subquery = db.query(Recipe.id) \
                .join(recipe_ingredient) \
                .group_by(Recipe.id)

            if operator == '<=':
                subquery = subquery.having(func.count(recipe_ingredient.c.ingredient_id) <= threshold)
            else:
                subquery = subquery.having(func.count(recipe_ingredient.c.ingredient_id) > threshold)

            return query.filter(Recipe.id.in_(subquery.subquery()))
        return query


def get_recipe_data(db: Session, recipe: Recipe) -> Dict:
    """Получает полные данные рецепта включая ингредиенты"""

    ingredients_data = db.query(
        Ingredient.ingredient_name,
        recipe_ingredient.c.quantity,
        recipe_ingredient.c.unit
    ).join(
        recipe_ingredient, Ingredient.id == recipe_ingredient.c.ingredient_id
    ).filter(
        recipe_ingredient.c.recipe_id == recipe.id
    ).all()

    ingredients = [
        {
            "ingredient_name": ing.ingredient_name,
            "quantity": ing.quantity,
            "unit": ing.unit or ""
        }
        for ing in ingredients_data
    ]

    return {
        "id": recipe.id,
        "recipe_name": recipe.recipe_name,
        "cooking_time": recipe.cooking_time,
        "number_of_servings": recipe.number_of_servings,
        "description": recipe.description,
        "ingredients": ingredients
    }


# глобальный экземпляр фильтра
recipe_filter = RecipeFilter()


@app.post("/api/generate-recipe")
async def generate_recipe(answers: Dict[str, str], db: Session = Depends(get_db)):
    try:
        # базовый запрос
        base_query = db.query(Recipe)

        # применяем фильтры
        filtered_query = recipe_filter.apply_filters(base_query, db, answers)
        filtered_recipes = filtered_query.all()

        # если нет результатов после фильтрации, берем все рецепты
        recipes = filtered_recipes if filtered_recipes else base_query.all()

        if not recipes:
            raise HTTPException(status_code=404, detail="Рецепты не найдены в базе данных")

        # выбираем случайный рецепт и возвращаем данные
        selected_recipe = random.choice(recipes)
        return get_recipe_data(db, selected_recipe)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации рецепта: {str(e)}")
