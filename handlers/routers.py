from datetime import datetime, date, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)

from database import (
    save_file, get_files_by_subject, search_files_by_keyword, delete_file,
    add_homework, get_homework, mark_homework_done, delete_homework,
    add_important, get_important, delete_important,
    add_override, get_overrides_for_date
)
from schedule import SCHEDULE, get_schedule_for_date, DAYS_RU

router = Router()

SUBJECTS_INFO = {
    "Архитектура ЭВМ": {"teacher": "М. Ю. Кудряшов", "control": "Зачёт"},
    "Основы предпринимательской деятельности": {"teacher": "Н. А. Мансурова", "control": "Зачёт"},
    "Разработка цифровых решений на базе технологий 1С": {"teacher": "А. В. Гаврилова", "control": "Зачёт"},
    "Бухгалтерский и управленческий учет": {"teacher": "А. А. Смородова", "control": "Зачёт"},
    "Теория вероятностей и математическая статистика": {"teacher": "И. В. Захарова / О. И. Сидорова", "control": "Экзамен"},
    "Введение в информационные технологии": {"teacher": "В. Н. Новикова", "control": "Экзамен"},
    "Количественные методы в маркетинге": {"teacher": "С. В. Архипов", "control": "Экзамен"},
    "Финансы и кредит": {"teacher": "А. А. Смородова", "control": "Экзамен"},
    "Менеджмент": {"teacher": "Н. А. Мансурова", "control": "Зачёт"},
}

SUBJECTS = list(SUBJECTS_INFO.keys())
user_subject = {}

class HWForm(StatesGroup):
    subject = State()
    task = State()
    deadline = State()

class ImportantForm(StatesGroup):
    subject = State()
    title = State()
    comment = State()
    date = State()

class OverrideForm(StatesGroup):
    date = State()
    subject = State()
    action = State()
    new_date = State()
    comment = State()

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Предметы", callback_data="menu_subjects")],
        [
            InlineKeyboardButton(text="📅 Расписание", callback_data="menu_schedule"),
            InlineKeyboardButton(text="📝 Все ДЗ", callback_data="all_hw"),
        ],
        [
            InlineKeyboardButton(text="⚠️ Важное", callback_data="all_important"),
            InlineKeyboardButton(text="✏️ Изменить расписание", callback_data="edit_sched"),
        ],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")],
    ])

def subjects_keyboard():
    buttons, row = [], []
    for i, subj in enumerate(SUBJECTS):
        row.append(InlineKeyboardButton(text=subj[:30], callback_data=f"subj:{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def subject_menu(index):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Загрузить файл", callback_data=f"upload:{index}")],
        [InlineKeyboardButton(text="📂 Файлы", callback_data=f"show:{index}")],
        [InlineKeyboardButton(text="📝 Добавить ДЗ", callback_data=f"hw_add:{index}")],
        [InlineKeyboardButton(text="📋 ДЗ по предмету", callback_data=f"hw_list:{index}")],
        [InlineKeyboardButton(text="⚠️ Добавить важное", callback_data=f"imp_add:{index}")],
        [InlineKeyboardButton(text="📌 Важное по предмету", callback_data=f"imp_list:{index}")],
        [InlineKeyboardButton(text="⬅️ К предметам", callback_data="menu_subjects")],
    ])

def schedule_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Сегодня", callback_data="sched_today"),
            InlineKeyboardButton(text="Завтра", callback_data="sched_tomorrow")
        ],
        [
            InlineKeyboardButton(text="Пн", callback_data="sched_day:0"),
            InlineKeyboardButton(text="Вт", callback_data="sched_day:1"),
            InlineKeyboardButton(text="Ср", callback_data="sched_day:2"),
            InlineKeyboardButton(text="Чт", callback_data="sched_day:3"),
        ],
        [
            InlineKeyboardButton(text="Пт", callback_data="sched_day:4"),
            InlineKeyboardButton(text="Сб", callback_data="sched_day:5"),
            InlineKeyboardButton(text="Вс", callback_data="sched_day:6"),
        ],
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")],
    ])

def back_to_sched_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К выбору дня", callback_data="menu_schedule")]
    ])

@router.message(Command("start", ignore_case=True))
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Я твой учебный помощник.\n\nВыбери действие:", reply_markup=main_menu_keyboard())

@router.message(Command("help", ignore_case=True))
async def cmd_help(message: Message):
    await message.answer("/start — главное меню\n/schedule — расписание\n/hw — все ДЗ\n/important — всё важное\n/help — справка")

@router.message(Command("hw", ignore_case=True))
async def cmd_hw(message: Message):
    await show_all_homework(message)

@router.message(Command("important", ignore_case=True))
async def cmd_important(message: Message):
    await show_all_important(message)

@router.message(Command("schedule", ignore_case=True))
async def cmd_sched(message: Message):
    await message.answer("📅 На какой день посмотреть расписание?", reply_markup=schedule_menu_keyboard())

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cb.message.edit_text("👋 Главное меню:", reply_markup=main_menu_keyboard())
    except:
        await cb.message.answer("👋 Главное меню:", reply_markup=main_menu_keyboard())
    await cb.answer()

@router.callback_query(F.data == "menu_subjects")
async def cb_menu_subjects(cb: CallbackQuery):
    await cb.message.edit_text("📚 Выбери предмет:", reply_markup=subjects_keyboard())
    await cb.answer()

@router.callback_query(F.data == "close")
async def cb_close(cb: CallbackQuery):
    await cb.message.delete()
    await cb.answer()

@router.callback_query(F.data.startswith("subj:"))
async def cb_subject(cb: CallbackQuery):
    idx = int(cb.data.split(":")[1])
    subj_name = SUBJECTS[idx]
    info = SUBJECTS_INFO[subj_name]
    text = f"📚 <b>{subj_name}</b>\n\n👨‍🏫 <b>Преподаватель:</b> {info['teacher']}\n📋 <b>Форма контроля:</b> {info['control']}\n\nЧто сделать?"
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=subject_menu(idx))
    await cb.answer()

async def show_all_homework(target):
    rows = await get_homework()
    if not rows:
        text = "ДЗ пока нет 🎉"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")]])
    else:
        text = "📝 <b>Все домашние задания:</b>\n\n"
        buttons = []
        for hw_id, subj, task, deadline, done in rows:
            mark = "✅" if done else "🔴"
            text += f"{mark} <b>[{hw_id}] {subj}</b>\n   {task}\n   до {deadline}\n\n"
            if not done:
                buttons.append([InlineKeyboardButton(text=f"✅ Выполнить ДЗ [{hw_id}]", callback_data=f"hw_done:{hw_id}")])
            buttons.append([InlineKeyboardButton(text=f"🗑 Удалить ДЗ [{hw_id}]", callback_data=f"hw_del:{hw_id}")])
        
        buttons.append([InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)

async def show_all_important(target):
    rows = await get_important()
    if not rows:
        text = "Пока ничего важного нет."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")]])
    else:
        text = "⚠️ <b>Важное:</b>\n\n"
        buttons = []
        for item_id, subj, title, comment, d in rows:
            text += f"<b>[{item_id}] {subj}</b> — {title}\n   {comment or ''}\n   {d or ''}\n\n"
            buttons.append([InlineKeyboardButton(text=f"🗑 Удалить запись [{item_id}]", callback_data=f"imp_del:{item_id}")])
        
        buttons.append([InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "all_hw")
async def cb_all_hw(cb: CallbackQuery):
    await show_all_homework(cb)

@router.callback_query(F.data == "all_important")
async def cb_all_imp(cb: CallbackQuery):
    await show_all_important(cb)

@router.callback_query(F.data.startswith("hw_del:"))
async def cb_hw_del(cb: CallbackQuery):
    hw_id = int(cb.data.split(":")[1])
    await delete_homework(hw_id)
    await cb.answer("🗑 ДЗ удалено!")
    await show_all_homework(cb)

@router.callback_query(F.data.startswith("hw_done:"))
async def cb_hw_done(cb: CallbackQuery):
    hw_id = int(cb.data.split(":")[1])
    await mark_homework_done(hw_id)
    await cb.answer("✅ ДЗ выполнено!")
    await show_all_homework(cb)

@router.callback_query(F.data.startswith("imp_del:"))
async def cb_imp_del(cb: CallbackQuery):
    item_id = int(cb.data.split(":")[1])
    await delete_important(item_id)
    await cb.answer("🗑 Запись удалена!")
    await show_all_important(cb)

@router.callback_query(F.data == "menu_schedule")
async def cb_menu_schedule(cb: CallbackQuery):
    await cb.message.edit_text("📅 На какой день посмотреть расписание?", reply_markup=schedule_menu_keyboard())
    await cb.answer()

@router.callback_query(F.data == "sched_today")
async def cb_sched_today(cb: CallbackQuery):
    await send_schedule(cb.message, date.today(), is_edit=True)
    await cb.answer()

@router.callback_query(F.data == "sched_tomorrow")
async def cb_sched_tomorrow(cb: CallbackQuery):
    await send_schedule(cb.message, date.today() + timedelta(days=1), is_edit=True)
    await cb.answer()

@router.callback_query(F.data.startswith("sched_day:"))
async def cb_sched_day(cb: CallbackQuery):
    day_idx = int(cb.data.split(":")[1])
    today = date.today()
    days_ahead = day_idx - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    target_date = today + timedelta(days=days_ahead)
    await send_schedule(cb.message, target_date, is_edit=True)
    await cb.answer()

async def send_schedule(message: Message, target_date: date, is_edit=False):
    weekday = target_date.weekday()
    day_name = DAYS_RU[weekday]
    date_str = target_date.strftime("%d.%m.%Y")
    day_data = SCHEDULE.get(weekday, {})
    
    if "both" in day_data:
        subj_plus = day_data["both"]
        subj_minus = day_data["both"]
    else:
        subj_plus = day_data.get("+", [])
        subj_minus = day_data.get("-", [])
        
    overrides = await get_overrides_for_date(target_date.isoformat())
    
    lines = [f"📅 <b>{day_name}, {date_str}</b>\n"]
    
    lines.append("🟢 <b>Чётная неделя:</b>")
    if not subj_plus:
        lines.append("Занятий нет 🎉")
    else:
        for i, s in enumerate(subj_plus, 1):
            is_cancel = False
            for subj, action, _, comment in overrides:
                if action == "cancel" and subj.lower() in s.lower():
                    lines.append(f"❌ <s>{i}. {s}</s> — {comment or 'Отменено'}")
                    is_cancel = True
                    break
            if not is_cancel:
                lines.append(f"{i}. {s}")
                
    lines.append("\n🔴 <b>Нечётная неделя:</b>")
    if not subj_minus:
        lines.append("Занятий нет 🎉")
    else:
        for i, s in enumerate(subj_minus, 1):
            is_cancel = False
            for subj, action, _, comment in overrides:
                if action == "cancel" and subj.lower() in s.lower():
                    lines.append(f"❌ <s>{i}. {s}</s> — {comment or 'Отменено'}")
                    is_cancel = True
                    break
            if not is_cancel:
                lines.append(f"{i}. {s}")
                
    other = [o for o in overrides if o[1] != "cancel"]
    if other:
        lines.append("\n⚠️ <b>Изменения:</b>")
        for subj, action, new_date, comment in other:
            if action == "move":
                lines.append(f"➡️ {subj} — перенесено на {new_date}. {comment or ''}")
            elif action == "add":
                lines.append(f"➕ {subj} — добавлено. {comment or ''}")
                
    text = "\n".join(lines)
    if is_edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=back_to_sched_keyboard())
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=back_to_sched_keyboard())

@router.callback_query(F.data.startswith("upload:"))
async def cb_upload(cb: CallbackQuery):
    idx = int(cb.data.split(":")[1])
    user_subject[cb.from_user.id] = SUBJECTS[idx]
    await cb.message.answer(f"📎 Отправь файл для «{SUBJECTS[idx]}»")
    await cb.answer()

@router.callback_query(F.data.startswith("show:"))
async def cb_show(cb: CallbackQuery):
    idx = int(cb.data.split(":")[1])
    subj = SUBJECTS[idx]
    files = await get_files_by_subject(subj)
    
    kb_back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"subj:{idx}")]])
    
    if not files:
        await cb.message.edit_text(f"По «{subj}» файлов нет.", reply_markup=kb_back)
    else:
        try:
            await cb.message.edit_text(f"📂 Файлы по «{subj}»:", reply_markup=kb_back)
        except:
            await cb.message.answer(f"📂 Файлы по «{subj}»:", reply_markup=kb_back)
            
        for db_id, file_id, name, ftype in files:
            kb_del = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Удалить файл", callback_data=f"file_del:{db_id}:{idx}")]
            ])
            
            if ftype == "photo":
                await cb.message.answer_photo(file_id, caption=name, reply_markup=kb_del)
            else:
                await cb.message.answer_document(file_id, caption=name, reply_markup=kb_del)
    await cb.answer()

@router.callback_query(F.data.startswith("file_del:"))
async def cb_file_del(cb: CallbackQuery):
    parts = cb.data.split(":")
    db_id = int(parts[1])
    idx = int(parts[2])
    
    await delete_file(db_id)
    await cb.answer("🗑 Файл удален!")
    
    subj = SUBJECTS[idx]
    files = await get_files_by_subject(subj)
    kb_back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ К предмету", callback_data=f"subj:{idx}")]])
    
    await cb.message.delete()
    
    if not files:
        await cb.message.answer(f"По «{subj}» файлов больше нет.", reply_markup=kb_back)
    else:
        await cb.message.answer(f"Файл удален. Осталось файлов: {len(files)}", reply_markup=kb_back)

@router.message(F.document)
async def h_doc(message: Message):
    subj = user_subject.get(message.from_user.id)
    if not subj:
        await message.answer("Сначала выбери предмет в меню.")
        return
    await save_file(subj, message.document.file_id, message.document.file_name or "file", "document")
    await message.answer(f"✅ Файл сохранён для «{subj}».", reply_markup=main_menu_keyboard())

@router.message(F.photo)
async def h_photo(message: Message):
    subj = user_subject.get(message.from_user.id)
    if not subj:
        await message.answer("Сначала выбери предмет в меню.")
        return
    await save_file(subj, message.photo[-1].file_id, "photo.jpg", "photo")
    await message.answer(f"✅ Картинка сохранена для «{subj}».", reply_markup=main_menu_keyboard())

@router.callback_query(F.data.startswith("hw_add:"))
async def cb_hw_add(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split(":")[1])
    await state.update_data(subject=SUBJECTS[idx])
    await state.set_state(HWForm.task)
    await cb.message.answer("📝 Напиши текст ДЗ:")
    await cb.answer()

@router.message(HWForm.task)
async def hw_task(message: Message, state: FSMContext):
    await state.update_data(task=message.text)
    await state.set_state(HWForm.deadline)
    await message.answer("📅 До какого числа сдать? (ГГГГ-ММ-ДД):")

@router.message(HWForm.deadline)
async def hw_deadline(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат. Пример: 2026-11-15")
        return
    data = await state.get_data()
    await add_homework(data["subject"], data["task"], message.text)
    await state.clear()
    
    await message.answer(
        f"✅ ДЗ добавлено по «{data['subject']}» до {message.text}.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Посмотреть все ДЗ", callback_data="all_hw")],
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")]
        ])
    )

@router.callback_query(F.data.startswith("hw_list:"))
async def cb_hw_list(cb: CallbackQuery):
    idx = int(cb.data.split(":")[1])
    subj = SUBJECTS[idx]
    rows = await get_homework(subj)
    
    kb_back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"subj:{idx}")]])
    
    if not rows:
        await cb.message.edit_text(f"По «{subj}» ДЗ нет.", reply_markup=kb_back)
    else:
        text = f"📋 <b>ДЗ по «{subj}»:</b>\n\n"
        buttons = []
        for hw_id, s, task, deadline, done in rows:
            mark = "✅" if done else "🔴"
            text += f"{mark} [{hw_id}] {task}\n   до {deadline}\n\n"
            if not done:
                buttons.append([InlineKeyboardButton(text=f"✅ Выполнить [{hw_id}]", callback_data=f"hw_done:{hw_id}")])
            buttons.append([InlineKeyboardButton(text=f"🗑 Удалить [{hw_id}]", callback_data=f"hw_del:{hw_id}")])
        
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"subj:{idx}")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("imp_add:"))
async def cb_imp_add(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split(":")[1])
    await state.update_data(subject=SUBJECTS[idx])
    await state.set_state(ImportantForm.title)
    await cb.message.answer("⚠️ Что важное? (например: Контрольная работа)")
    await cb.answer()

@router.message(ImportantForm.title)
async def imp_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(ImportantForm.comment)
    await message.answer("💬 Комментарий (что готовить):")

@router.message(ImportantForm.comment)
async def imp_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await state.set_state(ImportantForm.date)
    await message.answer("📅 Дата события (ГГГГ-ММ-ДД):")

@router.message(ImportantForm.date)
async def imp_date(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат. Пример: 2026-11-20")
        return
    data = await state.get_data()
    await add_important(data["subject"], data["title"], data["comment"], message.text)
    await state.clear()
    
    await message.answer(
        f"✅ Важное добавлено по «{data['subject']}».",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚠️ Посмотреть всё важное", callback_data="all_important")],
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")]
        ])
    )

@router.callback_query(F.data.startswith("imp_list:"))
async def cb_imp_list(cb: CallbackQuery):
    idx = int(cb.data.split(":")[1])
    subj = SUBJECTS[idx]
    rows = await get_important(subj)
    
    kb_back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"subj:{idx}")]])
    
    if not rows:
        await cb.message.edit_text(f"По «{subj}» важного нет.", reply_markup=kb_back)
    else:
        text = f"📌 <b>Важное по «{subj}»:</b>\n\n"
        buttons = []
        for item_id, s, title, comment, d in rows:
            text += f"[{item_id}] <b>{title}</b>\n   {comment or ''}\n   {d or ''}\n\n"
            buttons.append([InlineKeyboardButton(text=f"🗑 Удалить запись [{item_id}]", callback_data=f"imp_del:{item_id}")])
        
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"subj:{idx}")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data == "edit_sched")
async def cb_edit_sched(cb: CallbackQuery, state: FSMContext):
    await state.set_state(OverrideForm.date)
    await cb.message.answer("✏️ Введи дату занятия (ГГГГ-ММ-ДД):")
    await cb.answer()

@router.message(OverrideForm.date)
async def ov_date(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат. Пример: 2026-11-15")
        return
    await state.update_data(date=message.text)
    await state.set_state(OverrideForm.subject)
    await message.answer("Какой предмет? (напиши название как в расписании)")

@router.message(OverrideForm.subject)
async def ov_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await state.set_state(OverrideForm.action)
    await message.answer("Что произошло?\nНапиши: <b>отмена</b>, <b>перенос</b> или <b>добавить</b>", parse_mode="HTML")

@router.message(OverrideForm.action)
async def ov_action(message: Message, state: FSMContext):
    action_map = {"отмена": "cancel", "перенос": "move", "добавить": "add"}
    act = action_map.get(message.text.lower().strip())
    if not act:
        await message.answer("Напиши: отмена / перенос / добавить")
        return
    await state.update_data(action=act)
    if act in ["move", "add"]:
        await state.set_state(OverrideForm.new_date)
        await message.answer("На какую дату? ГГГГ-ММ-ДД")
    else:
        await state.set_state(OverrideForm.comment)
        await message.answer("Комментарий (например: НО МЕНЕДЖМЕНТА НЕ БУДЕТ, или напиши «-»):")

@router.message(OverrideForm.new_date)
async def ov_new_date(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат. Пример: 2026-11-15")
        return
    await state.update_data(new_date=message.text)
    await state.set_state(OverrideForm.comment)
    await message.answer("Комментарий (можно «-»):")

@router.message(OverrideForm.comment)
async def ov_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    comment = None if message.text.strip() == "-" else message.text
    await add_override(data["date"], data["subject"], data["action"], data.get("new_date"), comment)
    await state.clear()
    await message.answer("✅ Изменение расписания сохранено.", reply_markup=main_menu_keyboard())

@router.message(F.text)
async def handle_text(message: Message):
    text = message.text.lower()
    triggers = ["пришли", "отправь", "дай", "скинь", "найди", "покажи"]
    if any(t in text for t in triggers):
        keyword = text
        for t in triggers:
            keyword = keyword.replace(t, "")
        keyword = keyword.replace("мне", "").replace("по", "").strip()
        files = await search_files_by_keyword(keyword)
        if not files:
            await message.answer(f"Ничего не нашёл по «{keyword}».")
            return
        for file_id, name in files:
            await message.answer_document(file_id, caption=name)
        return
    await message.answer("Я тебя не понял. Воспользуйся меню /start.", reply_markup=main_menu_keyboard())