import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin

BASE_URL = "https://www.russianfood.com/recipes/recipe.php" 

# функция получения html страницы по url
def get_page(url):

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

# функция получения ингредиентов для рецепта из преобразованной html страницы
def get_ingredients(soup):
    
    # ищем класс 'ingr' с тэгом 'table'
    ingredients_table = soup.find('table', class_='ingr')  
        
    ingredients = []
    if not ingredients_table:
        return []
    # разбиваем таблицу ингредиентов на строки
    rows = ingredients_table.find_all('tr')

    rows.pop(0) # Это заголовок "Продукты"

    # одна строка - один инргедиент в рецепте
    for row in rows:
        # разбиваем строку на ячейки
        cells = row.find_all('td')
        ingredient = {}
        # на сайте оказалось 2 формата рецептов: 
        # 1) где все красиво разбито: один тэг на название, другой на количество, третий на единицы измерения
        # 2) где все просто в одну строку намешано :(
        # поэтому идет разделение на старый формат с 3 тегами (первые 115000 рецептов)
        if len(cells) == 3:
            ingredient = parse_old_format(cells)
        # и на новый с 1 тэгом (после 115000 рецептов)
        elif len(cells) == 1:
            ingredient = parse_new_format(cells[0])
        # других я еще не встречал на этом сайте, поэтому кидаем исключение
        else:
            raise RuntimeError("Unknown format of recipe")
        ingredients.append(ingredient)
    return ingredients

# парсинг старого формата рецептов
def parse_old_format(cells):
    # получаем название ингридиента
    name_cell = cells[0]
    name_span = name_cell.find('span')
    ingredient_name = name_span.get_text(strip=True) if name_span else name_cell.get_text(strip=True)
    # получаем его количество
    quantity_cell = cells[1]
    quantity = quantity_cell.get_text(strip=True)
    # получааем единицы измерения
    unit_cell = cells[2]
    unit_nobr = unit_cell.find('nobr')
    unit = unit_nobr.get_text(strip=True) if unit_nobr else unit_cell.get_text(strip=True)
    
    return {
        'name': ingredient_name,
        'quantity': quantity,
        'unit': unit,
        'format': 'old'  
    }

# парсинг нового формата рецептов
def parse_new_format(cell):

    
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
        return {
            'name': full_text,
            'quantity': '',
            'unit': '',
            'format': 'new_unsplit'
        }
    
    if len(parts) == 2:
        # удаляем лишние пробелы, если они есть
        name = parts[0].strip()
        quantity_unit = parts[1].strip()

        quantity, unit = extract_quantity_and_unit(quantity_unit)
        
        return {
            'name': name,
            'quantity': quantity,
            'unit': unit,
            'format': 'new'
        }
    
    return None

# функция для разбиения количества и единиц измерения из новой записи ингридиента на сайте
def extract_quantity_and_unit(quantity_unit):
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

def parsing():

    recipes = []
    while True:
        # ввод айдишника рецепта
        print('Введите номер рецепта, который хотите спарсить.\nЕсли хотите остановить выполнение программы введите 0\nid = ', end='')
        page_num = int(input())
        if page_num == 0:
            break
        # собираем готовый url
        url = f"{BASE_URL}?rid={page_num}"
        print(f"Парсинг страницы: {url}")
        
        # получаем html страницу по url
        html = get_page(url)
        if not html:
            continue
            
        soup = BeautifulSoup(html, 'lxml')
        
        # парсим преобразованную html страницу и получаем словарь с рецептом
        ingredients_for_recipe = get_ingredients(soup)
        if ingredients_for_recipe:
            recipes.append(ingredients_for_recipe)
        print(*ingredients_for_recipe)
        print('Для продолжения нажмите любую клавишу...')
        input()
    return recipes

def main():

    # всего на сайте russianfood ~177000 рецептов

    # массив со всеми рецептами, которые удалось спарсить
    recipes = parsing()
    
    # запись в json файл
    with open('recipes.json', 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

    print(f"Сохранено рецептов: {len(recipes)}")

if __name__ == "__main__":
    main()