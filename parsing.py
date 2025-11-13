import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin
from entities import IngredientBase, RecipeBase
from typing import List, Tuple

BASE_URL = "https://www.russianfood.com/recipes/recipe.php" 

class RecipeParser:
    # единственное поле - URL страницы, которую парсим
    __URL = None
    def __init__(self, url):
        self.__URL = url
    # основная функция парсинга
    def parsing(self, count : int) -> List[RecipeBase]:

        recipes = []
        recipe = RecipeBase()

        page_num = 0

        while len(recipes) >= count:
            page_num += 1
            # собираем готовый url
            url = f"{self.__URL}?rid={page_num}"
            print(f"Парсинг страницы: {url}")
            
            # получаем html страницу по url
            html = self.__get_page(url)
            if not html:
                continue
                
            soup = BeautifulSoup(html, 'lxml')
            
            # парсим преобразованную html страницу и получаем готовый рецепт
            recipe = self.__get_full_recipe(soup)
            if recipe.recipe_name:
                recipes.append(recipe)
            print(recipe)
            print('Для продолжения нажмите любую клавишу...')
            input()
        return recipes
    # функция получения html страницы по url
    def __get_page(self, url) -> str:

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при загрузке страницы: {e}")
            return None
    # функция получения полной информации о рецепте
    def __get_full_recipe(self, soup) -> RecipeBase:
        recipe = RecipeBase()
        recipe.recipe_name = self.__get_recipe_title(soup)
        recipe.cooking_time = self.__get_recipe_subinfo(soup)['total_time']
        recipe.categories = self.__get_recipe_categories(soup)
        recipe.description = self.__get_recipe_description(soup)
        recipe.ingredients = self.__get_ingredients(soup)
        recipe.number_of_servings = self.__get_recipe_subinfo(soup)['portions']
        return recipe
    # функция получения категорий, к которым относится блюдо
    def __get_recipe_categories(self, soup) -> List[str]:
        
        categories_div = soup.find('div', class_='razdels padding_l')
        if not categories_div:
            return []
        
        categories = []
        
        category_links = categories_div.find_all('a', href=True)
        
        for link in category_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if '/recipes/recipe.php' in href or '/search/' in href:
                continue
                
            if not text:
                continue
                
            categories.append(text)
        
        return categories
    # функция получения названия блюда
    def __get_recipe_title(self, soup) -> str:
        recipe_title = soup.find('h1', class_='title')
        if recipe_title:
            return recipe_title.get_text(strip=True)
        return ""
    # функция получения доп информации
    def __get_recipe_subinfo(self, soup) -> dict:
        info = {
            'portions': '',
            'total_time': '',
            'prep_time': '',
        }
        
        sub_info = soup.find('div', class_='sub_info')
        if not sub_info:
            return info
        
        # Извлекаем порции
        portions = sub_info.find('span', class_='hl')
        if portions:
            info['portions'] = portions.get_text(strip=True)
        
        # Извлекаем время готовки
        time_elements = sub_info.find_all('span', class_='hl')
        if len(time_elements) >= 2:
            info['total_time'] = time_elements[1].get_text(strip=True)  # общее время
        if len(time_elements) >= 3:
            info['prep_time'] = time_elements[2].get_text(strip=True)   # ваше время
        else:
            info['total_time'] = 0
        return info
    # функция получения краткого описания рецепта
    def __get_recipe_description(self, soup) -> str:
        # ищем первый абзац после заголовка
        description_p = soup.find('div').find_next('p')
        if description_p:
            return description_p.get_text(strip=True)
        
        # альтернативный способ: ищем в div после title
        title = soup.find('h1', class_='title')
        if title:
            # ищем следующий div с описанием
            next_div = title.find_next('div')
            if next_div:
                p_tag = next_div.find('p')
                if p_tag:
                    return p_tag.get_text(strip=True)
        
        return ""
    # функция получения ингредиентов для рецепта из преобразованной html страницы
    def __get_ingredients(self, soup) -> List[IngredientBase]:
        
        # ищем класс 'ingr' с тэгом 'table'
        ingredients_table = soup.find('table', class_='ingr')  
            
        ingredients = []
        if not ingredients_table:
            return []
        # разбиваем таблицу ингредиентов на строки
        rows = ingredients_table.find_all('tr')

        rows.pop(0) # Это заголовок "Продукты"

        ingredient = IngredientBase()
        # одна строка - один инргедиент в рецепте
        for row in rows:
            # разбиваем строку на ячейки
            cells = row.find_all('td')
            # на сайте оказалось 2 формата рецептов: 
            # 1) где все красиво разбито: один тэг на название, другой на количество, третий на единицы измерения
            # 2) где все просто в одну строку намешано :(
            # поэтому идет разделение на старый формат с 3 тегами (первые 115000 рецептов)
            if len(cells) == 3:
                ingredient = self.__parse_old_format(cells)
            # и на новый с 1 тэгом (после 115000 рецептов)
            elif len(cells) == 1:
                ingredient = self.__parse_new_format(cells[0])
            # других я еще не встречал на этом сайте, поэтому кидаем исключение
            else:
                raise RuntimeError("Unknown format of recipe")
            ingredients.append(ingredient)
        return ingredients
    # парсинг старого формата рецептов
    def __parse_old_format(self, cells) -> IngredientBase:
        ingredient = IngredientBase()
        # получаем название ингридиента
        name_cell = cells[0]
        name_span = name_cell.find('span')
        ingredient.ingredient_name = name_span.get_text(strip=True) if name_span else name_cell.get_text(strip=True)
        # получаем его количество
        quantity_cell = cells[1]
        ingredient.ingredient_quantity = quantity_cell.get_text(strip=True)
        # получааем единицы измерения
        unit_cell = cells[2]
        unit_nobr = unit_cell.find('nobr')
        ingredient.ingredient_unit = unit_nobr.get_text(strip=True) if unit_nobr else unit_cell.get_text(strip=True)
        
        return ingredient
    # парсинг нового формата рецептов
    def __parse_new_format(self, cell) -> IngredientBase:

        ingredient = IngredientBase()

        span = cell.find('span')
        if not span:
            return None
        
        # получаем текст, заключенный в тэге 'span'
        full_text = span.get_text(strip=True)
        # разбиваем по тире (в основном в рецептах нового образца разделителем является '—' между названием ингридиента 
        # и его еоличеством и единиц измерения)
        if '—' in full_text:
            parts = full_text.split('—', 1) 
        # если нет тире, пока на похуй возвращаю каку как есть
        else:
            ingredient.ingredient_name = full_text
        
        if len(parts) == 2:
            # удаляем лишние пробелы, если они есть
            ingredient.ingredient_name = parts[0].strip()
            quantity_unit = parts[1].strip()

            quantity, unit = self.__extract_quantity_and_unit(quantity_unit)
            ingredient.ingredient_quantity = quantity
            ingredient.ingredient_unit = unit
            return ingredient
        
        return None
    # функция для разбиения количества и единиц измерения из новой записи ингридиента на сайте
    def __extract_quantity_and_unit(self, quantity_unit) -> Tuple[str, str]:
        quantity, unit = '', ''
        # суть в том, что пока мы не встретили подстроку "пробел + русская буква" - это все прибавляем к количеству, 
        # а остальное что осталось к единицам измеререния
        for i in range(len(quantity_unit) - 1):
            # 1040 - А
            # 1103 - я
            if quantity_unit[i] == ' ' and (ord(quantity_unit[i + 1]) >= 1040 and ord(quantity_unit[i + 1]) <= 1103):
                unit = quantity_unit[i+1:]
                break
            else:
                quantity += quantity_unit[i]
        return quantity, unit

# функция, возвращающая список всех категорий, которые встретились при парсинге, для добавления в 
# таблицу categories в БД
def get_all_categories(recipes : List[RecipeBase]) -> set[str]:
    categories = List()
    for recipe in recipes:
        for category in recipe.categories:
            categories.append(category)
    return set(categories)

# функция, возвращающая список всех ингредиентов, которые встретились при парсинге, для добавления в 
# таблицу ingredients в БД
def get_all_ingredients(recipes : List[RecipeBase]) -> set[str]:
    ingredients = List()
    for recipe in recipes:
        for ingredient in recipe.ingredients:
            ingredients.append(ingredient.ingredient_name)
    return set(ingredients)

# функция, возвращающая список всех рецептов, которые встретились при парсинге, но без списка ингредиентов
# и категорий, для добавления в таблицу categories в БД
def get_all_recipes(recipes : List[RecipeBase]) -> list:
    result_recipes = []
    current_recipe = {'recipe_name': None, 'number_of_servings': None, 'cooking_time': None, 'description': None}
    for recipe in recipes:
        current_recipe['recipe_name'] = recipe.recipe_name
        current_recipe['number_of_servings'] = recipe.number_of_servings
        current_recipe['cooking_time'] = recipe.cooking_time
        current_recipe['description'] = recipe.description
        result_recipes.append(current_recipe)
    return result_recipes

# функция поиска строки в массиве строк, возвращаемое значение - {индекс искомой строки в массиве + 1}
def search_string_in_string_list(list : List[str], finding_string : str) -> int:
    if finding_string not in list:
        raise RuntimeError('Array does not contain the given string')
    for i in range(len(list)):
        if list[i] == finding_string:
            return i + 1

# функция, формирующая список со строчками для сводной таблицы recipe|ingredient
def get_ingredients_and_recipe_db_table(recipes: List[RecipeBase]) -> list:
    result_list = []
    current_row = {'recipe_id': None, 'ingredient_id' : None, 'quantity' : None, 'unit' : None}
    ingredients = get_all_ingredients(recipes)
    for i in range(len(recipes)):
        current_row['recipe_id'] = i + 1
        for ingredient in recipes[i].ingredients:
            current_row['ingredient_id'] = search_string_in_string_list(ingredients, ingredient.ingredient_name)
            current_row['quantity'] = ingredient.ingredient_quantity
            current_row['unit'] = ingredient.ingredient_unit
            result_list.append(current_row)
    return result_list

# функция, формирующая список со строчками для сводной таблицы recipe|category 
def get_categories_and_recipe_db_table(recipes: List[RecipeBase]) -> list:
    result_list = []
    current_row = {'recipe_id': None, 'category_id' : None}
    categories = get_all_categories(recipes)
    for i in range(len(recipes)):
        current_row['recipe_id'] = i + 1
        for category in recipes[i].categories:
            current_row['category_id'] = search_string_in_string_list(categories, category)
            result_list.append(current_row)
    return result_list

def main():

    # всего на сайте russianfood ~177000 рецептов
    # создание объекта класса RecipeParser
    parser = RecipeParser(BASE_URL)
    # массив со всеми рецептами, которые удалось спарсить
    recipes = parser.parsing(10)
    
    for recipe in recipes:
        print(f"Название рецепта: {recipe.recipe_name}")
        print(f"Количество порций = {recipe.number_of_servings}")
        print(f"Время готовки = {recipe.cooking_time}")
        print(f"Описание:\n{recipe.description}")
        print("Ингредиенты:")
        for ingredient in recipe.ingredients:
            print(f"{ingredient.ingredient_name}, {ingredient.ingredient_quantity}, {ingredient.ingredient_unit}")
        print(f"Категории:")
        for category in recipe.categories:
            print(category, end=', ')

if __name__ == "__main__":
    main()