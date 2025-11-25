import streamlit as st
import pandas as pd
import json
from scrape_market import (
    scrape_yandex_market_selenium,
    setup_driver,
    scrape_yandex_market_alternatives,
    scrape_price_from_product_page,
)
import time
import os
import re

# --- Page Config ---
st.set_page_config(page_title="Подбор подарков", page_icon="🎁", layout="wide")


# --- Functions ---
def save_data(data):
    """Saves the current gift data to a JSON file."""
    with open("podarki.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_data():
    """Loads gift data from a JSON file."""
    try:
        with open("podarki.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# --- State Management ---
if "gift_data" not in st.session_state:
    st.session_state.gift_data = load_data()
if "alternatives" not in st.session_state:
    st.session_state.alternatives = (
        {}
    )  # Словарь для хранения альтернатив {index: [items]}
if "driver" not in st.session_state:
    st.session_state.driver = None


# --- UI ---
st.title("🎁 Парсер подарков с Яндекс.Маркета")

st.sidebar.header("Добавить идеи для подарков")
new_gift_ideas = st.sidebar.text_area(
    "Введите по одному названию на строку:", height=200
)

if st.sidebar.button("Начать парсинг"):
    if new_gift_ideas:
        gift_list = [
            idea.strip() for idea in new_gift_ideas.split("\n") if idea.strip()
        ]

        st.info("Идет настройка браузера...")
        if st.session_state.driver is None:
            st.session_state.driver = setup_driver()

        if st.session_state.driver:
            st.success("Браузер готов. Начинаю парсинг...")
            progress_bar = st.progress(0)

            for i, gift_name in enumerate(gift_list):
                st.write(f"Ищу: '{gift_name}'...")
                name, price, url, image_url = scrape_yandex_market_selenium(
                    st.session_state.driver, gift_name
                )

                if name:
                    st.session_state.gift_data.append(
                        {
                            "name": name,
                            "price": price,
                            "purchaseUrl": url,
                            "imageUrl": image_url,
                            "query": gift_name,
                        }
                    )
                    st.write(f"✅ Найдено: {name}")
                else:
                    st.write(f"❌ Не удалось найти '{gift_name}'")

                progress_bar.progress((i + 1) / len(gift_list))
                time.sleep(1)

            st.success("Парсинг завершен!")
            save_data(st.session_state.gift_data)
        else:
            st.error(
                "Не удалось запустить браузер. Проверьте, установлен ли Google Chrome."
            )
    else:
        st.sidebar.warning("Пожалуйста, введите хотя бы одну идею для подарка.")

st.header("Список найденных подарков")

if st.session_state.gift_data:
    total_items = len(st.session_state.gift_data)
    st.markdown(f"**Всего позиций: {total_items}**")

    header_cols = st.columns([1, 3, 1, 2, 1, 1, 1])
    header_cols[0].write("**Фото**")
    header_cols[1].write("**Название**")
    header_cols[2].write("**Цена (₽)**")
    header_cols[3].write("**Запрос**")
    header_cols[4].write("**Ссылка**")
    header_cols[5].write("**Действие**")
    header_cols[6].write("")  # Placeholder for replace button

    indices_to_delete = []
    for i, item in enumerate(st.session_state.gift_data):
        cols = st.columns([1, 3, 1, 2, 1, 1, 1])

        # Display main item
        if item.get("imageUrl"):
            if re.match(r"^https?://", item["imageUrl"]):
                cols[0].image(item["imageUrl"], width=160)
            else:
                cols[0].write("Нет фото")
        else:
            cols[0].write("Нет фото")
        cols[1].write(item.get("name", "N/A"))
        cols[2].write(item.get("price", "N/A"))
        cols[3].write(item.get("query", "N/A"))
        cols[4].link_button("Купить", item.get("purchaseUrl", "#"))

        if cols[5].button("Удалить", key=f"delete_{i}"):
            indices_to_delete.append(i)

        if cols[6].button("Заменить", key=f"replace_{i}"):
            query = item.get("query", item.get("name"))
            with st.spinner(f"Ищу варианты для '{query}'..."):
                if st.session_state.driver is None:
                    st.session_state.driver = setup_driver()

                if st.session_state.driver:
                    st.session_state.alternatives[i] = (
                        scrape_yandex_market_alternatives(
                            st.session_state.driver, query
                        )
                    )
                else:
                    st.error("Браузер не запущен.")
            pass  # Убираем rerun, чтобы избежать лишних перезагрузок

        # Display alternatives if they exist
        if i in st.session_state.alternatives and st.session_state.alternatives[i]:
            st.write("---")
            st.write(f"**Варианты замены для \"{item.get('name')}\":**")

            for alt_idx, alt_item in enumerate(st.session_state.alternatives[i]):
                alt_cols = st.columns(5)  # Создаем колонки прямо в цикле

                if alt_item.get("imageUrl"):
                    alt_cols[0].image(alt_item["imageUrl"], width=100)
                else:
                    alt_cols[0].write("Нет фото")

                alt_cols[1].write(alt_item.get("name", "N/A"))
                alt_price = alt_item.get("price")
                if alt_price:
                    alt_cols[2].write(f"{alt_price} ₽")
                else:
                    alt_cols[2].write("N/A")
                alt_cols[3].link_button("Ссылка", alt_item.get("purchaseUrl", "#"))

                if alt_cols[4].button("Выбрать", key=f"select_{i}_{alt_idx}"):
                    # Ensure price is determined for the selected alternative
                    if not alt_item.get("price"):
                        with st.spinner("Определяю цену для выбранного товара..."):
                            # Try product page price if URL exists
                            if st.session_state.driver is None:
                                st.session_state.driver = setup_driver()

                            if st.session_state.driver:
                                price = None
                                if alt_item.get("purchaseUrl"):
                                    price = scrape_price_from_product_page(
                                        st.session_state.driver,
                                        alt_item.get("purchaseUrl"),
                                    )

                                # If price still missing, fallback to running a search by name
                                if not price and alt_item.get("name"):
                                    _, price, url, image_url = (
                                        scrape_yandex_market_selenium(
                                            st.session_state.driver,
                                            alt_item.get("name"),
                                        )
                                    )
                                    # update fields if found
                                    if url:
                                        alt_item["purchaseUrl"] = url
                                    if image_url:
                                        alt_item["imageUrl"] = image_url

                                if price:
                                    alt_item["price"] = price
                                else:
                                    st.warning(
                                        "Не удалось определить цену для выбранного варианта."
                                    )
                            else:
                                st.error("Браузер не запущен — цена не определена.")

                    # Save chosen alternative (with price if found)
                    st.session_state.gift_data[i] = alt_item
                    if i in st.session_state.alternatives:
                        del st.session_state.alternatives[i]
                    save_data(st.session_state.gift_data)
                    st.rerun()
            st.write("---")

    if indices_to_delete:
        for index in sorted(indices_to_delete, reverse=True):
            del st.session_state.gift_data[index]
            if index in st.session_state.alternatives:
                del st.session_state.alternatives[index]
        save_data(st.session_state.gift_data)
        st.rerun()

else:
    st.info("Здесь появится таблица с подарками после парсинга.")

# Close the browser when the app is done
if st.session_state.driver is not None:
    # This is tricky in Streamlit's lifecycle. A proper solution might involve atexit or a manual button.
    # For now, we rely on the user closing the app which will terminate the process.
    pass
