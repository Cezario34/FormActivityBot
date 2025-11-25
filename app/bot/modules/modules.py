import json
from pathlib import Path
import re
from datetime import datetime
import io, csv
import pandas as pd

def load_form_json():
    base_path = Path(__file__).resolve().parents[2]
    form_path = base_path / 'quest.json'
    print(form_path)
    with form_path.open(encoding="utf-8") as f:
        return json.load(f)

def get_question(form: dict, order: int) -> dict | None:
    """
    form — dict из JSON.
    order — номер текущего вопроса.
    Возвращает dict вопроса или None.
    """
    for q in form["questions"]:
        if q["order"] == order:
            return q
    return None

def extract_answer(message, q: dict):
    text = message.text.strip()

    rules = q.get("validation") or {}
    q_type = q["q_type"]

    # 1) Фото
    if q_type == "photo":
        if not message.photo:
            return None, "Нужно отправить фото."
        # берём самое большое фото
        return message.photo[-1].file_id, None

    if q_type == "choice":
        opts = q.get("options") or []
        if opts and text not in opts:
            return None, "Выберите вариант кнопкой."
        return text, None


    # 2) Выбор / текст (reply-кнопки тоже приходят как text)
    if q_type == "text":
        if not message.text:
            return None, "Введите текст"
        return message.text.strip(), None




    # 3) Число
    if q_type == "number":
        if not text.isdigit():
            return None, "Введите число."
        val = int(text)
        mn, mx = rules.get("min"), rules.get("max")
        if mn is not None and val < mn:
            return None, f"Минимум {mn}."
        if mx is not None and val > mx:
            return None, f"Максимум {mx}."
        return val, None

        return val, None

    # 4) Дата (дд.мм.гггг)
    if q_type == "date":
        if not message.text:
            return None, "Введите дату в формате дд.мм.гггг."
        text = message.text.strip()
        try:
            dt = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            return None, "Неверный формат даты. Пример: 25.12.1990"
        return dt.isoformat(), None  # чтобы хранить единообразно

    # 5) Телефон
    if q_type == "phone":
        if not message.text:
            return None, "Введите номер телефона."
        phone = message.text.strip().replace(" ", "").replace("-", "")
        v = q.get("validation", {})
        pattern = v.get("regex")
        if pattern and not re.match(pattern, phone):
            return None, "Номер в формате +7XXXXXXXXXX"
        return phone, None

    # Если тип неизвестен — просто текстом
    if message.text:
        return message.text.strip(), "Неизвестный тип вопроса."

    return None, "Неизвестный тип вопроса."

def get_next_question(form: dict, cur_order: int) -> dict | None:

    next_orders = [q["order"] for q in form["questions"] if q["order"] > cur_order]
    if not next_orders:
        return None

    # Следующий = минимальный order из тех, что больше текущего
    next_order = min(next_orders)

    # Возвращаем сам вопрос
    for q in form["questions"]:
        if q["order"] == next_order:
            return q

    return None

def rows_to_csv_bytes(rows) -> bytes:
    if not rows:
        # пустой файл, но с заголовками (можно и без)
        return b""
    df = pd.DataFrame(rows)
    wide = (
        df.pivot_table(
            index=["tg_id", "answered_at"],          # строки = одно заполнение
            columns="question_text",               # колонки = тексты вопросов
            values="answer_text",
            aggfunc="first"                        # если вдруг дубли — берём первый
        )
        .reset_index()
    )

    buf = io.StringIO()
    wide.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
    return buf.getvalue().encode("utf-8-sig")