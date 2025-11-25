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
    # Добавляем комментарии к данным перед сохранением
    data_with_comments = []
    for i, item in enumerate(data):
        item_copy = item.copy()
        # Сохраняем комментарий только если он не пустой
        if i in st.session_state.comments and st.session_state.comments[i].strip():
            item_copy['comment'] = st.session_state.comments[i]
        else:
            # Не добавляем поле comment, если комментарий пустой
            pass
        data_with_comments.append(item_copy)
    
    with open("podarki.json", "w", encoding="utf-8") as f:
        json.dump(data_with_comments, f, ensure_ascii=False, indent=4)

def load_data():
    """Loads gift data from a JSON file."""
    try:
        with open("podarki.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Извлекаем комментарии из загруженных данных
        comments = {}
        gift_data = []
        for i, item in enumerate(data):
            # Проверяем, есть ли в элементе поле 'comment'
            if isinstance(item, dict) and 'comment' in item:
                comment = item.pop('comment', '')  # Извлекаем комментарий из словаря
                if comment and comment.strip():  # Сохраняем только непустые комментарии
                    comments[i] = comment
                else:
                    # Добавляем пустой комментарий, если поле было, но пустое
                    comments[i] = ""
            else:
                # Добавляем пустой комментарий, если поле отсутствовало
                comments[i] = ""
            gift_data.append(item)
        
        # Обновляем состояние комментариев
        st.session_state.comments = comments
        
        return gift_data
    except (FileNotFoundError, json.JSONDecodeError):
        return []


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
if "comments" not in st.session_state:
    st.session_state.comments = {}  # Словарь для хранения комментариев {index: comment}
if "editing_comment" not in st.session_state:
    st.session_state.editing_comment = {}  # Словарь для отслеживания режима редактирования {index: True/False}
if "driver" not in st.session_state:
    st.session_state.driver = None

# После загрузки данных убедимся, что комментарии из файла загружены в состояние
if "gift_data" in st.session_state and hasattr(st.session_state, 'comments_loaded') == False:
    # Проверим, есть ли уже комментарии в состоянии (это может произойти при первом запуске)
    if not st.session_state.comments:
        # Если комментариев нет, инициализируем их из данных, если они были загружены в load_data
        # Это будет происходить один раз при старте приложения
        pass  # load_data уже устанавливает st.session_state.comments при загрузке
    
    # Пометим, что комментарии уже были загружены
    st.session_state.comments_loaded = True


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

            # Сохраняем начальное количество элементов для корректного добавления комментариев
            initial_count = len(st.session_state.gift_data)

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
                    # Добавляем пустой комментарий для нового элемента
                    new_index = initial_count + i
                    st.session_state.comments[new_index] = ""
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
        cols = st.columns([1, 3, 1, 2, 1, 1, 1, 1])  # Добавляем еще одну колонку для комментариев

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

        # Кнопка для удаления
        if cols[5].button("Удалить", key=f"delete_{i}"):
            indices_to_delete.append(i)

        # Кнопка для замены
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

        # Кнопка для комментария
        comment_key = f"comment_btn_{i}"
        # Показываем разные значки в зависимости от наличия комментария
        if i in st.session_state.comments and st.session_state.comments[i].strip():
            # Если комментарий есть, показываем закрашенный значок
            comment_icon = "💬✓"
        else:
            # Если комментария нет, показываем обычный значок
            comment_icon = "💬"
        
        comment_button = cols[7].button(comment_icon, key=comment_key)
        
        if comment_button:
            st.session_state.editing_comment[i] = not st.session_state.get(f"editing_comment_{i}", False)

        # Отображение комментария, если он есть
        if i in st.session_state.comments and st.session_state.comments[i].strip():
            # Используем стиль, чтобы сделать комментарий менее заметным и компактным
            st.markdown(f'<div style="margin-top: 5px; font-size: 0.85em; color: #666; word-break: break-word; max-width: 100%; overflow-wrap: break-word;"><span style="font-weight: bold;">💬</span> {st.session_state.comments[i]}</div>', unsafe_allow_html=True)

        # Поле для редактирования комментария
        if st.session_state.editing_comment.get(i, False):
            comment_input_key = f"comment_input_{i}"
            current_comment = st.session_state.comments.get(i, "")
            new_comment = st.text_area("Комментарий:", value=current_comment, key=comment_input_key, height=70)
            
            save_comment_key = f"save_comment_{i}"
            if st.button("Сохранить комментарий", key=save_comment_key):
                st.session_state.comments[i] = new_comment
                st.session_state.editing_comment[i] = False
                save_data(st.session_state.gift_data)  # Сохраняем данные
                st.rerun()  # Обновляем страницу для отображения изменений

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

                    # Сохраняем комментарий до замены элемента
                    comment_for_transfer = st.session_state.comments.get(i, "")
                    
                    # Save chosen alternative (with price if found)
                    st.session_state.gift_data[i] = alt_item
                    if i in st.session_state.alternatives:
                        del st.session_state.alternatives[i]
                    
                    # Восстанавливаем комментарий для нового элемента
                    if comment_for_transfer:
                        st.session_state.comments[i] = comment_for_transfer
                    elif i in st.session_state.comments:
                        # Удаляем старый комментарий, если его больше нет
                        del st.session_state.comments[i]
                    
                    save_data(st.session_state.gift_data)
                    st.rerun()
            st.write("---")

    if indices_to_delete:
        for index in sorted(indices_to_delete, reverse=True):
            del st.session_state.gift_data[index]
            if index in st.session_state.alternatives:
                del st.session_state.alternatives[index]
            # Удаляем комментарий, если он существовал для этого индекса
            if index in st.session_state.comments:
                del st.session_state.comments[index]
            # Удаляем режим редактирования комментария, если он был
            if index in st.session_state.editing_comment:
                del st.session_state.editing_comment[index]
            # Переносим комментарии с последующих индексов на один назад
            # чтобы соответствовать новым индексам после удаления
            new_comments = {}
            new_editing_comment = {}
            for k, v in st.session_state.comments.items():
                if k > index:
                    new_comments[k - 1] = v
                else:
                    new_comments[k] = v
            for k, v in st.session_state.editing_comment.items():
                if k > index:
                    new_editing_comment[k - 1] = v
                else:
                    new_editing_comment[k] = v
            st.session_state.comments = new_comments
            st.session_state.editing_comment = new_editing_comment
            save_data(st.session_state.gift_data)
            st.rerun()

else:
    st.info("Здесь появится таблица с подарками после парсинга.")

# Close the browser when the app is done
if st.session_state.driver is not None:
    # This is tricky in Streamlit's lifecycle. A proper solution might involve atexit or a manual button.
    # For now, we rely on the user closing the app which will terminate the process.
    pass
