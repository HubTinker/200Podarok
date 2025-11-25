from bs4 import BeautifulSoup
import re

# Читаем HTML файл
with open('debug_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

soup = BeautifulSoup(content, 'html.parser')

# Находим все карточки товаров
cards = soup.find_all('article', {'data-auto': 'searchOrganic'})
print(f'Найдено карточек: {len(cards)}')

if cards:
    # Берем первую карточку для анализа
    first_card = cards[0]
    print('\n=== СТРУКТУРА ПЕРВОЙ КАРТОЧКИ ===')
    print(first_card.prettify()[:200])  # Показываем начало структуры
    
    print('\n=== LOOKING FOR LINKS WITH TEXT INSIDE ===')
    # Ищем все ссылки внутри карточки
    links = first_card.find_all('a')
    for i, link in enumerate(links):
        link_text = link.get_text(strip=True)
        if link_text:  # Показываем только ссылки с текстом
            safe_text = link_text[:50].encode('ascii', errors='ignore').decode('ascii')
            print(f'Link {i+1}: {repr(safe_text)}...')
            print(f'  href: {link.get("href", "N/A")}')
            print(f'  class: {link.get("class", "N/A")}')
            print(f'  data-zone-name: {link.get("data-zone-name", "N/A")}')
    
    print('\n=== LOOKING FOR HEADINGS AND TEXT ELEMENTS ===')
    # Ищем возможные заголовки
    titles = first_card.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'span', 'div'])
    for i, title in enumerate(titles):
        title_text = title.get_text(strip=True)
        if len(title_text) > 5:  # Показываем только с достаточным количеством текста
            safe_text = title_text[:50].encode('ascii', errors='ignore').decode('ascii')
            print(f'Element {i+1}: {title.name} class={title.get("class", "N/A")} data-auto={title.get("data-auto", "N/A")}')
            print(f'  Text: {repr(safe_text)}...')
    
    print('\n=== LOOKING FOR ELEMENTS WITH data-zone-name=title ATTRIBUTES ===')
    title_elements = first_card.find_all(attrs={'data-zone-name': 'title'})
    for i, elem in enumerate(title_elements):
        elem_text = elem.get_text(strip=True)
        safe_text = elem_text[:100].encode('ascii', errors='ignore').decode('ascii') if elem_text else ""
        print(f'Element with data-zone-name=title {i+1}: {repr(safe_text) if elem_text else "No text"}')
        print(f'  Tag: {elem.name}')
        print(f' href: {elem.get("href", "N/A")}')
        print(f' class: {elem.get("class", "N/A")}')