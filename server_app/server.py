import os
import sqlite3
import threading
import time
import socket
from flask import Flask, request, jsonify, send_from_directory, abort
import sys
import io
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.parse import unquote

# Проверка и создание баз данных, если их нет
def ensure_databases_exist():
    db_files = ['employees.db', 'management.db', 'chat.db', 'server_logs.db']
    for db_file in db_files:
        if not os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            conn.close()

ensure_databases_exist()

# Конфигурация сервера
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5000
UPLOAD_FOLDER = r'D:\like\server_app\uploads'

# Установите максимальный размер загружаемого файла (10 ГБ)
MAX_CONTENT_LENGTH = 10 * 1024 * 1024 * 1024  # 10 ГБ

# Создание директории для загрузки файлов, если она не существует
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Инициализация Flask приложения
flask_app = Flask(__name__)
flask_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
flask_app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('management.db')
    c = conn.cursor()

    # Проверка существования таблицы users и добавление, если нужно
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY,
                 username TEXT NOT NULL UNIQUE,
                 password TEXT NOT NULL
                 )''')

    # Проверка и добавление недостающих столбцов
    existing_columns = [row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()]

    if 'is_admin' not in existing_columns:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    if 'can_like' not in existing_columns:
        c.execute("ALTER TABLE users ADD COLUMN can_like INTEGER DEFAULT 1")
    if 'can_dislike' not in existing_columns:
        c.execute("ALTER TABLE users ADD COLUMN can_dislike INTEGER DEFAULT 1")
    if 'can_half_like' not in existing_columns:
        c.execute("ALTER TABLE users ADD COLUMN can_half_like INTEGER DEFAULT 1")

    # Добавляем пользователя admin, если он не существует
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, is_admin, can_like, can_dislike, can_half_like) VALUES (?, ?, ?, ?, ?, ?)",
            ('admin', 'admin100', 1, 1, 1, 1))

    conn.commit()
    conn.close()


init_db()



# Маршруты для работы с сотрудниками
@flask_app.route('/employees', methods=['GET'])
def get_employees():
    try:
        conn = sqlite3.connect('employees.db')
        c = conn.cursor()
        c.execute("SELECT * FROM employees")
        employees = c.fetchall()
        conn.close()
        return jsonify(employees)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@flask_app.route('/employees', methods=['POST'])
def add_employee():
    data = request.get_json()
    try:
        conn = sqlite3.connect('employees.db')
        c = conn.cursor()
        c.execute("INSERT INTO employees (first_name, last_name, middle_name, position) VALUES (?, ?, ?, ?)",
                  (data['first_name'], data['last_name'], data['middle_name'], data['position']))
        conn.commit()
        conn.close()
        return jsonify({"message": "Employee added successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Маршруты для голосования
@flask_app.route('/vote', methods=['POST'])
def vote_employee():
    data = request.get_json()
    conn = sqlite3.connect('employees.db')
    c = conn.cursor()
    if data['vote_type'] == 'can_like':
        c.execute("UPDATE employees SET likes = likes + 1 WHERE id=?", (data['employee_id'],))
    elif data['vote_type'] == 'can_dislike':
        c.execute("UPDATE employees SET dislikes = dislikes + 1 WHERE id=?", (data['employee_id'],))
    elif data['vote_type'] == 'can_half_like':
        c.execute("UPDATE employees SET half_likes = half_likes + 1 WHERE id=?", (data['employee_id'],))
    conn.commit()

    # Логирование для проверки, что данные действительно обновляются
    c.execute("SELECT likes, dislikes, half_likes FROM employees WHERE id=?", (data['employee_id'],))
    updated_values = c.fetchone()
    print(f"Updated values for employee {data['employee_id']}: {updated_values}")

    conn.close()
    return jsonify({"message": "Vote recorded successfully!"})


@flask_app.route('/remove_vote', methods=['POST'])
def remove_vote_employee():
    data = request.get_json()
    conn = sqlite3.connect('employees.db')
    c = conn.cursor()
    if data['vote_type'] == 'can_like':
        c.execute("UPDATE employees SET likes = likes - 1 WHERE id=? AND likes > 0", (data['employee_id'],))
    elif data['vote_type'] == 'can_dislike':
        c.execute("UPDATE employees SET dislikes = dislikes - 1 WHERE id=? AND dislikes > 0", (data['employee_id'],))
    elif data['vote_type'] == 'can_half_like':
        c.execute("UPDATE employees SET half_likes = half_likes - 1 WHERE id=? AND half_likes > 0",
                  (data['employee_id'],))
    conn.commit()

    # Логирование для проверки, что данные действительно обновляются
    c.execute("SELECT likes, dislikes, half_likes FROM employees WHERE id=?", (data['employee_id'],))
    updated_values = c.fetchone()
    print(f"Updated values for employee {data['employee_id']}: {updated_values}")

    conn.close()
    return jsonify({"message": "Vote removed successfully!"})


@flask_app.route('/update_permission', methods=['POST'])
def update_permission():
    data = request.get_json()
    username = data.get('username')
    permission = data.get('permission')
    value = data.get('value')

    if not username or not permission:
        return jsonify({"error": "Missing required data"}), 400

    try:
        conn = sqlite3.connect('management.db')
        c = conn.cursor()
        query = f"UPDATE users SET {permission} = ? WHERE username = ?"
        c.execute(query, (value, username))
        conn.commit()
        conn.close()
        return jsonify({"message": "User permissions updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@flask_app.route('/remove_vote', methods=['POST'])
def remove_vote():
    data = request.get_json()
    conn = sqlite3.connect('employees.db')
    c = conn.cursor()
    if data['vote_type'] == 'like':
        c.execute("UPDATE employees SET likes = likes - 1 WHERE id=?", (data['employee_id'],))
    elif data['vote_type'] == 'dislike':
        c.execute("UPDATE employees SET dislikes = dislikes - 1 WHERE id=?", (data['employee_id'],))
    elif data['vote_type'] == 'half_like':  # Добавляем поддержку пол лайков
        c.execute("UPDATE employees SET half_likes = half_likes - 1 WHERE id=?", (data['employee_id'],))
    conn.commit()
    conn.close()
    return jsonify({"message": "Vote removed successfully!"})


# Маршруты для работы с чатом
@flask_app.route('/chat', methods=['GET'])
def get_chat_messages():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("SELECT username, message, file_path FROM chat ORDER BY id ASC")
    rows = c.fetchall()
    messages = [{"username": row[0], "message": row[1], "file_path": row[2]} for row in rows]
    conn.close()
    return jsonify(messages)


@flask_app.route('/users', methods=['GET'])
def get_users():
    conn = sqlite3.connect('management.db')
    c = conn.cursor()
    c.execute("SELECT username, is_admin, can_like, can_dislike, can_half_like FROM users")
    users = [{"username": row[0], "is_admin": row[1], "can_like": row[2], "can_dislike": row[3], "can_half_like": row[4]} for row in c.fetchall()]
    conn.close()
    return jsonify(users)


@flask_app.route('/chat', methods=['POST'])
def add_chat_message():
    username = request.form.get('username')
    message = request.form.get('message', '')
    file = request.files.get('file')

    file_path = None

    if file:
        try:
            filename = file.filename
            file_path = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        except Exception as e:
            return jsonify({"error": f"Ошибка при сохранении файла: {str(e)}"}), 500

    try:
        conn = sqlite3.connect('chat.db')
        c = conn.cursor()
        c.execute("INSERT INTO chat (username, message, file_path) VALUES (?, ?, ?)", (username, message, file_path))
        conn.commit()
        conn.close()
        return jsonify({"message": "Message sent successfully!"})
    except Exception as e:
        return jsonify({"error": f"Ошибка при сохранении сообщения в базу данных: {str(e)}"}), 500


@flask_app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    filename = unquote(filename)  # Декодирование URL
    return send_from_directory(UPLOAD_FOLDER, filename)

@flask_app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_from_directory(UPLOAD_FOLDER, filename)
    else:
        abort(404, description="File not found")


# Маршруты для регистрации и авторизации
@flask_app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if len(password) != 6 or not password.isdigit():
        return jsonify({"error": "Password must be 6 digits long"}), 400

    try:
        conn = sqlite3.connect('management.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return jsonify({"message": "User registered successfully!"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400


@flask_app.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = sqlite3.connect('management.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()

    if user:
        # Возвращаем права пользователя
        user_permissions = {
            "is_admin": bool(user[3]),  # Предполагая, что is_admin - 4-й столбец
            "can_like": bool(user[4]),  # Предполагая, что can_like - 5-й столбец
            "can_dislike": bool(user[5]),  # Предполагая, что can_dislike - 6-й столбец
            "can_half_like": bool(user[6])  # Предполагая, что can_half_like - 7-й столбец
        }
        return jsonify({"message": "Login successful", "permissions": user_permissions})
    else:
        return jsonify({"error": "Invalid username or password"}), 401


# Маршрут для удаления сотрудника
@flask_app.route('/remove_employee', methods=['POST'])
def remove_employee():
    data = request.get_json()
    employee_id = data.get('employee_id')

    if not employee_id:
        return jsonify({"error": "Employee ID is required"}), 400

    try:
        conn = sqlite3.connect('employees.db')
        c = conn.cursor()
        c.execute("DELETE FROM employees WHERE id=?", (employee_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Employee removed successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Запуск Flask-сервера в отдельном потоке
def run_flask():
    flask_app.run(host=SERVER_HOST, port=SERVER_PORT)


# Перенаправление вывода в консоль приложения
class ConsoleText(io.TextIOBase):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, message)
        self.text_widget.configure(state='disabled')
        self.text_widget.see(tk.END)


# GUI приложение для управления сервером
class ServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Server Management")
        self.server_thread = None
        self.server_running = False

        # Верхняя часть интерфейса с индикацией состояния сервера
        self.status_label = tk.Label(root, text="Server Status: OFFLINE", bg="red", fg="white", font=("Arial", 14))
        self.status_label.pack(pady=10, padx=10, fill=tk.X)

        # Кнопки включения и выключения сервера
        self.start_button = tk.Button(root, text="Включить сервер", command=self.start_server)
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(root, text="Выключить сервер", command=self.stop_server)
        self.stop_button.pack(pady=5)

        # Кнопка для отображения данных для подключения
        self.connection_button = tk.Button(root, text="Данные для подключения", command=self.show_connection_info)
        self.connection_button.pack(pady=5)

        # Таблица логов ошибок
        self.error_table = ttk.Treeview(root, columns=("Error Name", "Timestamp"), show="headings")
        self.error_table.heading("Error Name", text="Название ошибки")
        self.error_table.heading("Timestamp", text="Время ошибки")
        self.error_table.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Кнопка квитирования ошибок
        self.ack_button = tk.Button(root, text="⚠️", command=self.acknowledge_errors, fg="white", bg="red",
                                    font=("Arial", 12))
        self.ack_button.pack(pady=5)

        # Добавляем консоль для отображения логов
        console_frame = tk.Frame(root)
        console_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.console_text = tk.Text(console_frame, wrap=tk.WORD, state='disabled', height=10, bg="black", fg="white")
        self.console_text.pack(fill=tk.BOTH, expand=True)

        sys.stdout = ConsoleText(self.console_text)
        sys.stderr = ConsoleText(self.console_text)

        # Поток для мониторинга состояния сервера
        self.monitor_thread = threading.Thread(target=self.monitor_server)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def start_server(self):
        if not self.server_running:
            try:
                self.server_thread = threading.Thread(target=run_flask)
                self.server_thread.daemon = True
                self.server_thread.start()
                self.server_running = True
                self.update_status("ONLINE", "green")
                print("Сервер успешно запущен.")
            except Exception as e:
                self.log_error(str(e))
                print(f"Не удалось запустить сервер: {e}")
                messagebox.showerror("Ошибка", f"Не удалось запустить сервер: {e}")

    def stop_server(self):
        if self.server_running:
            self.server_running = False
            self.update_status("OFFLINE", "red")
            print("Сервер остановлен.")

    def update_status(self, status, color):
        self.status_label.config(text=f"Server Status: {status}", bg=color)

    def monitor_server(self):
        while True:
            if self.server_running and not self.server_thread.is_alive():
                self.server_running = False
                self.update_status("OFFLINE", "red")
                self.log_error("Server unexpectedly stopped.")
                print("Server unexpectedly stopped.")
            time.sleep(2)

    def log_error(self, error_name):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect('management.db')
        c = conn.cursor()
        c.execute("INSERT INTO error_logs (error_name, timestamp) VALUES (?, ?)", (error_name, timestamp))
        conn.commit()
        conn.close()
        self.refresh_error_table()

    def refresh_error_table(self):
        for row in self.error_table.get_children():
            self.error_table.delete(row)
        conn = sqlite3.connect('management.db')
        c = conn.cursor()
        c.execute("SELECT error_name, timestamp FROM error_logs")
        rows = c.fetchall()
        for row in rows:
            self.error_table.insert("", "end", values=row)
        conn.close()

    def acknowledge_errors(self):
        conn = sqlite3.connect('management.db')
        c = conn.cursor()
        c.execute("DELETE FROM error_logs")
        conn.commit()
        conn.close()
        self.refresh_error_table()
        messagebox.showinfo("Уведомление", "Все ошибки квитированы.")

    def show_connection_info(self):
        # Получение всех IP-адресов компьютера
        ip_addresses = socket.gethostbyname_ex(socket.gethostname())[2]
        info = "\n".join([f"IP: {ip}, Порт: {SERVER_PORT}" for ip in ip_addresses])
        messagebox.showinfo("Данные для подключения", info)


if __name__ == "__main__":
    root = tk.Tk()
    app = ServerApp(root)
    root.mainloop()
