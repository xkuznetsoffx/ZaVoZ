from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from models import Base, Ingredient, Recipe, Category
from database import engine, session_local
from schemas import IngredientCreate, CategoryCreate, RecipeCreate, Ingredient as db_ingr

import parsing

app = FastAPI()

Base.metadata.create_all(bind=engine)

def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()

@app.get("/")

def main_page():
    return "Сосал?"

@app.post("/ingredients/", response_model=db_ingr)
async def create_ingredient(ingredient: IngredientCreate, db: Session = Depends(get_db)) -> Ingredient:
    db_ingredient = Ingredient(ingredient_name=ingredient.ingredient_name)
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    return db_ingredient

# Сделать так, чтобы по запросу /refill_database/ - бдшка заполнялась данными, которые мы спарсили

# @app.post("/refill_database/", response_model=db_ingr)
# async def refill_database(db: Session = Depends(get_db)):
#     parser = parsing.RecipeParser(parsing.BASE_URL)
#     recipes = parser.parsing(10)
    
    
# @app.post("/refill_database/ingr/", response_model=)
# def fill_ingredients_table(recipes):
#     ingredients = parsing.get_all_ingredients(recipes)

# def fill_categories_table(recipes):
#     categories = parsing.get_all_categories(recipes)

# def fill_bald_recipes_table(recipes):
#     bald_recipes = parsing.get_all_recipes(recipes)

# def fill_recipe_ingr_table(recipes):
#     recipe_ingr_table = parsing.get_ingredients_and_recipe_db_table(recipes)

# def fill_recipe_category_table(recipes):
#     recipe_category_table = parsing.get_categories_and_recipe_db_table(recipes)