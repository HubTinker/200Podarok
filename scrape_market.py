import json
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import quote


def get_search_url(query):
    """Constructs a Yandex Market search URL."""
    return f"https://market.yandex.ru/search?text={quote(query)}"


def setup_driver():
    """Sets up the Chrome webdriver."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1200")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Error setting up webdriver: {e}")
        print("Please ensure you have Google Chrome installed.")
        return None


def scrape_yandex_market_selenium(driver, gift_name):
    """
    Searches for a gift on Yandex Market using Selenium and returns the name, price, URL, and image URL of the first result.
    """
    search_url = get_search_url(gift_name)

    try:
        print(f"Loading search page for '{gift_name}'...")
        driver.get(search_url)
        # Wait for the product cards to be loaded.
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # It's good practice to wait a bit for all dynamic content to load
        time.sleep(2)
        body = driver.find_element(By.TAG_NAME, "body")
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(body.get_attribute("outerHTML"))
        print("Page HTML saved to debug_page.html for inspection.")
    except Exception as e:
        print(f"Error loading page or finding element for '{gift_name}': {e}")
        return None, None, None, None

    soup = BeautifulSoup(driver.page_source, "html.parser")

    print(f"Looking for product cards for '{gift_name}'...")

    # Попробуем разные возможные селекторы для поиска карточек товаров
    product_card = soup.find("article", {"data-auto": "searchOrganic"})
    if not product_card:
        print(
            f"Could not find product card with 'data-auto=searchOrganic' for '{gift_name}'"
        )
        # Попробуем другой селектор
        product_card = soup.find("div", {"data-zone-name": "item"})
        if not product_card:
            print(
                f"Could not find product card with 'data-zone-name=item' for '{gift_name}'"
            )
            # Попробуем ещё один селектор
            product_card = soup.find(
                "div", {"class": lambda x: x and "snippet-card" in x}
            )
            if not product_card:
                print(
                    f"Could not find product card with class containing 'snippet-card' for '{gift_name}'"
                )
                # Попробуем найти все карточки товаров
                all_cards = soup.find_all(
                    "div",
                    {
                        "class": lambda x: x
                        and ("card" in x or "product" in x or "item" in x)
                    },
                )
                print(f"Found {len(all_cards)} potential product cards")
                if all_cards:
                    product_card = all_cards[0]  # Берём первую карточку
                    print(f"Using first card as product card for '{gift_name}'")
                else:
                    print(f"Could not find any product card for '{gift_name}'")
                    return None, None, None, None
            else:
                print(
                    f"Found product card with class containing 'snippet-card' for '{gift_name}'"
                )
        else:
            print(f"Found product card with 'data-zone-name=item' for '{gift_name}'")
    else:
        print(f"Found product card with 'data-auto=searchOrganic' for '{gift_name}'")

    # Extract the product name
    name = gift_name  # Начинаем с поискового запроса на случай, если не найдем реальное имя

    # Ищем элемент с data-zone-name="title" - это основной источник названия товара
    title_element = product_card.find(attrs={"data-zone-name": "title"})
    if title_element:
        name = title_element.get_text(strip=True)
        # Убираем лишние символы вроде запятых и т.п. в конце
        name = re.sub(r"[,\.\-\s]+$", "", name)
    else:
        # Если не найден элемент с data-zone-name="title", пробуем другие селекторы
        # Попробуем разные селекторы для поиска названия
        name_tag = product_card.find("h3", {"data-auto": "snippet-title"})
        if not name_tag:
            # Ищем заголовок внутри ссылки с data-zone-name=title
            title_zone = product_card.find("a", {"data-zone-name": "title"})
            if title_zone:
                # Проверяем внутри этой ссылки наличие заголовков
                name_tag = title_zone.find(["h3", "h4", "h5", "span", "div"])
                if not name_tag:
                    # Если нет заголовков, используем текст самой ссылки
                    name = title_zone.get_text(strip=True)
            if not name_tag and not name:
                # Ищем тег с классом, содержащим 'title' или 'name'
                name_tag = product_card.find(
                    ["h1", "h2", "h3", "h4", "h5", "span", "div"],
                    {
                        "class": lambda x: x
                        and ("title" in x or "name" in x or "product" in x)
                    },
                )
        if not name_tag and not name:
            # Ищем внутри всей карточки тег с текстом, который может быть названием
            name_tag = product_card.find(
                ["span", "div"], {"class": lambda x: x and "link" in x and "title" in x}
            )
        if not name_tag and not name:
            # Последняя попытка - любой тег с осмысленным текстом
            all_text_elements = product_card.find_all(
                ["span", "div", "a", "h1", "h2", "h3", "h4", "h5"]
            )
            for element in all_text_elements:
                element_text = element.get_text(strip=True)
                if (
                    element_text
                    and len(element_text) > 5
                    and not element_text.startswith("https")
                    and element_text != gift_name
                ):
                    name = element_text
                    break

        # Если нашли name_tag, извлекаем текст из него
        if name_tag:
            name = name_tag.get_text(strip=True)

    print(f"Found name: '{name}' for '{gift_name}'")

    price = None
    # Prices can be in different tags, let's try a few selectors
    price_tag = product_card.find("span", {"data-auto": "price-value"})
    if not price_tag:
        price_tag = product_card.find("div", {"data-auto": "price-value"})
    if not price_tag:
        # Попробуем найти цену с помощью класса
        price_tag = product_card.find("span", {"class": lambda x: x and "price" in x})
    if not price_tag:
        price_tag = product_card.find("div", {"class": lambda x: x and "price" in x})
    if not price_tag:
        # Попробуем найти цену в дочерних элементах
        all_price_elements = product_card.find_all(
            ["span", "div"],
            {"class": lambda x: x and ("price" in x or "cost" in x or "value" in x)},
        )
        for element in all_price_elements:
            element_text = element.get_text(strip=True)
            if re.search(r"\d", element_text):  # Проверяем, есть ли цифры в тексте
                price_tag = element
                break
    if not price_tag:
        print(f"Could not find price tag for '{gift_name}'")
    else:
        price_text = price_tag.get_text(strip=True)
        # Remove all non-digit characters to get a clean price number
        price = re.sub(r"\D", "", price_text)
        print(f"Found price: '{price}' for '{gift_name}'")

    purchase_url = None
    link_tag = product_card.find("a", {"data-zone-name": "title"}, href=True)
    if not link_tag:
        # Fallback to the link that contains the title
        link_tag = product_card.find("a", href=re.compile(r"/product/"))
        if not link_tag:
            # Попробуем найти ссылку с классом, содержащим 'link'
            link_tag = product_card.find(
                "a", {"class": lambda x: x and "link" in x}, href=True
            )
            if not link_tag:
                # Попробуем найти ссылку с data-uid
                link_tag = product_card.find("a", {"data-uid": True}, href=True)
                if not link_tag:
                    # Попробуем найти любую ссылку внутри карточки
                    link_tag = product_card.find("a", href=True)
                    if not link_tag:
                        print(f"Could not find URL for '{gift_name}'")
                    else:
                        print(f"Found fallback URL link for '{gift_name}'")
                else:
                    print(f"Found URL link with 'data-uid' for '{gift_name}'")
            else:
                print(f"Found URL link with 'link' in class for '{gift_name}'")
        else:
            print(f"Found URL link with '/product/' in href for '{gift_name}'")
    else:
        print(f"Found title URL link for '{gift_name}'")

    if link_tag:
        url = link_tag["href"]
        if url.startswith("/"):
            purchase_url = "https://market.yandex.ru" + url
        else:
            purchase_url = url
        print(f"Final URL: '{purchase_url}' for '{gift_name}'")

    image_url = None
    # Find the image tag
    img_tag = product_card.find("img", src=True)
    if img_tag:
        image_url = img_tag["src"]
        # Ensure the URL is absolute
        if image_url.startswith("//"):
            image_url = "https:" + image_url
        print(f"Found image URL: '{image_url}' for '{gift_name}'")
    else:
        print(f"Could not find image for '{gift_name}'")

    return name, price, purchase_url, image_url


def scrape_yandex_market_alternatives(driver, query, num_results=5):
    """
    Searches for a gift on Yandex Market and returns a list of alternative results.
    """
    search_url = get_search_url(query)
    results = []

    try:
        print(f"Loading search page for alternatives to '{query}'...")
        driver.get(search_url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "article[data-auto='searchOrganic'] , div[data-zone-name='item']",
                )
            )
        )
        time.sleep(2)
    except Exception as e:
        print(f"Error loading page or finding elements for '{query}': {e}")
        return results

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Ищем все карточки товаров
    product_cards = soup.find_all("article", {"data-auto": "searchOrganic"})
    if not product_cards:
        product_cards = soup.find_all("div", {"data-zone-name": "item"})

    print(f"Found {len(product_cards)} product cards for '{query}'.")

    for card in product_cards[:num_results]:
        name, price, purchase_url, image_url = None, None, None, None

        # Extract product name
        title_element = card.find(attrs={"data-zone-name": "title"})
        if title_element:
            name = title_element.get_text(strip=True)
            name = re.sub(r"[,\.\-\s]+$", "", name)

        # Extract price
        price_tag = card.find("span", {"data-auto": "price-value"})
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            price = re.sub(r"\D", "", price_text)

        # Extract purchase URL
        link_tag = card.find("a", {"data-zone-name": "title"}, href=True)
        if not link_tag:
            # broad fallback: any link inside card
            link_tag = card.find("a", href=True)

        if link_tag and link_tag.has_attr("href"):
            url = link_tag["href"]
            if url.startswith("/"):
                purchase_url = "https://market.yandex.ru" + url
            else:
                purchase_url = url
        else:
            purchase_url = None

        # Extract image URL
        img_tag = card.find("img", src=True)
        if img_tag and img_tag.has_attr("src"):
            image_url = img_tag["src"]
            if image_url.startswith("//"):
                image_url = "https:" + image_url

        # Keep card as an alternative if we at least have a name and a URL.
        # Prices or images may be missing on some cards but they're still valid alternatives.
        # If at least a name is present, keep the card as an alternative.
        # It's acceptable for price or URL to be missing; we'll still show the item.
        if name:
            results.append(
                {
                    "name": name,
                    "price": price,
                    "purchaseUrl": purchase_url,
                    "imageUrl": image_url,
                    "query": query,
                }
            )
            print(
                f"  -> Appended alternative: name='{name}', price='{price}', url='{purchase_url[:80] if purchase_url else 'None'}'"
            )
        else:
            print(
                f"  -> Skipped card (missing name or url) name='{name}', url='{purchase_url}'"
            )

    print(f"Returning {len(results)} alternatives for '{query}'.")
    return results


def scrape_price_from_product_page(driver, product_url):
    """
    Given a product page URL on market.yandex.ru, try to extract the product price.
    Returns price string (digits only) or None.
    """
    try:
        print(f"Loading product page to get price: {product_url}")
        driver.get(product_url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(1)
    except Exception as e:
        print(f"Error loading product page: {e}")
        return None

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Try typical selectors for price on product page
    price_tag = soup.find("span", {"data-auto": "price-value"})
    if not price_tag:
        price_tag = soup.find("div", {"data-auto": "price-value"})
    if not price_tag:
        # try common classes
        price_tag = soup.find("span", {"class": lambda x: x and "price" in x})

    if price_tag:
        price_text = price_tag.get_text(strip=True)
        price = re.sub(r"\D", "", price_text)
        print(f"Found product page price: {price}")
        return price if price else None

    # As a final attempt, search for any numeric text that looks like a price
    text = soup.get_text(separator="\n")
    m = re.search(r"(\d[\d\s]*\d)\s*₽|(?:Price[:\s])?(\d[\d\s]*\d)", text)
    if m:
        candidate = m.group(1) or m.group(2)
        candidate = re.sub(r"\D", "", candidate)
        print(f"Found fallback price: {candidate}")
        return candidate

    print("Could not determine price on product page")
    return None


def main():
    """
    Main function to read gifts, scrape Yandex Market, and save to JSON.
    """
    try:
        with open("unique_gifts.txt", "r", encoding="utf-8") as f:
            gift_names = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Error: unique_gifts.txt not found.")
        return

    print("Setting up browser driver...")
    driver = setup_driver()
    if not driver:
        return

    print("Driver setup complete.")

    # Тестовый запуск: обрабатываем только последние 5 товаров для отладки
    gift_names = gift_names[-5:]

    scraped_data = []
    image_id_counter = 1

    for gift_name in gift_names:
        print(f"Scraping '{gift_name}'...")
        name, price, url, image_url = scrape_yandex_market_selenium(driver, gift_name)

        if price and url:
            scraped_data.append(
                {
                    "name": name,
                    "price": price,
                    "purchaseUrl": url,
                    "imageUrl": image_url,
                }
            )
            print(
                f"  -> Found name: {name}, price: {price}, URL: {url}, Image: {image_url}"
            )
        else:
            scraped_data.append(
                {
                    "name": gift_name,
                    "price": None,
                    "purchaseUrl": None,
                    "imageUrl": None,
                }
            )
            print("  -> Could not find name, price, URL or image.")

        image_id_counter += 1
        # A small delay between requests to be polite
        time.sleep(1)

    driver.quit()

    with open("scraped_gifts_selenium.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=4)

    print("\nScraping complete. Results saved to scraped_gifts_selenium.json")


if __name__ == "__main__":
    main()
