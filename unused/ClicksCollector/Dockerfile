# Вибираємо офіційний Python образ
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо залежності
COPY requirements.txt .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код сервісу
COPY . .

# Вказуємо команду запуску
CMD ["python", "app/main.py"]
