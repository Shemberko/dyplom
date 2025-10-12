# Базовий образ Python
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Робоча директорія
WORKDIR /app

# Копіюємо залежності
COPY requirements.txt .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо увесь код сервісу
COPY . .

# Відкриваємо порт для FastAPI
EXPOSE 8000

# Запускаємо FastAPI через Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]