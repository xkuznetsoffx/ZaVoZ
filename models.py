from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base

# Вспомагательная таблица для рецептов и категорий
recipe_category = Table('recipe_category', Base.metadata,
    Column('recipe_id', Integer, ForeignKey('recipes.id')),
    Column('category_id', Integer, ForeignKey('categories.id'))
)

# Вспомогательная таблица для рецептов и ингредиентов
recipe_ingredient = Table('recipe_ingredient', Base.metadata,
    Column('recipe_id', Integer, ForeignKey('recipes.id')),
    Column('ingredient_id', Integer, ForeignKey('ingredients.id')),
    Column('quantity', String),  # количество для данного рецепта
    Column('unit', String)       # единицы измерения для данного рецепта
)

class Category(Base):
    __tablename__ = "categories"
    # id категории
    id = Column(Integer, primary_key=True, index=True)
    # название категории
    name = Column(String, unique=True, index=True)
    # явная связь с рецептами (многие-ко-многим)
    recipes = relationship("Recipe", secondary=recipe_category, back_populates="categories")

class Ingredient(Base):
    __tablename__ = "ingredients"
    # id ингредиента
    id                  = Column(Integer, primary_key=True, index=True)
    # название ингридиента
    ingredient_name     = Column(String, unique=True, index=True)
    # связь с рецептами (многие-ко-многим)
    recipes = relationship("Recipe", secondary=recipe_ingredient, back_populates="ingredients")

class Recipe(Base):
    __tablename__ = "recipes"
    # id рецепта
    id                  = Column(Integer, primary_key=True, index=True)
    # название рецепта
    recipe_name         = Column(String, index=True)
    # на какое количество персон рецепт
    number_of_servings  = Column(Integer)
    # время приготовления
    cooking_time        = Column(Integer)
    # описание рецепта
    description         = Column(String)
    # связь с ингредиентами (многие-ко-многим)
    ingredients = relationship("Ingredient", secondary=recipe_ingredient, back_populates="recipes")
    # связь с категориями (многие-ко-многим)
    categories = relationship("Category", secondary=recipe_category, back_populates="recipes")
