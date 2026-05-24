import sqlite3
import hashlib

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text


def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Добавили поле department в таблицу пользователей
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    department TEXT
                   )
                   ''')

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS test_results
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT, 
                    score INTEGER,
                    total_questions INTEGER,
                    percentage REAL,
                    passing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def save_test_result(username, score, total_questions):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # ПРИНУДИТЕЛЬНАЯ ПОДСТРАХОВКА: создаем таблицу, если её нет
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS test_results
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    score INTEGER,
                    total_questions INTEGER,
                    percentage REAL,
                    passing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )
                   ''')

    # Расчет процента
    percentage = round((score / total_questions) * 100, 1)

    # Теперь запись сработает на 100%
    cursor.execute('''
                   INSERT INTO test_results (username, score, total_questions, percentage)
                   VALUES (?, ?, ?, ?)
                   ''', (username, score, total_questions, percentage))

    conn.commit()
    conn.close()


def get_user_leaderboard():
    import sqlite3
    import pandas as pd

    conn = sqlite3.connect('users.db')

    # Пишем SQL-запрос: сортируем по проценту (от большего к меньшему)
    # Используем MAX(percentage), чтобы если пользователь сдавал несколько раз (или для подстраховки), брался лучший результат
    query = """
            SELECT username AS "Пользователь", MAX(percentage) AS "Успешность (%)"
            FROM test_results
            GROUP BY username
            ORDER BY "Успешность (%)" DESC LIMIT 5 \
            """

    # Сразу чиатем данные в формат Pandas DataFrame для Streamlit
    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        # Если тесты еще никто не сдавал и таблицы нет, вернем пустой или тестовый шаблон
        df = pd.DataFrame(columns=["Пользователь", "Успешность (%)"])

    conn.close()
    return df
def add_user(username, password, department):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (username, password, department) 
            VALUES (?, ?, ?)
        ''', (username, password, department))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Пользователь с таким логином уже есть
    finally:
        conn.close()

def login_user(username, password):
    c = sqlite3.connect('users.db')
    cursor = c.cursor()

    # Ищем пользователя по логину И паролю
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()

    c.close()

    # Если нашли — вернет True, если нет — False
    return user is not None


def get_company_awareness():
    """Считает общий процент осведомленности по всему РДЦ"""
    import sqlite3
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Берем среднее значение от лучших результатов всех пользователей
    query = """
            SELECT AVG(max_percent) \
            FROM (SELECT MAX(percentage) as max_percent \
                  FROM test_results \
                  GROUP BY username) \
            """
    cursor.execute(query)
    result = cursor.fetchone()[0]
    conn.close()

    # Если тесты еще никто не сдавал, вернем 0
    return round(result, 1) if result is not None else 0.0


def get_department_analytics():
    """Собирает средний процент прохождения теста по каждому отделению РДЦ"""
    import sqlite3
    import pandas as pd

    conn = sqlite3.connect('users.db')

    # Связываем таблицы результатов и пользователей через username, чтобы узнать отдел
    query = """
            SELECT u.department                AS "Отделение РДЦ",
                   ROUND(AVG(t.percentage), 1) AS "Уровень защиты (%)"
            FROM test_results t
                     JOIN users u ON t.username = u.username
            GROUP BY u.department
            ORDER BY "Уровень защиты (%)" DESC \
            """

    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        df = pd.DataFrame(columns=["Отделение РДЦ", "Уровень защиты (%)"])

    conn.close()

    # Если данных в БД пока нет, вернем пустой DataFrame
    return df

def init_achievements_db():
    """Создает таблицу ачивок, если её еще нет"""
    import sqlite3
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            achieve_key TEXT,       -- Уникальный идентификатор ачивки (например, 'first_step')
            unlock_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, achieve_key) -- Защита от дублирования одной и той же ачивки
        )
    ''')
    conn.commit()
    conn.close()

def unlock_achievement(username, achieve_key):
    """Безопасно открывает ачивку для пользователя"""
    import sqlite3
    init_achievements_db() # Подстраховка
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO user_achievements (username, achieve_key)
            VALUES (?, ?)
        ''', (username, achieve_key))
        conn.commit()
        # Если строка добавилась, можно вернуть True (ачивка новая)
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def get_user_achievements(username):
    """Возвращает список ключей всех открытых ачивок пользователя"""
    import sqlite3
    init_achievements_db()
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT achieve_key FROM user_achievements WHERE username = ?', (username,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]