import traceback
from typing import List, Optional, Tuple, Any, Dict
from sentence_transformers import SentenceTransformer

# --- [ВИПРАВЛЕНО 1: Абсолютні імпорти] ---
# Імпортуємо 'app' та 'query_runner' з абсолютних шляхів
from services.asyn.celery_worker import app
from services.neo4j.query_runner import query_runner as neo4j_client
# --- [КІНЕЦЬ ВИПРАВЛЕННЯ] ---


# Ініціалізація моделі (один раз при запуску worker'а)
try:
    s_model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    print(f"Помилка завантаження моделі SentenceTransformer: {e}")
    s_model = None

# Параметри
EMBEDDING_DIM = 384


def incrementally_update_text_profile_from_recent(neo4j_client: Any, user_id: str, hours_ago: int = 24) -> Any:
    """
    ІНКРЕМЕНТАЛЬНО оновлює TEXT профіль, додаючи всі відвідування
    за останні 'hours_ago' годин до існуючого профілю.
    """
    print(f"Запуск пакетного інкрементального оновлення (Text) для {user_id}...")

    # --- [ВИПРАВЛЕНО 11: Видалено коментарі] ---
    FETCH_Q = """
    MATCH (u:User {id: $user_id})-[v:VISIT]->(p:Page)
    WHERE p.text_embedding IS NOT NULL
      AND v.active_time IS NOT NULL 
      AND v.total_open_time IS NOT NULL
      AND v.visitedAt IS NOT NULL
      AND any(ts IN v.visitedAt WHERE datetime(ts) >= datetime() - duration({hours: $hours_ago}))
    RETURN p.text_embedding AS emb, 
           (coalesce(toFloat(v.active_time), 0.0) + 0.1 * coalesce(toFloat(v.total_open_time), 0.0)) AS w
    """
    # --- [КІНЕЦЬ ВИПРАВЛЕННЯ] ---
    try:
        records = neo4j_client.run_query(FETCH_Q, {'user_id': user_id, 'hours_ago': hours_ago})
    except Exception as e:
        print(f"Помилка (Text) зчитування відвідувань для {user_id}: {e}")
        return None

    (batch_sum_weighted, batch_total_w, dim) = _aggregate_visits(records)
    if not batch_sum_weighted:
        return "Немає нових відвідувань (Text) для оновлення."

    try:
        old_profile = neo4j_client.run_one(
            "MATCH (u:User {id: $user_id}) RETURN u.sumWeightedTextEmbedding AS old_sum, u.totalTextWeight AS old_total",
            {'user_id': user_id}
        )
    except Exception as e:
        print(f"Помилка (Text) зчитування старого профілю для {user_id}: {e}")
        return None

    if old_profile is None:
        old_profile = {}

    old_sum = validate_embedding_vector(old_profile.get("old_sum")) or [0.0] * dim
    old_total = float(old_profile.get("old_total") or 0.0)
    
    if len(old_sum) != dim:
        old_sum = (old_sum + [0.0] * dim)[:dim]

    new_sum = [s_old + s_new for s_old, s_new in zip(old_sum, batch_sum_weighted)]
    new_total = old_total + batch_total_w
    
    new_embedding = [x / new_total for x in new_sum] if new_total != 0.0 else new_sum
    
    WRITE_Q = """
    MATCH (u:User {id: $user_id})
    SET u.sumWeightedTextEmbedding = $sum,
        u.totalTextWeight = $total,
        u.textEmbedding = $embedding
    RETURN u.id
    """
    try:
        return neo4j_client.run_query(WRITE_Q, {'user_id': user_id, 'sum': new_sum, 'total': new_total, 'embedding': new_embedding})
    except Exception as e:
        print(f"Помилка (Text) запису оновленого профілю для {user_id}: {e}")
        traceback.print_exc()
        return None

def validate_embedding_vector(vec: Optional[List[float]]) -> Optional[List[float]]:
    if vec is None: return None
    return [float(x) for x in vec]

def compute_incremental_update(sum_weighted: Optional[List[float]],
                               total_weight: float,
                               page_emb: List[float],
                               weight: float) -> Tuple[List[float], float, List[float]]:
    pe = [float(x) for x in page_emb]
    n = len(pe)
    if sum_weighted is None: sum_weighted = [0.0] * n
    else:
        if len(sum_weighted) < n: sum_weighted = sum_weighted + [0.0] * (n - len(sum_weighted))
        elif len(sum_weighted) > n: sum_weighted = sum_weighted[:n]
    v_new_weighted = [v * float(weight) for v in pe]
    sum_new = [s + v for s, v in zip(sum_weighted, v_new_weighted)]
    total_new = float(total_weight) + float(weight)
    if total_new == 0.0: embedding = sum_new
    else: embedding = [x / total_new for x in sum_new]
    return sum_new, total_new, embedding


   
def _aggregate_visits(visit_records: List[Dict[str, Any]]) -> Tuple[List[float], float, int]:
    """
    Допоміжна функція: агрегує список записів відвідувань у (sum_weighted, total_w, dim).
    """
    embeddings: List[List[float]] = []
    weights: List[float] = []
    
    for r in visit_records:
        emb = r.get("emb")
        w = r.get("w")
        if emb:
            embeddings.append([float(x) for x in emb])
            weights.append(float(w or 0.0))

    if not embeddings:
        return ([], 0.0, 0)

    dim = len(embeddings[0])
    batch_sum_weighted = [0.0] * dim
    batch_total_w = 0.0
    
    for emb, w in zip(embeddings, weights):
        if len(emb) != dim:
            emb = emb[:dim] if len(emb) > dim else emb + [0.0] * (dim - len(emb))
        
        for i in range(dim):
            batch_sum_weighted[i] += emb[i] * w
        batch_total_w += w

    return (batch_sum_weighted, batch_total_w, dim)

@app.task(bind=True, max_retries=3)
def task_update_text_profile_batch(self ,neo4j_client: Any, user_id: str, hours_ago: int = 24):
    """
    Celery task: Інкрементально оновлює text профіль на основі
    відвідувань за останні 'hours_ago' годин.
    """
    try:
        result = incrementally_update_text_profile_from_recent(neo4j_client, user_id, hours_ago)
        return f"Пакетне оновлення (Text) для {user_id} завершено. Результат: {result}"
    except Exception as exc:
        print(f"Помилка таска (Text Batch) для {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)