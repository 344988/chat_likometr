import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, ttk, Checkbutton, BooleanVar
import requests
import sqlite3
import threading
import time
import os


SERVER_URL = 'http://10.61.100.91:5000'
current_user = None
user_permissions = {}
table_window = None  # Переменная для хранения ссылки на окно таблицы
admin_window = None  # Окно администратора

# Глобальная переменная для хранения количества сообщений после первой загрузки
initial_message_count = 0

#import pygame

#pygame.mixer.init()

#def play_notification_sound():
    #try:
        #pygame.mixer.music.load('/notification_sound.mp3')
        #pygame.mixer.music.play()
    #except Exception as e:
        #print(f"Ошибка при воспроизведении звука: {e}")


def load_chat(play_sound=False):
    global initial_message_count
    new_messages = load_chat_from_server()

    #if play_sound and isinstance(new_messages, list):
        #print(f"Количество новых сообщений: {len(new_messages)}, Старое количество: {initial_message_count}")
        #if len(new_messages) > initial_message_count:
            #play_notification_sound()  # Воспроизведение звука при появлении нового сообщения

    chat_text.delete(1.0, tk.END)

    if isinstance(new_messages, list):
        for msg in new_messages:
            if isinstance(msg, dict) and 'username' in msg and 'message' in msg:
                chat_text.insert(tk.END, f"{msg['username']}: {msg['message']}\n")
                if msg.get('file_path'):
                    file_name = os.path.basename(msg['file_path'])
                    download_button = tk.Button(chat_text, text="Скачать", fg="blue",
                                                command=lambda path=file_name: download_file(path))
                    chat_text.window_create(tk.END, window=download_button)
                    chat_text.insert(tk.END, f" {file_name}\n")
            else:
                print("Неверный формат сообщения:", msg)

        # Обновляем количество сообщений после загрузки
        initial_message_count = len(new_messages)
    else:
        print("Ошибка: Ожидался список сообщений, но получено что-то другое:", new_messages)

    # Прокручиваем к концу текста
    chat_text.see(tk.END)


# Функции для работы с сервером
def load_chat_from_server():
    try:
        response = requests.get(f'{SERVER_URL}/chat')
        if response.status_code == 200:
            return response.json()
        else:
            messagebox.showerror("Error", "Unexpected server response")
            return []
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Could not reach the server: {e}")
        return []

def get_employees():
    try:
        response = requests.get(f'{SERVER_URL}/employees')
        if response.status_code == 200:
            return response.json()
        else:
            messagebox.showerror("Error", "Unexpected server response")
            return []
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Could not reach the server: {e}")
        return []





def remove_vote_employee(employee_id, vote_type):
    if vote_type not in user_permissions or not user_permissions[vote_type]:
        messagebox.showerror("Ошибка", "У вас нет прав на выполнение этого действия.")
        return
    data = {
        "employee_id": employee_id,
        "vote_type": vote_type
    }
    try:
        response = requests.post(f'{SERVER_URL}/remove_vote', json=data)
        if response.status_code == 200:
            messagebox.showinfo("Info", response.json()["message"])
        else:
            messagebox.showerror("Error", "Unexpected server response")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Could not reach the server: {e}")

def add_new_employee():
    first_name = simpledialog.askstring("Input", "Имя:")
    last_name = simpledialog.askstring("Input", "Фамилия:")
    middle_name = simpledialog.askstring("Input", "Отчество:")
    position = simpledialog.askstring("Input", "Должность:")

    if first_name and last_name and position:
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "position": position
        }
        try:
            response = requests.post(f'{SERVER_URL}/employees', json=data)
            if response.status_code == 200:
                messagebox.showinfo("Info", response.json()["message"])
            else:
                messagebox.showerror("Error", "Unexpected server response")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Could not reach the server: {e}")
    else:
        messagebox.showerror("Error", "Все поля обязательны!")

def register_user_dialog():
    username = simpledialog.askstring("Регистрация", "Введите имя пользователя:")
    password = simpledialog.askstring("Регистрация", "Введите пароль (6 цифр):", show="*")

    if username and password:
        data = {
            "username": username,
            "password": password
        }
        try:
            response = requests.post(f'{SERVER_URL}/register', json=data)
            if response.status_code == 200:
                messagebox.showinfo("Успех", "Пользователь успешно зарегистрирован.")
            elif response.status_code == 400:
                messagebox.showerror("Ошибка", response.json().get("error", "Unexpected error"))
            else:
                messagebox.showerror("Ошибка", "Unexpected server response")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Could not reach the server: {e}")

def login_user_dialog():
    def on_login():
        username = entry_username.get()
        password = entry_password.get()
        if username and password:
            data = {
                "username": username,
                "password": password
            }
            try:
                response = requests.post(f'{SERVER_URL}/login', json=data)
                if response.status_code == 200:
                    global current_user
                    global user_permissions
                    current_user = username
                    user_permissions = response.json().get("permissions", {})
                    messagebox.showinfo("Успех", f"Добро пожаловать, {username}!")
                    update_ui_for_login()
                    login_window.destroy()  # Закрыть окно после успешного входа
                elif response.status_code == 401:
                    messagebox.showerror("Ошибка", "Неправильное имя пользователя или пароль.")
                else:
                    messagebox.showerror("Ошибка", "Unexpected server response")
            except requests.exceptions.RequestException as e:
                messagebox.showerror("Ошибка", f"Could not reach the server: {e}")

    login_window = tk.Toplevel(root)
    login_window.title("Вход")

    tk.Label(login_window, text="Имя пользователя:").pack(pady=5)
    entry_username = tk.Entry(login_window)
    entry_username.pack(pady=5)

    tk.Label(login_window, text="Пароль:").pack(pady=5)
    entry_password = tk.Entry(login_window, show="*")
    entry_password.pack(pady=5)

    btn_login = tk.Button(login_window, text="Войти", command=on_login)
    btn_login.pack(pady=10)

    login_window.transient(root)  # Окно поверх главного
    login_window.grab_set()  # Захват фокуса на этом окне
    root.wait_window(login_window)  # Ожидание закрытия окна


def logout_user_dialog():
    global current_user
    current_user = None
    update_ui_for_logout()

def update_ui_for_login():
    btn_register.pack_forget()
    btn_login.pack_forget()
    btn_logout.pack(side=tk.LEFT)
    lbl_username.config(text=f"{current_user}", fg="green")
    lbl_username.pack(side=tk.LEFT)

    if user_permissions.get('is_admin', False):
        global btn_admin, btn_user_list
        btn_admin = tk.Button(top_frame, text="Удалить участника", command=delete_user_dialog)
        btn_admin.pack(side=tk.LEFT)

        btn_user_list = tk.Button(top_frame, text="Пользователи", fg="blue", command=show_user_list)
        btn_user_list.pack(side=tk.LEFT)


def update_ui_for_logout():
    btn_logout.pack_forget()
    lbl_username.pack_forget()
    btn_register.pack(side=tk.LEFT)
    btn_login.pack(side=tk.LEFT)

    # Удаляем администраторские кнопки, если они были созданы
    if btn_admin:
        btn_admin.pack_forget()
    if btn_user_list:
        btn_user_list.pack_forget()


def delete_user_dialog():
    employee_id = simpledialog.askinteger("Удалить участника", "Введите ID участника:")
    if employee_id:
        try:
            response = requests.post(f'{SERVER_URL}/remove_employee', json={"employee_id": employee_id})
            if response.status_code == 200:
                messagebox.showinfo("Успех", "Участник успешно удален.")
                load_chat()  # Обновляем таблицу
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить участника.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")

def show_user_list():
    global admin_window

    if admin_window and admin_window.winfo_exists():
        admin_window.lift()
        admin_window.focus_force()
        return

    admin_window = tk.Toplevel(root)
    admin_window.title("Список пользователей")
    admin_window.geometry("500x400")

    try:
        response = requests.get(f'{SERVER_URL}/users')
        if response.status_code == 200:
            users = response.json()
        else:
            messagebox.showerror("Ошибка", "Не удалось получить список пользователей.")
            return
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")
        return

    for row, user in enumerate(users, start=1):
        ttk.Label(admin_window, text=user['username']).grid(row=row, column=0, padx=5, pady=5)

        is_admin_var = BooleanVar(value=user['is_admin'])
        can_like_var = BooleanVar(value=user['can_like'])
        can_dislike_var = BooleanVar(value=user['can_dislike'])
        can_half_like_var = BooleanVar(value=user['can_half_like'])

        Checkbutton(admin_window, text="Админ", variable=is_admin_var, command=lambda u=user['username'], v=is_admin_var: update_permission(u, 'is_admin', v)).grid(row=row, column=1)
        Checkbutton(admin_window, text="Лайк", variable=can_like_var, command=lambda u=user['username'], v=can_like_var: update_permission(u, 'can_like', v)).grid(row=row, column=2)
        Checkbutton(admin_window, text="Дизлайк", variable=can_dislike_var, command=lambda u=user['username'], v=can_dislike_var: update_permission(u, 'can_dislike', v)).grid(row=row, column=3)
        Checkbutton(admin_window, text="Полу-лайк", variable=can_half_like_var, command=lambda u=user['username'], v=can_half_like_var: update_permission(u, 'can_half_like', v)).grid(row=row, column=4)

def update_permission(username, permission, var):
    try:
        response = requests.post(f'{SERVER_URL}/update_permission', json={"username": username, "permission": permission, "value": var.get()})
        if response.status_code != 200:
            messagebox.showerror("Ошибка", "Не удалось обновить права пользователя.")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")

def auto_refresh_chat():
    load_chat()
    root.after(5000, auto_refresh_chat)  # Обновление чата каждые 5 секунд

def check_server_status():
    time.sleep(2)  # Задержка перед первым запросом для гарантии запуска сервера
    try:
        response = requests.get(f'{SERVER_URL}/employees', timeout=2)
        if response.status_code == 200:
            server_status_label.config(text="Server Status: ONLINE", bg="green")
        else:
            server_status_label.config(text="Server Status: OFFLINE", bg="red")
    except requests.exceptions.RequestException:
        server_status_label.config(text="Server Status: OFFLINE", bg="red")
    finally:
        root.after(5000, check_server_status)  # Повторяем проверку через 5 секунд


# Прогресс-бар для загрузки/скачивания файлов
def show_progress_window(title):
    progress_window = tk.Toplevel(root)
    progress_window.title(title)
    progress_window.geometry("300x100")
    progress_label = tk.Label(progress_window, text="Пожалуйста, подождите...")
    progress_label.pack(pady=10)
    progress_bar = ttk.Progressbar(progress_window, orient="horizontal", mode="determinate", length=250)
    progress_bar.pack(pady=10)
    progress_bar.start()
    return progress_window, progress_bar

def attach_file():
    if current_user is None:
        messagebox.showerror("Ошибка", "Только авторизованные пользователи могут отправлять файлы.")
        return

    file_path = filedialog.askopenfilename()
    if file_path:
        try:
            progress_window, progress_bar = show_progress_window("Загрузка файла")
            threading.Thread(target=upload_file, args=(file_path, progress_window, progress_bar)).start()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при отправке файла: {e}")

def upload_file(file_path, progress_window, progress_bar):
    try:
        with open(file_path, 'rb') as f:
            file_name = os.path.basename(file_path)
            files = {'file': (file_name, f)}
            data = {'username': current_user}
            response = requests.post(f'{SERVER_URL}/chat', files=files, data=data, stream=True)

            total_length = response.headers.get('content-length')

            if total_length is None:
                progress_window.destroy()
                messagebox.showerror("Ошибка", "Не удалось отправить файл.")
            else:
                total_length = int(total_length)
                bytes_transferred = 0
                for data in response.iter_content(chunk_size=4096):
                    bytes_transferred += len(data)
                    progress = int(100 * bytes_transferred / total_length)
                    progress_bar['value'] = progress
                progress_window.destroy()
                load_chat()
                messagebox.showinfo("Успех", f"Файл {file_name} успешно загружен.")
    except requests.exceptions.RequestException as e:
        progress_window.destroy()
        messagebox.showerror("Ошибка при отправке файла", f"{e}")

def download_file(file_path):
    try:
        progress_window, progress_bar = show_progress_window("Скачивание файла")
        threading.Thread(target=download_file_thread, args=(file_path, progress_window, progress_bar)).start()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка при скачивании файла: {e}")

def download_file_thread(file_path, progress_window, progress_bar):
    try:
        response = requests.get(f'{SERVER_URL}/download/{file_path}', stream=True)
        response.raise_for_status()

        total_length = response.headers.get('content-length')

        save_path = filedialog.asksaveasfilename(initialfile=file_path)
        if save_path and total_length:
            total_length = int(total_length)
            bytes_transferred = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=4096):
                    f.write(chunk)
                    bytes_transferred += len(chunk)
                    progress = int(100 * bytes_transferred / total_length)
                    progress_bar['value'] = progress
            progress_window.destroy()
            messagebox.showinfo("Успех", f"Файл {file_path} успешно скачан.")
        else:
            progress_window.destroy()
            messagebox.showerror("Ошибка", "Не удалось сохранить файл.")
    except requests.exceptions.RequestException as e:
        progress_window.destroy()
        messagebox.showerror("Ошибка при скачивании файла", f"{e}")

def send_message():
    if current_user is None:
        messagebox.showerror("Ошибка", "Только авторизованные пользователи могут отправлять сообщения.")
        return

    message = chat_entry.get()
    if message:
        data = {
            "message": message,
            "username": current_user
        }
        try:
            response = requests.post(f'{SERVER_URL}/chat', data=data)
            if response.status_code == 200:
                chat_text.insert(tk.END, f"{current_user}: {message}\n")
                chat_entry.delete(0, tk.END)
                load_chat()
            else:
                messagebox.showerror("Ошибка", "Не удалось отправить сообщение.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")




##тут функция

def show_table():
    global table_window

    if table_window and table_window.winfo_exists():
        table_window.lift()
        table_window.focus_force()
        return

    table_window = tk.Toplevel(root)
    table_window.title("Список сотрудников")
    table_window.geometry("1200x300")

    headers = ["ID", "Имя", "Фамилия", "Отчество", "Должность", "__Лайки__", "+", "__Дизлайки__", "+", "__Пол-Лайки__", "+", "DEL L", "Del D", "DEL P"]

    for i, header in enumerate(headers):
        ttk.Label(table_window, text=header, font=('Arial', 10, 'bold'), borderwidth=2, relief="groove").grid(row=0, column=i, sticky="nsew")

    employees = get_employees()

    for row, emp in enumerate(employees, start=1):
        for col, value in enumerate(emp[:5]):
            ttk.Label(table_window, text=value, font=('Arial', 10), borderwidth=2, relief="groove", anchor="center").grid(row=row, column=col, sticky="nsew")

        likes_count = ttk.Label(table_window, text=f"{emp[5] if len(emp) > 5 else 0}", font=('Arial', 10), borderwidth=2, relief="groove", anchor="center")
        likes_count.grid(row=row, column=5, sticky="nsew")

        dislikes_count = ttk.Label(table_window, text=f"{emp[6] if len(emp) > 6 else 0}", font=('Arial', 10), borderwidth=2, relief="groove", anchor="center")
        dislikes_count.grid(row=row, column=7, sticky="nsew")

        half_likes_count = ttk.Label(table_window, text=f"{emp[7] if len(emp) > 7 else 0}", font=('Arial', 10), borderwidth=2, relief="groove", anchor="center")
        half_likes_count.grid(row=row, column=9, sticky="nsew")

        # Кнопки для добавления лайков
        btn_like = tk.Button(table_window, text="👍", bg="green",
                             command=lambda emp_id=emp[0], likes_lbl=likes_count, dislikes_lbl=dislikes_count, half_likes_lbl=half_likes_count:
                             vote_employee(emp_id, 'can_like', likes_lbl, dislikes_lbl, half_likes_lbl))
        btn_like.grid(row=row, column=6, sticky="nsew")

        # Кнопки для добавления дизлайков
        btn_dislike = tk.Button(table_window, text="👎", bg="red",
                                command=lambda emp_id=emp[0], likes_lbl=likes_count, dislikes_lbl=dislikes_count, half_likes_lbl=half_likes_count:
                                vote_employee(emp_id, 'can_dislike', likes_lbl, dislikes_lbl, half_likes_lbl))
        btn_dislike.grid(row=row, column=8, sticky="nsew")

        # Кнопки для добавления пол-лайков
        btn_half_like = tk.Button(table_window, text="👍", bg="orange",
                                  command=lambda emp_id=emp[0], likes_lbl=likes_count, dislikes_lbl=dislikes_count, half_likes_lbl=half_likes_count:
                                  vote_employee(emp_id, 'can_half_like', likes_lbl, dislikes_lbl, half_likes_lbl))
        btn_half_like.grid(row=row, column=10, sticky="nsew")

        # Кнопки для удаления лайков
        btn_remove_like = tk.Button(table_window, text="del", bg="red",
                                    command=lambda emp_id=emp[0], likes_lbl=likes_count, dislikes_lbl=dislikes_count, half_likes_lbl=half_likes_count:
                                    remove_vote_employee(emp_id, 'can_like', likes_lbl, dislikes_lbl, half_likes_lbl))
        btn_remove_like.grid(row=row, column=11, sticky="nsew")

        # Кнопки для удаления дизлайков
        btn_remove_dislike = tk.Button(table_window, text="del", bg="red",
                                       command=lambda emp_id=emp[0], likes_lbl=likes_count, dislikes_lbl=dislikes_count, half_likes_lbl=half_likes_count:
                                       remove_vote_employee(emp_id, 'can_dislike', likes_lbl, dislikes_lbl, half_likes_lbl))
        btn_remove_dislike.grid(row=row, column=12, sticky="nsew")

        # Кнопки для удаления пол-лайков
        btn_remove_half_like = tk.Button(table_window, text="del", bg="red",
                                         command=lambda emp_id=emp[0], likes_lbl=likes_count, dislikes_lbl=dislikes_count, half_likes_lbl=half_likes_count:
                                         remove_vote_employee(emp_id, 'can_half_like', likes_lbl, dislikes_lbl, half_likes_lbl))
        btn_remove_half_like.grid(row=row, column=13, sticky="nsew")

    for col in range(14):
        table_window.grid_columnconfigure(col, weight=1)

    for row in range(len(employees) + 1):
        table_window.grid_rowconfigure(row, weight=1)

def remove_vote_employee(employee_id, vote_type, likes_label, dislikes_label, half_likes_label):
    if vote_type not in user_permissions or not user_permissions[vote_type]:
        messagebox.showerror("Ошибка", "У вас нет прав на выполнение этого действия.")
        return
    data = {
        "employee_id": employee_id,
        "vote_type": vote_type
    }
    try:
        response = requests.post(f'{SERVER_URL}/remove_vote', json=data)
        if response.status_code == 200:
            messagebox.showinfo("Info", response.json()["message"])
            update_like_count(employee_id, vote_type, likes_label, dislikes_label, half_likes_label)
        else:
            messagebox.showerror("Error", "Unexpected server response")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Could not reach the server: {e}")


def update_like_count(employee_id, vote_type, likes_label, dislikes_label, half_likes_label):
    employees = get_employees()
    for emp in employees:
        if emp[0] == employee_id:
            if vote_type == 'can_like':
                new_value = emp[5] if len(emp) > 5 else 0
                likes_label.config(text=f"{new_value}")
            elif vote_type == 'can_dislike':
                new_value = emp[6] if len(emp) > 6 else 0
                dislikes_label.config(text=f"{new_value}")
            elif vote_type == 'can_half_like':
                new_value = emp[7] if len(emp) > 7 else 0
                half_likes_label.config(text=f"{new_value}")
            break

def vote_employee(employee_id, vote_type, likes_label, dislikes_label, half_likes_label):
    if vote_type not in user_permissions or not user_permissions[vote_type]:
        messagebox.showerror("Ошибка", "У вас нет прав на выполнение этого действия.")
        return
    data = {
        "employee_id": employee_id,
        "vote_type": vote_type
    }
    try:
        response = requests.post(f'{SERVER_URL}/vote', json=data)
        if response.status_code == 200:
            messagebox.showinfo("Info", response.json()["message"])
            # Обновление интерфейса
            update_like_count(employee_id, vote_type, likes_label, dislikes_label, half_likes_label)
        else:
            messagebox.showerror("Error", "Unexpected server response")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Could not reach the server: {e}")



# Инициализация основного окна
root = tk.Tk()
root.title("Management App")
root.geometry("800x600")

top_frame = ttk.Frame(root)
top_frame.pack(side=tk.TOP, fill=tk.X)

btn_table = ttk.Button(top_frame, text="Таблица", command=show_table)
btn_table.pack(side=tk.LEFT)

btn_add = ttk.Button(top_frame, text="Добавить участника", command=add_new_employee)
btn_add.pack(side=tk.LEFT)

btn_register = ttk.Button(top_frame, text="Регистрация", command=register_user_dialog)
btn_register.pack(side=tk.LEFT)

btn_login = ttk.Button(top_frame, text="Вход", command=login_user_dialog)
btn_login.pack(side=tk.LEFT)

btn_logout = ttk.Button(top_frame, text="Выход", command=logout_user_dialog)
btn_logout.pack_forget()

lbl_username = tk.Label(top_frame, text="", font=("Arial", 10))
lbl_username.pack_forget()

server_status_label = tk.Label(root, text="Server Status: OFFLINE", bg="red", fg="white", font=("Arial", 14))
server_status_label.pack(pady=10)

chat_frame = ttk.Frame(root)
chat_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

chat_text = tk.Text(chat_frame, state=tk.NORMAL, wrap=tk.WORD, bg='#1a1a1a', fg='#ffffff')
chat_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

chat_entry = ttk.Entry(chat_frame)
chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

btn_send = ttk.Button(chat_frame, text="Send", command=send_message)
btn_send.pack(side=tk.RIGHT)

btn_attach = tk.Button(chat_frame, text="📎", command=attach_file)
btn_attach.pack(side=tk.LEFT)

load_chat()
auto_refresh_chat()

check_server_status()

root.mainloop()
