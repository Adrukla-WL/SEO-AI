"""
AI Engine Service
Handles interactions with Google Gemini API for text generation.
"""

import re
import random
import google.generativeai as genai

def configure_gemini(api_key):
    """Configures the Gemini API with the provided key."""
    genai.configure(api_key=api_key)

def humanize_text(text):
    """
    Advanced Humanizer Pipeline.
    Strips AI patterns, markdown, and formatting garbage.
    """
    # 1. Жесткая очистка от технического Markdown (кроме жирного шрифта) и HTML
    text = re.sub(r'#+\s*', '', text)   # Заголовки (обычно не нужны в ячейке)
    # text = re.sub(r'\*\*', '', text)    # Жирный шрифт - ТЕПЕРЬ ОСТАВЛЯЕМ
    text = re.sub(r'__', '', text)      # Курсив
    text = re.sub(r'`', '', text)       # Код
    text = re.sub(r'<[^>]*>', '', text) # HTML-теги

    # 2. Удаление типичных вступлений AI
    text = re.sub(r"^(Конечно|Вот|Согласно вашему|Текст:|Статья:).*\n?", "", text, flags=re.IGNORECASE)
    
    # 3. Замена "AI-лексики" на человеческую (русский вариант)
    replacements = {
        "Кроме того,": "А еще,",
        "Более того,": "Также,",
        "В заключение,": "В общем,",
        "Следовательно,": "Так что,",
        "Важно отметить, что": "",
        "Стоит подчеркнуть, что": "",
        "Является идеальным выбором": "Отлично подойдет",
        "Предлагает широкий спектр": "Тут есть всё:",
        "Уникальная возможность": "Шанс",
        "Погрузитесь в мир": "Попробуйте",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # 4. Финальная чистка лишних пробелов, но сохранение ДВОЙНЫХ переносов для абзацев
    text = re.sub(r'[ \t]+', ' ', text) # Схлопываем лишние пробелы в строке
    text = re.sub(r'\n{3,}', '\n\n', text) # Максимум 2 переноса строки
    
    return text.strip()

def _get_model():
    """Returns a working GenerativeModel instance with fallback logic based on diagnostics."""
    models_to_try = [
        'gemini-flash-latest', 
        'gemini-pro-latest', 
        'gemini-1.5-flash', 
        'gemini-pro'
    ]
    last_err = None
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            # Simple test call is expensive, so we just return the model and handle errors later
            return model
        except Exception as e:
            last_err = e
            continue
    raise last_err or Exception("No working Gemini model found")

def generate_new_description(title, keywords, old_description, _content_context=""):
    """
    Module 2: Generate New Description without AI pattern, specific length constraints.
    """
    try:
        model = _get_model()
        prompt = f"""
    Act as an SEO expert. Write a meta description (Russian language).
    Target:
    - [Keyword phrase near start] + [Specific benefit/diff] + [Call to action]
    Constraints:
    - Length: 140-155 characters (strict).
    - Use keywords: {keywords}
    - Base on context from: {title} - {old_description}
    - Tone: Natural, no spam.

    Output ONLY the description. No quotes.
    """
        response = model.generate_content(prompt)
        text = response.text.strip()
        if len(text) > 160:
            text = text[:157] + "..."
        return text
    except Exception as e: # pylint: disable=broad-exception-caught
        return f"Error: {str(e)}"

# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def run_multi_agent_text_generation(title, link, keywords, _description, page_context, api_key):
    """
    Module 3: Multi-Agent System (Strict Implementation).
    """
    configure_gemini(api_key)
    try:
        model = _get_model()
        
        # --- 1. Агент-копирайтер (генерация черновика) ---
        prompt_a = f"""
        ROLE: Архетип: "Свой парень". Популярный автор travel-текстов, эксперт по круизам.
        TASK: Напиши текст для страницы сайта: {title} ({link}).
        CONTEXT:
        - Ключевые слова: {keywords}
        - Description: {_description}
        - Смысловой контекст страницы: {page_context[:2000]}
        
        STYLE & MISSION:
        - Пиши как человек, только что сошедший с борта. Вдохновленно, но для сайта (не блог).
        - Оригинально, нешаблонно. Чётко и ясно.
        - ЦКП: после текста хочется "паковать чемоданы".
        
        CONSTRAINTS:
        - Язык: РУССКИЙ.
        - Размер: СТРОГО 1400–1600 символов.
        - СТРУКТУРА: Обязательно разбей текст на 3-4 логических абзаца.
        - ФОРМАТИРОВАНИЕ: Выдели основные ключевые слова (2-3 раза за текст) жирным шрифтом, используя двойные звездочки: **слово**.
        - ЗАПРЕЩЕНО: Заголовки (#), HTML, списки.
        - Никаких "Sure!", "Here is the text" и прочих AI-вступлений.
        - Избегай AI-клише: "Кроме того", "Важно отметить", "В заключение".
        
        Выдай только текст.
        """
        draft_response = model.generate_content(prompt_a)
        current_text = draft_response.text.strip()
        
        # --- Цикл доработки (Агент-Критик + Агент-Редактор) ---
        max_iterations = 3
        for i in range(max_iterations):
            # 2. Агент-критик (оценка)
            prompt_b = f"""
            ROLE: Строгий Критик/Редактор.
            TASK: Оцени текст по 10-балльной шкале.
            
            TEXT:
            {current_text}
            
            METRICS (1-10):
            1) Google SEO-friendly (учет ключевых слов: {keywords})
            2) Оригинальность (индивидуальность стиля)
            3) Качество написания (ритм, отсутствие "воды")
            4) Humanize (отсутствие признаков AI, естественность)
            
            OUTPUT FORMAT:
            SCORES: [S1, S2, S3, S4]
            FEEDBACK: [Список конкретных замечаний для исправления]
            """
            critic_response = model.generate_content(prompt_b)
            feedback = critic_response.text
            
            # Парсим оценки (упрощенно)
            scores = re.findall(r'\b([0-9]|10)\b', feedback)
            is_perfect = all(int(s) >= 9 for s in scores[:4]) if len(scores) >= 4 else False
            
            if is_perfect:
                break
                
            # 3. Агент-редактор (исправление)
            prompt_c = f"""
            ROLE: Экспертный Редактор.
            TASK: Исправь текст на основе замечаний Критика, чтобы по ВСЕМ пунктам стало 10/10.
            
            ORIGINAL TEXT:
            {current_text}
            
            CRITIC FEEDBACK:
            {feedback}
            
            STRICT RULES:
            - Сохраняй разбивку на абзацы и жирный шрифт (**).
            - НИКАКИХ заголовков (#) и HTML.
            - Убери AI-слова: "Кроме того", "Является", "Важно", "Подчеркивает".
            - Сохрани объем 1400-1600 символов.
            - Язык: РУССКИЙ.
            
            Выдай только финальный отшлифованный текст.
            """
            editor_response = model.generate_content(prompt_c)
            current_text = editor_response.text.strip()

        # --- Финальная очистка (Humanizer Pipeline) ---
        # 1. Regex очистка от технического мусора (оставляем только нужное)
        current_text = re.sub(r'<[^>]*>', '', current_text) # HTML
        current_text = re.sub(r'#+\s*', '', current_text)   # Headers
        
        # 2. Humanizer post-process
        current_text = humanize_text(current_text)
        
        return current_text

    except Exception as e:
        return f"Error in Multi-Agent Gen: {str(e)}"
