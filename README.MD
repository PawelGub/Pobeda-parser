# 🚀 Pobeda Parser - Flight Search

Полнофункциональная платформа для поиска авиабилетов авиакомпании "Победа" с  минималистичной аналитикой и масштабируемой архитектурой.

## 🌟 Возможности

- 🔍 **Умный поиск** - поиск рейсов на 30 дней вперед
- 🌍 **Куда угодно** - AI подбор самых дешевых направлений  
- 📊 **Аналитика цен** - графики и статистика
- 🐳 **Cloud Native** - Docker & Kubernetes готовность
- 📈 **Мониторинг** - ELK стек + Grafana
- 🔄 **Event-Driven** - Kafka для обработки событий
- ⚡ **Кеширование** - Redis для ускорения запросов

## 🏗 Архитектура
┌─────────────────┐ ┌──────────────────┐ ┌─────────────────┐
│ Frontend │───▶│ Backend API │───▶│ PostgreSQL │
│ (React/Vue) │ │ (FastAPI) │ │ (Database) │
└─────────────────┘ └──────────────────┘ └─────────────────┘
│ ▲
│ │
┌───┴──┴───┐
│ Kafka │
│ (Events) │
└───┬──┬───┘
│ │
┌─────────────┘ └─────────────┐
│ │
┌────┴─────┐ ┌─────┴────┐
│ Redis │ │ ELK │
│ (Cache) │ │ (Logs) │
└──────────┘ └──────────┘
## 🚀 Быстрый старт

### Локальный запуск (Docker)
# 1. База данных и кеш
kubectl apply -f k8s/postgres.yml
kubectl apply -f k8s/redis.yml
kubectl apply -f k8s/elasticsearch.yml

# 2. Backend со ВСТРОЕННОЙ Kafka (уже включает Zookeeper)
kubectl apply -f k8s/backend-with-kafka.yml

# 3. Kafka UI (если нужен)
kubectl apply -f k8s/kafka-ui.yml

#4. FRONTEND:

kubectl apply -f k8s/frontend.yml

Полная инструкция по port-forward:
1. Backend API (основной сервис)
   в консоли(powershell, bash):
   kubectl port-forward service/pobeda-backend-service 8000:8000
   URL: http://localhost:8000
   Docs: http://localhost:8000/docs

2. Frontend (веб-интерфейс)
   в консоли(powershell, bash):
   kubectl port-forward service/frontend 3000:80
   URL: http://localhost:3000

3. Kafka UI (мониторинг Kafka)
   в консоли(powershell, bash):
   kubectl port-forward service/kafka-ui 8080:8080
   URL: http://localhost:8080

4. Elasticsearch (логи и поиск)
   в консоли(powershell, bash):
   kubectl port-forward service/elasticsearch 9200:9200
   URL: http://localhost:9200

P.S. в ночь со вторника на среду сервера победы отключаются, видимо на обновления...

🔧 Технологии
Backend: FastAPI, SQLAlchemy, PostgreSQL, Redis, Kafka
Frontend: React/Vue, Chart.js, Bootstrap
Infra: Docker, Kubernetes, ELK, Grafana
Monitoring: Prometheus, Kibana, Kafka UI
