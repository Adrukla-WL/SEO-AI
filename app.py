"""
Магическая SEO Студия - Главное приложение Streamlit
"""

import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from services import sheets, parser, ai_engine, export

load_dotenv()

# --- Конфигурация и Тема ---
st.set_page_config(
    page_title="Magic SEO AI",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

# Функция для применения темы
def apply_theme(is_dark):
    """Инъекция CSS для переключения режимов день/ночь."""
    if is_dark:
        st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(135deg, #1e1e2f 0%, #121212 100%);
                color: #ffffff;
            }
            /* Обеспечиваем контраст для всех текстов */
            .stApp p, .stApp span, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3 {
                color: #ffffff !important;
            }
            .stSidebar {
                background-color: rgba(30, 30, 47, 0.95) !important;
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            }
            div[data-testid="stTitle"] h1 { color: #bb86fc !important; }
            .stButton>button {
                background-color: #6200ee;
                color: white !important;
                border-radius: 8px;
                border: none;
                transition: all 0.3s ease;
            }
            .stButton>button:hover {
                background-color: #3700b3;
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(98, 0, 238, 0.4);
            }
            /* Исправление цвета подсказок и вторичного текста */
            .stApp .stCaption {
                color: rgba(255, 255, 255, 0.7) !important;
            }
            </style>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            .stApp {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }
            .stButton>button {
                border-radius: 8px;
                transition: all 0.3s ease;
            }
            .stButton>button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            }
            </style>
            """, unsafe_allow_html=True)

# Инициализация состояния
if 'current_project_id' not in st.session_state:
    st.session_state.current_project_id = None
if 'project_data' not in st.session_state:
    st.session_state.project_data = []
if 'generation_active' not in st.session_state:
    st.session_state.generation_active = False

# Безопасность: Ключ API берется только из .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("Критическая ошибка: GEMINI_API_KEY не найден в файле .env")
    st.stop()

# --- Боковая панель (Sidebar) ---
with st.sidebar:
    st.title("✨ Magic SEO AI")
    
    # Переключатель темы
    is_dark_mode = st.toggle("Темный режим", value=True)
    apply_theme(is_dark_mode)
    
    st.divider()

    # Управление проектами
    st.subheader("📁 Проект")
    project_mode = st.radio("Режим", ["Выбрать существующий", "Создать новый"])

    if project_mode == "Выбрать существующий":
        sheet_id_input = st.text_input("ID Google Таблицы", help="Вставьте ID из URL таблицы")
        if st.button("Загрузить проект") and sheet_id_input:
            try:
                data = sheets.get_project_data(sheet_id_input)
                # Гарантируем наличие колонки "Выбрать" для всех строк
                for row in data:
                    if "Выбрать" not in row:
                        row["Выбрать"] = False
                st.session_state.project_data = data
                st.session_state.current_project_id = sheet_id_input
                st.success(f"Загружено строк: {len(data)}")
            except Exception as e: # pylint: disable=broad-exception-caught
                st.error(f"Ошибка загрузки: {e}")

    else: # Создать новый
        new_proj_name = st.text_input("Название нового проекта")
        if st.button("Создать проект") and new_proj_name:
            try:
                meta = sheets.create_project_sheet(new_proj_name)
                st.session_state.current_project_id = meta['id']
                st.session_state.project_data = []
                st.success(f"Проект создан! ID: {meta['id']}")
                st.info(
                    "Убедитесь, что у сервисного аккаунта есть доступ к этой таблице "
                    "(обычно доступ выдается автоматически при создании)."
                )
                st.markdown(f"[Открыть таблицу]({meta['url']})")
            except Exception as e: # pylint: disable=broad-exception-caught
                st.error(f"Ошибка создания: {e}")

        if st.button("❌ Очистить таблицу проекта", type="secondary"):
            if st.session_state.current_project_id:
                try:
                    # Очищаем в Google Sheets
                    sheets.replace_project_data(st.session_state.current_project_id, [])
                    # Очищаем локально
                    st.session_state.project_data = []
                    st.success("Таблица проекта полностью очищена!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка очистки: {e}")

    st.divider()

    # Глобальные действия
    action = st.selectbox(
        "⚡ Глобальное действие",
        [
            "Выбрать...",
            "Запуск парсера",
            "Генерация Meta-описаний",
            "Генерация текстов",
            "Экспорт"
        ]
    )

    st.divider()
    with st.expander("ℹ️ Помощь по доступу"):
        st.write("Если не получается создать проект:")
        st.write("1. Создайте таблицу вручную.")
        st.write("2. Дайте права Редактора этому email:")
        st.code("magic-seo@magic-seo-486911.iam.gserviceaccount.com")
        st.write("3. Вставьте ID таблицы в 'Выбрать существующий'.")

# --- Рабочая область (Main Area) ---
st.header("🛠 Рабочая область")

if st.session_state.current_project_id:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(
            f"ID проекта: {st.session_state.current_project_id} | "
            f"Всего строк: {len(st.session_state.project_data)}"
        )
    with col2:
        if st.button("🔄 Обновить данные"):
            data = sheets.get_project_data(
                st.session_state.current_project_id
            )
            for row in data:
                if "Выбрать" not in row:
                    row["Выбрать"] = False
            st.session_state.project_data = data
            st.rerun()

    st.subheader("📝 Данные проекта")
    st.info("💡 Подсказка: Чтобы удалить строку, выделите ее и нажмите кнопку 'Delete' на клавиатуре или используйте значок корзины внизу таблицы.")
    
    # Превращаем в DataFrame для более стабильной работы редактора
    df_for_editor = pd.DataFrame(st.session_state.project_data)
    
    # Если данных пока нет, создаем пустой DataFrame с нужными колонками
    if df_for_editor.empty:
        df_for_editor = pd.DataFrame(columns=["Выбрать", "Title", "Link", "Keywords", "Description", "New Description", "Text"])

    # Убеждаемся, что колонка "Выбрать" первая и имеет правильный тип
    if "Выбрать" in df_for_editor.columns:
        cols = ["Выбрать"] + [c for c in df_for_editor.columns if c != "Выбрать"]
        df_for_editor = df_for_editor[cols]
        df_for_editor["Выбрать"] = df_for_editor["Выбрать"].astype(bool)

    edited_df = st.data_editor(
        df_for_editor,
        num_rows="dynamic",
        use_container_width=True,
        key="project_editor"
    )
    
    # Для всей остальной логики используем список словарей
    edited_data = edited_df.to_dict('records')
    
    # ВАЖНО: Мы НЕ обновляем st.session_state.project_data = edited_data на каждом шаге,
    # так как это вызывает "прыжки" фокуса и сброс ввода при каждом символе.
    # Мы используем edited_data только при сохранении.

    if st.button("💾 Сохранить все изменения"):
        if st.session_state.current_project_id:
            # Превращаем результат редактора в список словарей (если это DataFrame)
            if isinstance(edited_data, pd.DataFrame):
                data_to_save = edited_data.to_dict('records')
            else:
                # Если уже список (бывает при определенных конфигах streamlit)
                data_to_save = edited_data

            with st.spinner("Сохранение в Google Таблицы..."):
                try:
                    sheets.replace_project_data(
                        st.session_state.current_project_id, data_to_save
                    )
                    # Только ПОСЛЕ успешного сохранения в Sheets обновляем мастер-состояние
                    st.session_state.project_data = data_to_save
                    st.success("Изменения успешно сохранены!")
                    # Сбрасываем ключ редактора, чтобы он перечитал новые данные
                    # (Но в Streamlit это иногда не нужно, просто st.rerun() достаточно)
                    st.rerun()
                except Exception as e: # pylint: disable=broad-exception-caught
                    st.error(f"Ошибка сохранения: {e}")

    # --- Инспекция контента (Expanders) ---
    st.divider()
    st.subheader("🔍 Просмотр контента")
    
    # Показываем только если есть данные
    if not df_for_editor.empty:
        for idx, row in df_for_editor.iterrows():
            has_desc = str(row.get("New Description", "")).strip()
            has_text = str(row.get("Text", "")).strip()
            
            if has_desc or has_text:
                title = row.get("Title", f"Строка {idx + 1}")
                with st.expander(f"📄 {title}"):
                    if has_desc:
                        st.markdown("### 📝 Meta Description")
                        st.markdown(row["New Description"])
                    if has_text:
                        if has_desc: st.divider()
                        st.markdown("### ✍️ Сгенерированный текст")
                        st.markdown(row["Text"])
            elif idx == 0 and not has_desc and not has_text:
                st.info("Здесь появятся развернутые тексты после их генерации.")
    else:
        st.info("Нет данных для отображения.")


    # Вспомогательная функция для проверки галочки
    def is_row_selected(row):
        val = row.get("Выбрать")
        if val is None: return False
        if isinstance(val, bool): return val
        s_val = str(val).strip().upper()
        return s_val in ["TRUE", "1", "YES", "ДА", "CHECKED", "V"]

    # Вспомогательная функция для проверки галочки (максимально гибкая)
    def check_if_selected(row):
        # Проверяем по ключу
        val = row.get("Выбрать")
        if val is True: return True
        if val is False: return False
        if val is None: return False
        
        # Если это строка (из Sheets иногда приходит как текст)
        s = str(val).strip().upper()
        if s in ["TRUE", "1", "YES", "ДА", "V", "X", "CHECKED"]: return True
        
        # Если вдруг ключ изменился или имеет пробелы
        for k, v in row.items():
            if "ВЫБРАТЬ" in str(k).upper().strip():
                if v is True or str(v).strip().upper() in ["TRUE", "1"]:
                    return True
        return False

    # --- Обработка действий (теперь edited_data доступна) ---
    st.divider()
    
    # Показываем статус выбора в реальном времени
    selected_count = sum(1 for r in edited_data if check_if_selected(r))
    
    # Всегда показываем статус, чтобы пользователь видел, что программа "жива"
    if selected_count > 0:
        st.success(f"🎯 Выбрано строк для генерации: {selected_count}")
    else:
        st.info("ℹ️ Ни одна строка не выбрана (AI будет заполнять только пустые ячейки).")
        pass
    
    if action == "Запуск парсера":
        st.info("Парсинг исходной страницы для поиска новых ссылок.")
        source_url = st.text_input("URL источника")
        
        # Инициализация флага остановки
        if 'parsing_active' not in st.session_state:
            st.session_state.parsing_active = False

        col_start, col_stop = st.columns(2)
        with col_start:
            start_btn = st.button("Начать парсинг", disabled=st.session_state.parsing_active)
        with col_stop:
            stop_btn = st.button("Остановить", disabled=not st.session_state.parsing_active)

        if stop_btn:
            st.session_state.parsing_active = False
            st.rerun()

        if start_btn and source_url:
            st.session_state.parsing_active = True
            with st.spinner("Парсим структуру сайта..."):
                res = parser.parse_source_page(source_url)
                
                if "error" in res:
                    st.error(res["error"])
                    st.session_state.parsing_active = False
                else:
                    links = res["links"]
                    existing_links = {
                        row.get("Link") for row in st.session_state.project_data
                    }
                    new_links = [l for l in links if l not in existing_links]
                    
                    if not new_links:
                        st.warning("Новых ссылок не обнаружено.")
                        st.session_state.parsing_active = False
                    else:
                        st.write(f"Найдено новых ссылок: {len(new_links)}. Начинаем сбор данных...")
                        
                        processed_rows = []
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        batch_size = 25
                        
                        for idx, link in enumerate(new_links):
                            if not st.session_state.parsing_active:
                                st.warning("Парсинг остановлен пользователем.")
                                break
                            
                            percent = int((idx + 1) / len(new_links) * 100)
                            status_text.text(f"Обработка {idx + 1} из {len(new_links)} ({percent}%): {link}")
                            meta = parser.fetch_page_metadata(link)
                            
                            if meta:
                                meta["Выбрать"] = False
                                meta["Keywords"] = ""
                                meta["New Description"] = ""
                                meta["Text"] = ""
                                processed_rows.append(meta)
                            
                            progress_bar.progress((idx + 1) / len(new_links))

                            # Сохранение пачкой каждые batch_size строк
                            if len(processed_rows) >= batch_size:
                                sheets.add_rows(st.session_state.current_project_id, processed_rows)
                                # Обновляем локальные данные, чтобы пользователь видел прогресс
                                st.session_state.project_data.extend(processed_rows)
                                processed_rows = [] # Очищаем батч
                        
                        # Сохраняем остаток
                        if processed_rows:
                            sheets.add_rows(st.session_state.current_project_id, processed_rows)
                            st.session_state.project_data.extend(processed_rows)
                        
                        st.session_state.parsing_active = False
                        st.success(f"Парсинг успешно завершен! Добавлено страниц: {len(new_links)}")
                        st.balloons()
                        st.info("💡 Следующий шаг: Выберите 'Генерация Meta-описаний' для создания SEO-тегов.")
                        st.rerun()

    elif action == "Генерация Meta-описаний":
        col_gen_start, col_gen_stop = st.columns(2)
        with col_gen_start:
            start_gen_btn = st.button("Запустить генерацию", disabled=st.session_state.generation_active)
        with col_gen_stop:
            stop_gen_btn = st.button("Остановить", disabled=not st.session_state.generation_active)

        if stop_gen_btn:
            st.session_state.generation_active = False
            st.rerun()

        if start_gen_btn:
            st.session_state.generation_active = True
            ai_engine.configure_gemini(GEMINI_API_KEY)
            
            data_to_process = edited_data.to_dict('records') if isinstance(edited_data, pd.DataFrame) else edited_data
            
            # Находим индексы строк для обработки
            target_indices = [i for i, r in enumerate(data_to_process) if check_if_selected(r)]
            
            if not target_indices:
                # Если ничего не выбрано - берем пустые
                target_indices = [
                    i for i, r in enumerate(data_to_process) 
                    if not str(r.get("New Description", "")).strip()
                ]
                st.info(f"Режим: Заполнение пустых ячеек ({len(target_indices)} строк).")
            else:
                st.info(f"Режим: Генерация для {len(target_indices)} выбранных строк.")

            if not target_indices:
                st.warning("Нет строк для обработки. Выберите строки галочками или очистите ячейки 'New Description'.")
                st.session_state.generation_active = False
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                updates_count = 0
                
                for step, idx in enumerate(target_indices):
                    if not st.session_state.generation_active:
                        st.warning("Генерация остановлена пользователем.")
                        break
                    
                    row = data_to_process[idx]
                    percent = int((step + 1) / len(target_indices) * 100)
                    status_text.text(f"Обработка {step + 1} из {len(target_indices)} ({percent}%): {row.get('Title', 'No Title')}")
                    
                    title = row.get("Title", "")
                    kw = row.get("Keywords", "")
                    old_desc = row.get("Description", "")

                    new_text = ai_engine.generate_new_description(title, kw, old_desc)

                    sheets.update_row(st.session_state.current_project_id, idx, {"New Description": new_text})
                    row["New Description"] = new_text
                    row["Выбрать"] = False
                    updates_count += 1
                    
                    progress_bar.progress((step + 1) / len(target_indices))

                st.session_state.project_data = data_to_process
                st.session_state.generation_active = False
                st.success(f"Готово! Сгенерировано описаний: {updates_count}")
                st.rerun()

    elif action == "Генерация текстов":
        col_txt_start, col_txt_stop = st.columns(2)
        with col_txt_start:
            start_txt_btn = st.button("Запустить генерацию текстов", disabled=st.session_state.generation_active)
        with col_txt_stop:
            stop_txt_btn = st.button("Остановить", disabled=not st.session_state.generation_active)

        if stop_txt_btn:
            st.session_state.generation_active = False
            st.rerun()

        if start_txt_btn:
            st.session_state.generation_active = True
            ai_engine.configure_gemini(GEMINI_API_KEY)
            
            data_to_process = edited_data.to_dict('records') if isinstance(edited_data, pd.DataFrame) else edited_data
            
            selected_indices = [i for i, r in enumerate(data_to_process) if is_row_selected(r)]
            
            if selected_indices:
                target_indices = selected_indices
                st.info(f"Режим: Генерация для {len(target_indices)} выбранных строк.")
            else:
                target_indices = [
                    i for i, r in enumerate(data_to_process) 
                    if not str(r.get("Text", "")).strip()
                ]
                st.info(f"Режим: Заполнение пустых ячеек ({len(target_indices)} строк).")

            if not target_indices:
                st.warning("Нет строк для обработки. Выберите строки галочками или очистите ячейки 'Text'.")
                st.session_state.generation_active = False
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                updates_count = 0
                
                for step, idx in enumerate(target_indices):
                    if not st.session_state.generation_active:
                        st.warning("Генерация остановлена пользователем.")
                        break
                    
                    row = data_to_process[idx]
                    percent = int((step + 1) / len(target_indices) * 100)
                    status_text.text(f"Обработка {step + 1} из {len(target_indices)} ({percent}%): {row.get('Title', 'No Title')}")
                    
                    page_text = parser.fetch_page_content(row.get("Link")) or "Контент недоступен"
                    res = ai_engine.run_multi_agent_text_generation(
                        title=row.get("Title"),
                        link=row.get("Link"),
                        keywords=row.get("Keywords"),
                        _description=row.get("Description"),
                        page_context=page_text,
                        api_key=GEMINI_API_KEY
                    )
                    sheets.update_row(st.session_state.current_project_id, idx, {"Text": res})
                    row["Text"] = res
                    row["Выбрать"] = False
                    updates_count += 1
                    progress_bar.progress((step + 1) / len(target_indices))
                
                st.session_state.project_data = data_to_process
                st.session_state.generation_active = False
                st.success(f"Готово! Сгенерировано текстов: {updates_count}")
                st.rerun()

    elif action == "Экспорт":
        # Экспорт всегда из мастер-данных или текущего буфера? 
        # Лучше из edited_data, чтобы экспортировать текущие правки.
        data_to_export = edited_data.to_dict('records') if isinstance(edited_data, pd.DataFrame) else edited_data
        
        if data_to_export:
            xls_data = export.export_to_excel(data_to_export)
            st.download_button(
                "Скачать .xlsx",
                xls_data,
                "project.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            xml_data = export.export_to_xml(data_to_export)
            st.download_button("Скачать .xml", xml_data, "project.xml", "text/xml")
        else:
            st.warning("Нет данных для экспорта")

else:
    st.info("Пожалуйста, выберите или создайте проект в боковой панели.")

