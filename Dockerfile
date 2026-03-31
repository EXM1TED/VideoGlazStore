FROM python:3.12-slim

WORKDIR /app

# Копируем только необходимое
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Открываем порт
EXPOSE 5000

# Запускаем приложение
CMD ["python", "run.py"]