# Цікаві Алгоритми та Формули у Проекті

## 1. Нормалізація Векторів Вбудовування (L2 Normalization)

**Використання:** На кожному кроці обробки текстових та гібридних вбудовувань.

**Формула:**
```
normalized_vector = vector / ||vector||₂

де ||vector||₂ = sqrt(∑(v_i²)) for all elements
```

**Код:**
```python
# RawDataCollector/app/services/record_processing/record_processor_service.py
v = np.array(page_vector)
norm = np.linalg.norm(v)  # L2 norm
if norm > 0:
    page_vector = (v / norm).tolist()  # Normalization
```

**Мета:** Приведення всіх векторів до одиничної довжини для коректної роботи косинус-подібності в Neo4j Vector Index.

---

## 2. Взважена Агрегація Візитів Користувача (Weighted Profile Update)

**Використання:** Оновлення профіля користувача при обробці нових візитів у `hybrid_embeddings.py`.

**Формули:**

### 2.1 Розрахунок ваги для окремого візиту
```
w = reading_time × exp(-0.05 × days_since_visit) × reward_multiplier

де:
  reading_time = active_time_in_minutes (або default 0.5 хвилини)
  days_since_visit = дні, що пройшли з моменту візиту
  reward_multiplier = 2.0 якщо source='recommendation', інакше 1.0
  exp(-0.05×d) = часовий розпад (exponential decay)
```

### 2.2 Експоненціальний розпад
```
decay_factor = exp(-0.05 × d)  // d = дні від візиту до сьогодні

Example:
  d=0 (сьогодні):    decay_factor ≈ 1.0
  d=7 (тиждень):    decay_factor ≈ 0.71
  d=30 (місяць):    decay_factor ≈ 0.22
  d=100 (3+ місяці): decay_factor ≈ 0.007 (фактично нульовується)
```

### 2.3 Поточне оновлення профілю з затуханням
```
new_weighted_sum = old_weighted_sum × DECAY + batch_sum

де:
  DECAY = 0.98  // коефіцієнт затухання старих даних
  batch_sum = ∑(emb_i × w_i) for all visits in batch
  
new_total_weight = old_total_weight × DECAY + ∑w_i
```

### 2.4 Нормалізація профілю користувача
```
final_user_embedding = (new_weighted_sum / new_total_weight) / ||result||₂
```

**Код:**
```python
# RecomendationsBuilder/services/asyn/tasks/hybrid_embeddings.py, line 206-207
DECAY = 0.98
new_sum = [(s_o * DECAY) + s_b for s_o, s_b in zip(old_sum, batch_sum)]
new_w = (old_w * DECAY) + batch_w
```

**Мета:** Адаптивна агрегація історії користувача з експоненціальним затуханням старих даних, щоб свіжі візити мали більший вплив.

---

## 3. Усунення Візиту з Профіля (Inverse Weighted Subtraction)

**Використання:** Коли користувач видаляє візит, потрібно обновити його профіль.

**Формула:**
```
w_to_remove = active_time × exp(-0.05 × days_since) × reward_mult

new_sum[i] = old_sum[i] - (page_embedding[i] × w_to_remove)

new_norm = ||new_sum||₂ = sqrt(∑(new_sum_j²))

final_embedding[i] = new_sum[i] / new_norm  (якщо new_norm > 0)
```

**Cypher запит** (4 CTE):
```cypher
-- Step 1: Знайти візит і розрахувати його вагу
WITH u, v, p, w,
     (coalesce(v.active_time, 0.5) * 
      exp(-0.05 * duration.inDays(datetime(v.visitedAt[-1]), datetime()).days) * 
      CASE WHEN v.source = 'recommendation' THEN 2.0 ELSE 1.0 END) AS w

-- Step 2: Відняти вектор (element-wise)
WITH u, v, p, w, new_sum,
     [i IN range(0, size(u.sumWeightedTextEmbedding)-1) | 
      u.sumWeightedTextEmbedding[i] - (p.text_embedding[i] * w)]
     AS new_sum

-- Step 3: Розрахувати новий коефіцієнт нормалізації
WITH u, v, p, w, new_sum,
     sqrt(reduce(s = 0.0, x IN new_sum | s + x*x)) AS norm

-- Step 4: Нормалізувати
WITH u, v, p, w, new_sum, norm,
     CASE WHEN norm > 0 THEN [x IN new_sum | x / norm] 
          ELSE [x IN new_sum | 0.0] END AS new_normalized_emb
```

**Код:**
```python
# RecomendationsReader/app/services/history_service.py, delete_visit method
```

---

## 4. Гібридна Рекомендація з Взважуванням (Unified Recommendation Scoring)

**Використання:** Об'єднання текстово-подібних та структурних рекомендацій.

**Формула:**
```
t_score = text_similarity_score
h_score = hybrid_similarity_score (GraphSAGE)

t_contrib = t_score × (1.0 - weight_struct)
h_contrib = h_score × weight_struct

final_score = t_contrib + h_contrib

де weight_struct ∈ [0.0, 1.0] - користувацький параметр балансу
```

**Логіка класифікації типу рекомендації:**
```
if abs(h_score - t_score) <= 0.03:
    rec_type = "mixed"      // обидва методи збігаються
elif h_score > t_score:
    rec_type = "hybrid"     // структурна подібність переважає
else:
    rec_type = "text"       // текстова подібність переважає
```

**Код:**
```python
# RecomendationsReader/app/services/unified_recommendation_service.py
t_score = text_recs[pid]['score'] if pid in text_recs else 0.0
h_score = hybrid_recs[pid]['score'] if pid in hybrid_recs else 0.0

t_contrib = t_score * (1.0 - weight_struct)
h_contrib = h_score * weight_struct
final_score = t_contrib + h_contrib

if final_score < 0.1:
    continue  # Фільтрація низькоякісних рекомендацій
```

---

## 5. Косинус-Подібність у Neo4j Vector Index

**Використання:** Вбудований механізм пошуку в Neo4j для векторних індексів.

**Формула:**
```
similarity = (vector_1 · vector_2) / (||vector_1||₂ × ||vector_2||₂)

де · позначає скалярний добуток

Для нормалізованих векторів (||vector||₂ = 1):
  similarity = vector_1 · vector_2
  
Діапазон: [-1, 1]
  1.0  = ідеальна подібність (однакові вектори)
  0.0  = ортогональні (независимі)
  -1.0 = протилежні
```

**Код Neo4j:**
```cypher
-- Vector Index creation (384D для text, 128D для hybrid)
CREATE VECTOR INDEX page_text_index IF NOT EXISTS
FOR (p:Page) ON (p.text_embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 384,
    `vector.similarity_function`: 'cosine'
  }
}

-- Vector search
CALL db.index.vector.queryNodes('page_text_index', $k, $embedding)
YIELD node AS page, score
```

---

## 6. GraphSAGE Вбудовування (Hybrid Embeddings)

**Використання:** RawDataCollector/services/asyn/tasks/hybrid_embeddings.py

**Параметри:**
```
embeddingDimension: 128D (меньше за text 384D для ефективності)
negativeSampleWeight: 5  (вага негативних прикладів)
sampleSizes: [25, 10]    (розміри батчів на кожному hop)
aggregator: "meanPool"   (осереднення features в окиці)
epochs: 10-20 (залежить від розміру графа)
```

**Архітектура графа для GDS:**
```
Вузли: User, Page, Category
Ребра:
  - User-[:VISIT]->Page (активний граф дружби)
  - Page-[:IN_CATEGORY]->Category (статичні метадані)
  - weight = log10(coalesce(r.active_time, 1.0) + 9.0)
```

**Вага ребра для VISIT:**
```
weight = log10(active_time + 9.0)

Example:
  active_time=0.5 min → weight = log10(9.5) ≈ 0.978
  active_time=1 min   → weight = log10(10) = 1.0
  active_time=10 min  → weight = log10(19) ≈ 1.279
  active_time=100 min → weight = log10(109) ≈ 2.037
```

---

## 7. Тренди з часовим фільтруванням (Trending Fallback)

**Використання:** Для користувачів без сформованого профіля.

**Формула:**
```
score_i = count_of_visits_in_last_7_days[page_i]

cutoff_date = datetime.now() - 7 days

trending_pages = all_pages WHERE count(visits after cutoff_date) > 0

sorted by score DESC
```

**Код:**
```python
# RecomendationsReader/app/services/unified_recommendation_service.py
cutoff_str = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

for r in results:
    valid_visits = 0
    for t in r.get("visit_times", []):
        time_str = str(t[-1]) if isinstance(t, list) else str(t)
        if time_str[:19] >= cutoff_str[:19]:
            valid_visits += 1
    
    if valid_visits > 0:
        trending_data.append({
            "score": valid_visits,  # Кількість свіжих візитів
            "visit_count": len(r["visit_times"])  # Глобальна статистика
        })
```

---

## 8. Фільтрація Content-у (Правила визначення)

**Використання:** Visually determine is URL/content recommendable.

**Regex фільтри:**
```python
# Заборонені типи сторінок:
BLOCKED_PATTERNS = [
    r"^chrome://",              # Chrome протоколи
    r"/login", r"/signin",      # Автентифікація
    r"/cart", r"/checkout",     # E-commerce
    r"/account", r"/settings",  # Personal
    r"google\.com/search",      # Search results
    r"youtube\.com/results"     # Video search
]
```

**LLM-базована логіка:**
```
Питання: Is this page just a login form without article?
         Is this a 404 or error page?
         Is this behind a Captcha/Cloudflare?

Відповідь: { "is_recommendable": true/false, "reason": "..." }
```

---

## 9. URL Нормалізація

**Використання:** Приведення до канонічної форми для уникнення дублів.

**Правила:**
```
1. Видалити fragment (#...):  https://site.com/page#section → https://site.com/page
2. Видалити query параметри:  https://site.com/page?utm=123 → https://site.com/page
3. Стандартизувати scheme:     http:// → https://
4. Видалити trailing slash:    https://site.com/ → https://site.com
5. Домен lowercase:             https://SITE.COM → https://site.com
```

**Код:**
```python
# RawDataCollector/app/services/record_processing/url_processor_service.py
def normalize(self, url: str) -> str:
    parsed = urlparse(url)
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment='',
        query=''
    )
    result = urlunparse(normalized)
    if result.endswith('/'):
        result = result[:-1]
    return result
```

---

## 10. Часова Конверсія та Дата-Час Обробка

**Використання:** Обробка активності брауера в мілісекундах.

**Конверсія:**
```
active_time_minutes = active_time_milliseconds / 60000

Example:
  30000 ms = 0.5 min
  300000 ms = 5 min
  1800000 ms = 30 min
```

**DateTime вирази в Cypher:**
```
current_time = datetime()
past_time = datetime() - duration('P7D')     // 7 днів назад
past_time = datetime() - duration('PT24H')   // 24 години назад
past_time = datetime() - duration('PT1H')    // 1 година назад

duration.inDays(past_date, current_date) = кількість днів між датами
```

---

## 11. Матриця Інцидентної Ваги для GraphSAGE

**Формула для VISIT ребра:**
```
weight_visit = log10(active_time + 9.0)
```

**Формула для IN_CATEGORY ребра:**
```
weight_in_category = 1.0 (фіксована одиниця)
```

**Використання в GDS:**
```cypher
MATCH (n) WHERE n:User OR n:Page OR n:Category RETURN n
WITH n, coalesce(n.text_embedding, [zeros...]) AS features

MATCH (start)-[r]->(end)
WHERE type(r) IN ["VISIT", "IN_CATEGORY"]
WITH r,
     CASE type(r)
       WHEN "VISIT" THEN log10(coalesce(r.active_time, 1.0) + 9.0)
       WHEN "IN_CATEGORY" THEN 1.0
       ELSE 0.0
     END AS weight
```

---

## 12. K-Nearest Neighbors Пошук з Фільтрацією

**Використання:** Vector search з виключенням вже переглянутих сторінок.

**Псевдокод:**
```
1. Отримати user embedding
2. candidates = k-NN search(index, embedding, k=n*multiplier)
3. Отримати all pages що user VISIT-した
4. filter candidates WHERE NOT page IN visited_pages
5. Sort by score DESC
6. LIMIT to n results
7. Return first n non-visited pages
```

**Код:**
```python
# RecomendationsReader/app/services/recomendation_builder_service.py
candidates_to_fetch = n * 10

CALL db.index.vector.queryNodes('page_hybrid_index', $k, $embedding)
YIELD node AS page, score

WHERE NOT EXISTS {
    MATCH (u:User {id: $user_id})-[v:VISIT]->(page)
}

ORDER BY score DESC
LIMIT $limit
```

---

## Резюме Ключових Констант

| Константа | Значення | Назначение |
|-----------|----------|-----------|
| EMBEDDING_SIZE (text) | 384D | Розмір текстового вбудовування |
| HYBRID_DIM | 128D | Розмір гібридного вбудовування (GraphSAGE) |
| DECAY | 0.98 | Затухання в profile update |
| TIME_DECAY | -0.05 | Коефіцієнт експоненціального затухання часу |
| REWARD_MULT | 2.0 | Множник ваги за recommendation visit |
| DEFAULT_ACTIVE_TIME | 0.5 min | Базова вага для візиту без активності |
| SIMILARITY_THRESHOLD | 0.1 | Мінімальна оцінка для включення в рекомендації |
| SCORE_DEVIATION | 0.03 | Поріг для "mixed" класифікації |
| CANVAS_LOG_SIZE | 10(log) | Логарифмічна базис для ваги активної часу |
| GDS_AGGREGATOR | meanPool | Агрегатор для GraphSAGE |
| GDS_NEGATIVE_WEIGHT | 5 | Вага негативних прикладів в GraphSAGE |
