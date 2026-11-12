# ============================================================
# Зручні команди для запуску тестів
# ============================================================
#
# Використання:
#   make test            — запустити ВСІ тести через Docker
#   make test-reader     — тільки RecommendationsReader
#   make test-server     — тільки server
#   make test-rawdata    — тільки RawDataCollector
#   make test-builder    — тільки RecommendationsBuilder
#

.PHONY: test test-reader test-server test-rawdata test-builder \
        test-local-reader test-local-server test-local-rawdata test-local-builder

# --- Запуск ВСІХ тестів у Docker ---
test:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
	docker compose -f docker-compose.test.yml down --remove-orphans

# --- Окремі сервіси через Docker ---
test-reader:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit test-reader
	docker compose -f docker-compose.test.yml rm -f test-reader

test-server:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit test-server
	docker compose -f docker-compose.test.yml rm -f test-server

test-rawdata:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit test-rawdata
	docker compose -f docker-compose.test.yml rm -f test-rawdata

test-builder:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit test-builder
	docker compose -f docker-compose.test.yml rm -f test-builder

# --- Локальний запуск (без Docker) ---
test-local-reader:
	cd microservices/RecommendationsReader && \
	pip install -q -r requirements.txt -r requirements-test.txt && \
	PYTHONPATH=. pytest tests/ -v --tb=short

test-local-server:
	cd server && \
	pip install -q -r requirements.txt -r requirements-test.txt && \
	PYTHONPATH=. pytest tests/ -v --tb=short

test-local-rawdata:
	cd microservices/RawDataCollector && \
	pip install -q -r requirements.txt -r requirements-test.txt && \
	PYTHONPATH=. pytest tests/ -v --tb=short

test-local-builder:
	cd microservices/RecommendationsBuilder && \
	pip install -q -r requirements.txt -r requirements-test.txt && \
	PYTHONPATH=. pytest tests/ -v --tb=short

