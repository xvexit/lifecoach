from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Разбор ситуации")
    kb.button(text="Мои проблемы")
    kb.button(text="Работа над проблемой")
    kb.button(text="Чек-ин")
    kb.button(text="Просто поговорить")
    kb.button(text="Мой прогресс")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def yes_no_unsure() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Да")
    kb.button(text="Нет")
    kb.button(text="Не уверен")
    return kb.as_markup(resize_keyboard=True)


def yes_no() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Да")
    kb.button(text="Нет")
    return kb.as_markup(resize_keyboard=True)


def scale_1_5() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text=str(i))
    kb.adjust(5)
    return kb.as_markup(resize_keyboard=True)


def scale_1_10() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for i in range(1, 11):
        kb.button(text=str(i))
    kb.adjust(5)
    return kb.as_markup(resize_keyboard=True)


def multi_choice_emotions() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for e in ["тревога", "злость", "апатия", "вина", "стыд", "грусть", "раздражение"]:
        kb.button(text=e)
    kb.button(text="✅ Готово")
    kb.adjust(3)
    return kb.as_markup(resize_keyboard=True)


def multi_choice_triggers() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for t in ["конфликты", "одиночество", "критика", "неопределённость", "давление", "сравнение с другими"]:
        kb.button(text=t)
    kb.button(text="✅ Готово")
    kb.adjust(3)
    return kb.as_markup(resize_keyboard=True)


def multi_choice_stress() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for s in ["замыкаюсь", "срываюсь", "избегаю", "переедаю", "прокрастинирую", "ищу поддержку"]:
        kb.button(text=s)
    kb.button(text="✅ Готово")
    kb.adjust(3)
    return kb.as_markup(resize_keyboard=True)


def skip_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Пропустить")
    return kb.as_markup(resize_keyboard=True)


def problems_inline(problems: list, prefix: str = "problem") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in problems:
        label = f"{p.name} ({p.probability}%) [severity: {p.severity}]"
        kb.button(text=label, callback_data=f"{prefix}:{p.id}")
    kb.adjust(1)
    return kb.as_markup()


def problem_detail_inline(problem_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Работать над этой проблемой", callback_data=f"work:{problem_id}")
    return kb.as_markup()


def done_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="✅ Готово")
    return kb.as_markup(resize_keyboard=True)


def confirm_plan_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Согласен")
    kb.button(text="Скорректировать")
    kb.button(text="Отменить")
    return kb.as_markup(resize_keyboard=True)


def make_conclusion_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Сделать вывод")
    return kb.as_markup(resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Отмена")
    return kb.as_markup(resize_keyboard=True)
