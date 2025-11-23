# Використовуємо образ Python 3.11 Slim
FROM python:3.11-slim

# Встановлюємо робочий каталог
WORKDIR /app

# Копіюємо файл залежностей та встановлюємо їх
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо решту коду (включаючи services/)
COPY . /app

# [ЗМІНА] Встановлюємо команду за замовчуванням на запуск Celery Worker.
# Якщо контейнер запускається без команди (docker run), він стає Worker'ом.
CMD ["celery", "-A", "services.asyn.celery_worker", "worker", "-l", "info", "-Q", "default"]