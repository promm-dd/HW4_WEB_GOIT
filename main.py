from http.server import SimpleHTTPRequestHandler, HTTPServer
import socket
import threading
import os
import json
from urllib.parse import parse_qs
from datetime import datetime

# Файл для хранения сообщений
DATA_FILE = "storage/data.json"
# Убедимся, что папка для хранения сообщений существует
os.makedirs("storage", exist_ok=True)
# Если файл не существует, создаём пустой JSON
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# Класс для обработки HTTP-запросов
class RequestHandler(SimpleHTTPRequestHandler):
    # Обработка GET-запросов
    def do_GET(self):
        if self.path == "/":  # Главная страница
            self.serve_file("templates/index.html")
        elif self.path == "/message":  # Страница отправки сообщения
            self.serve_file("templates/message.html")
        elif self.path == "/static/style.css":  # Стили
            self.serve_file("static/style.css", "text/css")
        else:  # Если маршрут не найден, возвращаем страницу ошибки
            self.serve_file("templates/error.html", status=404)

    # Обработка POST-запросов
    def do_POST(self):
        if self.path == "/message":  # Обработка отправки сообщения
            content_length = int(self.headers["Content-Length"])  # Размер данных запроса
            body = self.rfile.read(content_length).decode("utf-8")  # Чтение тела запроса
            data = parse_qs(body)  # Парсим данные формы

            # Получаем имя пользователя и сообщение
            username = data.get("username", [""])[0]
            message = data.get("message", [""])[0]

            # Если данные заполнены отправляем их на сокет-сервер
            if username and message:
                send_to_socket_server(username, message)
                self.respond("Message sent!")  # Ответ клиенту
            else:
                self.respond("Invalid data!", 400)  # Ошибка если данные некорректны
        else:
            self.respond("Not Found", 404)  # Если маршрут не поддерживается

    # Функция для отправки файлов
    def serve_file(self, path, content_type="text/html", status=200):
        self.send_response(status)  # Устанавливаем статус ответа
        self.send_header("Content-Type", content_type)  # Устанавливаем тип контента
        self.end_headers()  # Завершаем заголовки
        try:
            with open(path, "rb") as f:  # Открываем файл и читаем содержимое
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.wfile.write(b"File not found")  # Сообщение если файл не найден

    # Простая функция для отправки текстового ответа
    def respond(self, message, status=200):
        self.send_response(status)
        self.end_headers()
        self.wfile.write(message.encode())

# Функция для отправки данных на сокет-сервер
def send_to_socket_server(username, message):
    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Создаём UDP-сокет
    udp_client.sendto(f"{username}:{message}".encode("utf-8"), ("127.0.0.1", 5000))  # Отправляем данные
    udp_client.close()  # Закрываем сокет

# Запуск сокет-сервера для приёма сообщений
def start_socket_server():
    udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Создаём UDP-сокет
    udp_server.bind(("127.0.0.1", 5000))  # Привязываем сокет к порту 5000
    while True:
        data, _ = udp_server.recvfrom(1024)  # Ждём данные от клиента
        username, message = data.decode("utf-8").split(":", 1)  # Разделяем имя и сообщение
        timestamp = datetime.now().isoformat()  # Временная метка

        # Сохраняем сообщение в файл
        with open(DATA_FILE, "r+") as f:
            db = json.load(f)  # Загружаем существующие сообщения
            db[timestamp] = {"username": username, "message": message}  # Добавляем новое сообщение
            f.seek(0)  # Перемещаем указатель в начало файла
            json.dump(db, f, indent=4)  # Сохраняем обновлённый JSON

# Запуск HTTP сервера
if __name__ == "__main__":
    threading.Thread(target=start_socket_server, daemon=True).start()  # Запускаем сокет-сервер в отдельном потоке
    HTTPServer(("0.0.0.0", 3000), RequestHandler).serve_forever() # Запускаем HTTP-сервер на порту 3000