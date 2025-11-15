# Вибираємо офіційний Python образ
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо залежності
COPY requirements.txt .

RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.2.0" torchvision torchaudio


# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код сервісу
COPY . .

# Вказуємо команду запуску
CMD ["python", "app/main.py"]
