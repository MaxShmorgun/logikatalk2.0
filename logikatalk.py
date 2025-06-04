import customtkinter as ctk
from tkinter import messagebox, filedialog, Text
import threading
from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR

# Встановлення режиму вигляду та колірної теми для CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Константи для підключення до сервера (оновіть за потребою)
NGROK_ADDRESS = "6.tcp.eu.ngrok.io"  # !!! ОНОВІТЬ ЦЕ ЗНАЧЕННЯ !!!
NGROK_PORT = 10402                  # !!! ОНОВІТЬ ЦЕ ЗНАЧЕННЯ !!!


class LogiTalkApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LogiTalk (Simple)")
        self.geometry("700x500") 
        self.minsize(500, 300)

        self.username = None
        self.sock = None
        self.connected = False
        self.chat_box = None
        self.reg_win = None
        self.name_entry = None
        self.msg_entry = None
        self._current_color_index = 0

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.open_registration_form()

    def open_registration_form(self):
        self.reg_win = ctk.CTkToplevel(self)
        self.reg_win.title("Реєстрація")
        self.reg_win.geometry("300x150") # Менше вікно без аватара
        self.reg_win.grab_set()
        self.reg_win.protocol("WM_DELETE_WINDOW", self.on_closing_main_window)

        ctk.CTkLabel(self.reg_win, text="Введіть ваше ім'я:").pack(pady=(10,0))
        self.name_entry = ctk.CTkEntry(self.reg_win, placeholder_text="Ваше ім'я")
        self.name_entry.pack(pady=5, fill="x", padx=10)
        self.name_entry.bind("<Return>", lambda e: self.register_user())
        self.name_entry.focus()

        ctk.CTkButton(self.reg_win, text="Підключитись", command=self.register_user).pack(pady=10, fill="x", padx=10)

    def register_user(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Помилка імені", "Ім'я не може бути порожнім.", parent=self.reg_win)
            return

        self.username = name
        if self.reg_win:
            self.reg_win.destroy()
            self.reg_win = None
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing_main_window)
        self.build_main_ui()
        self.connect_to_server()

    def build_main_ui(self):
        sidebar = ctk.CTkFrame(self, width=180, corner_radius=0) # Вужча бічна панель
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="Налаштування", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkButton(sidebar, text="Змінити тему", command=self.toggle_theme).pack(pady=5, fill="x", padx=5)
        ctk.CTkButton(sidebar, text="Змінити колір", command=self.toggle_color).pack(pady=5, fill="x", padx=5)
        ctk.CTkButton(sidebar, text="Про програму", command=self.show_about).pack(pady=(15,5), fill="x", padx=5)
        
        main_area = ctk.CTkFrame(self, fg_color="transparent")
        main_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        main_area.grid_rowconfigure(0, weight=1)
        main_area.grid_columnconfigure(0, weight=1)

        chat_frame = ctk.CTkFrame(main_area)
        chat_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)

        ctk_theme = ctk.ThemeManager.theme
        text_bg_color = ctk_theme["CTkFrame"]["fg_color"]
        text_fg_color = ctk_theme["CTkLabel"]["text_color"]
        
        self.chat_box = Text(chat_frame, state="disabled", wrap="word", font=("Arial", 11),
                             bg=self._apply_appearance_mode(text_bg_color),
                             fg=self._apply_appearance_mode(text_fg_color),
                             relief="sunken", borderwidth=1) 
        self.chat_box.grid(row=0, column=0, sticky="nsew")

        scrollbar = ctk.CTkScrollbar(chat_frame, command=self.chat_box.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_box.configure(yscrollcommand=scrollbar.set)

        self.chat_box.tag_config("system", foreground="gray")
        user_message_color = self._apply_appearance_mode(ctk_theme["CTkButton"]["fg_color"])
        self.chat_box.tag_config("user", foreground=user_message_color if isinstance(user_message_color, str) else user_message_color[1])
        self.chat_box.tag_config("other", foreground="#00A000")

        bottom_frame = ctk.CTkFrame(main_area)
        bottom_frame.grid(row=1, column=0, sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

        self.msg_entry = ctk.CTkEntry(bottom_frame, placeholder_text="Введіть повідомлення...")
        self.msg_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=5)
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        ctk.CTkButton(bottom_frame, text="Надіслати", command=self.send_message).grid(row=0, column=1, pady=5, padx=(0,5))

        self._append_message("Система: ", f"Ласкаво просимо, {self.username}!", "system")

    def connect_to_server(self):
        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            self.sock.connect((NGROK_ADDRESS, NGROK_PORT))
            self.connected = True

            connect_msg = f"CONN::{self.username}::\n"
            self.sock.send(connect_msg.encode('utf-8'))

            threading.Thread(target=self.recv_message, daemon=True).start()
            # Сервер має надіслати підтвердження або вітальне повідомлення
            # self._append_message("Система: ", "Успішно підключено до сервера.", "system") # Краще чекати відповіді сервера
        except Exception as e:
            self._append_message("Система: ", f"Помилка підключення: {str(e)}.", "system")
            self.connected = False
    
    def _append_message(self, prefix_text: str, main_text: str, tag: str):
        if not self.chat_box: return
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", prefix_text, tag)
        self.chat_box.insert("end", main_text, tag)
        self.chat_box.insert("end", "\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def send_message(self):
        msg = self.msg_entry.get().strip()
        if not msg: return
        if not self.connected:
            self._append_message("Система: ", "Немає з'єднання з сервером.", "system")
            return

        try:
            message_payload = f"MSG::{self.username}::{msg}\n"
            self.sock.send(message_payload.encode('utf-8'))
            self._append_message(f"{self.username}: ", msg, "user")
            self.msg_entry.delete(0, "end")
        except Exception as e:
            self._append_message("Система: ", f"Помилка відправки: {str(e)}", "system")
            self.connected = False

    def recv_message(self):
        buffer = ""
        while self.connected:
            try:
                data = self.sock.recv(1024).decode('utf-8')
                if not data: 
                    if self.connected: # Якщо з'єднання було активним
                        self._append_message("Система: ", "Сервер розірвав з'єднання.", "system")
                        self.connected = False
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip(): # Обробляємо не порожні рядки
                        self.process_server_message(line)
            except ConnectionResetError:
                if self.connected:
                    self._append_message("Система:", "З'єднання з сервером було раптово розірвано.", "system")
                self.connected = False
                break
            except UnicodeDecodeError:
                self._append_message("Система:", "Помилка декодування отриманих даних (не UTF-8).", "system")
                buffer = "" # Очистити буфер, щоб уникнути подальших помилок з цими даними
                continue
            except Exception as e:
                if self.connected:
                    self._append_message("Система:", f"Помилка отримання даних: {str(e)}", "system")
                self.connected = False
                break
        
        if not self.connected and self.username:
             self._append_message("Система: ", "Відключено від сервера.", "system")

    def process_server_message(self, message_str: str):
        try:
            parts = message_str.strip().split('::', 2)
            msg_type = parts[0]
            sender = parts[1] # Може бути "SERVER" або ім'я користувача
            content = parts[2] if len(parts) > 2 else ""

            if msg_type == "MSG":
                if sender != self.username: # Не відображати власні повідомлення, що повернулись
                    self._append_message(f"{sender}: ", content, "other")
            elif msg_type == "NOTIF": # Сповіщення від сервера
                self._append_message(f"{sender}: ", content, "system") # "SERVER: user X joined"
            elif msg_type == "CONN_ACK": # Приклад: сервер підтверджує з'єднання
                self._append_message("Система: ", content, "system")
            # Додайте інші типи, якщо сервер їх надсилає (наприклад, список користувачів)
            else:
                 self._append_message("Система: ", f"Отримано невідомий тип повідомлення: {message_str}", "system")

        except IndexError:
            self._append_message("Система: ", f"Отримано пошкоджене повідомлення від сервера: {message_str}", "system")
        except Exception as e:
            self._append_message("Система: ", f"Помилка обробки повідомлення від сервера: {e}", "system")

    def _apply_appearance_mode(self, color):
        if isinstance(color, (list, tuple)):
            return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
        return color

    def _update_widget_colors(self):
        if self.chat_box:
            ctk_theme = ctk.ThemeManager.theme
            text_bg_color = self._apply_appearance_mode(ctk_theme["CTkFrame"]["fg_color"])
            text_fg_color = self._apply_appearance_mode(ctk_theme["CTkLabel"]["text_color"])
            user_message_color = self._apply_appearance_mode(ctk_theme["CTkButton"]["fg_color"])
            
            self.chat_box.configure(bg=text_bg_color, fg=text_fg_color)
            self.chat_box.tag_config("user", foreground=user_message_color if isinstance(user_message_color, str) else user_message_color[1])

    def toggle_theme(self):
        current_mode = ctk.get_appearance_mode()
        new_mode = "Dark" if current_mode == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)
        self._update_widget_colors()

    def toggle_color(self):
        colors = ["blue", "green", "dark-blue"]
        self._current_color_index = (self._current_color_index + 1) % len(colors)
        new_color_theme_name = colors[self._current_color_index]
        ctk.set_default_color_theme(new_color_theme_name)
        messagebox.showinfo("Зміна кольору", f"Колірну тему змінено на '{new_color_theme_name}'. "
                                             "Для повного ефекту може знадобитися перезапуск.", parent=self)
        self._update_widget_colors()

    def show_about(self):
        messagebox.showinfo("Про програму", "LogiTalk v1.3 (Simple Text)\nПростий текстовий чат-клієнт.")

    def on_closing_main_window(self):
        if self.connected and self.sock and self.username:
            try:
                disconnect_msg = f"DISC::{self.username}::\n"
                self.sock.send(disconnect_msg.encode('utf-8'))
            except Exception as e:
                print(f"Помилка при надсиланні DISC: {e}")

        if self.sock: # Закриваємо сокет, якщо він існує, незалежно від connected
            try:
                self.sock.shutdown(SHUT_RDWR)
                self.sock.close()
            except Exception as e:
                print(f"Помилка при закритті сокета: {e}")
        
        self.connected = False
        self.destroy()

if __name__ == "__main__":
    app = LogiTalkApp()
    app.mainloop()