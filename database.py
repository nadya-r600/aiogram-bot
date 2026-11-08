import aiosqlite
from datetime import date

DB_NAME = "bot_files.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                db_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS homework (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                task TEXT NOT NULL,
                deadline TEXT NOT NULL,
                done INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS important (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                title TEXT NOT NULL,
                comment TEXT,
                event_date TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schedule_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                subject TEXT NOT NULL,
                action TEXT NOT NULL,
                new_date TEXT,
                comment TEXT
            )
        """)
        await db.commit()

async def save_file(subject, file_id, file_name, file_type):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO files (subject, file_id, file_name, file_type) VALUES (?, ?, ?, ?)",
            (subject, file_id, file_name, file_type),
        )
        await db.execute("UPDATE files SET db_id = ? WHERE id = ?", (cursor.lastrowid, cursor.lastrowid))
        await db.commit()

async def get_files_by_subject(subject):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT id, file_id, file_name, file_type FROM files WHERE subject = ?",
            (subject,),
        )
        return await cur.fetchall()

async def delete_file(db_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM files WHERE id = ?", (db_id,))
        await db.commit()

async def search_files_by_keyword(keyword):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT file_id, file_name FROM files WHERE file_name LIKE ?",
            (f"%{keyword}%",),
        )
        return await cur.fetchall()

async def add_homework(subject, task, deadline):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO homework (subject, task, deadline) VALUES (?, ?, ?)",
            (subject, task, deadline),
        )
        await db.commit()

async def get_homework(subject=None):
    async with aiosqlite.connect(DB_NAME) as db:
        if subject:
            cur = await db.execute(
                "SELECT id, subject, task, deadline, done FROM homework WHERE subject = ? ORDER BY deadline",
                (subject,),
            )
        else:
            cur = await db.execute(
                "SELECT id, subject, task, deadline, done FROM homework ORDER BY deadline"
            )
        return await cur.fetchall()

async def mark_homework_done(hw_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE homework SET done = 1 WHERE id = ?", (hw_id,))
        await db.commit()

async def delete_homework(hw_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM homework WHERE id = ?", (hw_id,))
        await db.commit()

async def delete_passed_homework():
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM homework WHERE deadline < ?", (today,))
        await db.commit()

async def add_important(subject, title, comment, event_date):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO important (subject, title, comment, event_date) VALUES (?, ?, ?, ?)",
            (subject, title, comment, event_date),
        )
        await db.commit()

async def get_important(subject=None):
    async with aiosqlite.connect(DB_NAME) as db:
        if subject:
            cur = await db.execute(
                "SELECT id, subject, title, comment, event_date FROM important WHERE subject = ? ORDER BY event_date",
                (subject,),
            )
        else:
            cur = await db.execute(
                "SELECT id, subject, title, comment, event_date FROM important ORDER BY event_date"
            )
        return await cur.fetchall()

async def delete_important(item_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM important WHERE id = ?", (item_id,))
        await db.commit()

async def add_override(date_str, subject, action, new_date=None, comment=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO schedule_overrides (date, subject, action, new_date, comment) VALUES (?, ?, ?, ?, ?)",
            (date_str, subject, action, new_date, comment),
        )
        await db.commit()

async def get_overrides_for_date(date_str):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT subject, action, new_date, comment FROM schedule_overrides WHERE date = ?",
            (date_str,),
        )
        return await cur.fetchall()

async def clear_old_overrides():
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM schedule_overrides WHERE date < ?", (today,))
        await db.commit()