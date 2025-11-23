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



# ==============================================================================
# КОД ДЛЯ STRUCTURAL EMBEDDINGS (Односторінкове оновлення)
# ==============================================================================

def build_update_query() -> str:
    """
    Cypher query для інкрементального оновлення STRUCTURAL профілю.
    """
    return """
    MATCH (u:User {id: $user_id})
    MATCH (p:Page) WHERE elementId(p) = $page_element_id
    WITH u, p.structuralEmbedding AS V_p, toFloat($active_time) AS W_new
    WHERE V_p IS NOT NULL AND size(V_p) > 0
    WITH u, V_p, W_new,
         COALESCE(u.sumWeightedStructuralEmbedding, [x IN range(0, size(V_p)-1) | 0.0]) AS Sum_old,
         COALESCE(u.totalStructuralWeight, 0.0) AS TotalW_old
    WITH u, [i IN range(0, size(V_p)-1) | V_p[i] * W_new] AS V_new_weighted, Sum_old, TotalW_old, W_new
    WITH u, [i IN range(0, size(Sum_old)-1) | Sum_old[i] + V_new_weighted[i]] AS Sum_new,
         TotalW_old + W_new AS TotalW_new
    SET u.sumWeightedStructuralEmbedding = Sum_new,
        u.totalStructuralWeight = TotalW_new,
        u.structuralEmbedding = CASE 
            WHEN TotalW_new = 0.0 THEN Sum_new 
            ELSE [i IN range(0, size(Sum_new)-1) | Sum_new[i] / TotalW_new] 
        END
    RETURN u.id
    """


def run_update_cypher(neo4j_client: Any, user_id: str, page_element_id: str, active_time: float) -> Any:
    """
    Виконує build_update_query() (для structural) через neo4j_client.run_query().
    """
    q = build_update_query()
    results = neo4j_client.run_query(q, {'user_id': user_id, 'page_element_id': page_element_id, 'active_time': active_time})
    return results[0] if results else None

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
# ( ... кінець незмінних функцій ... )


def apply_incremental_update_via_python(neo4j_client: Any, user_id: str, page_element_id: str, active_time: float) -> Any:
    """
    Python‑варіант оновлення (для structural):
    """
    SELECT_Q = """
    MATCH (u:User {id: $user_id})
    MATCH (p:Page) WHERE elementId(p) = $page_element_id
    RETURN u.sumWeightedStructuralEmbedding AS sumWeighted, u.totalStructuralWeight AS totalWeight, p.structuralEmbedding AS page_emb
    """
    try:
        res_list = neo4j_client.run_query(SELECT_Q, {'user_id': user_id, 'page_element_id': page_element_id})
        if not res_list:
            return None
        row = res_list[0]
    except Exception as e:
        print(f"Error reading for python update: {e}")
        return None
        
    sumWeighted = row.get("sumWeighted")
    totalWeight = row.get("totalWeight") or 0.0
    page_emb = row.get("page_emb")

    page_emb = validate_embedding_vector(page_emb)
    if not page_emb:
        return None

    sumWeighted = validate_embedding_vector(sumWeighted)
    totalWeight = float(totalWeight or 0.0)

    sum_new, total_new, embedding = compute_incremental_update(sumWeighted, totalWeight, page_emb, active_time)

    WRITE_Q = """
    MATCH (u:User {id: $user_id})
    SET u.sumWeightedStructuralEmbedding = $sum_new,
        u.totalStructuralWeight = $total_new,
        u.structuralEmbedding = $embedding
    RETURN u.id
    """
    try:
        return neo4j_client.run_query(WRITE_Q, {'user_id': user_id, 'sum_new': sum_new, 'total_new': total_new, 'embedding': embedding})
    except Exception as e:
        print(f"Error writing incremental update: {e}")
        traceback.print_exc()
        return None


def recompute_user_from_visits_via_python(neo4j_client: Any, user_id: str) -> Any:
    """
    Повне перерахування STRUCTURAL профілю користувача з усіх VISIT зв'язків.
    """
    FETCH_Q = """
    MATCH (u:User {id: $user_id})-[v:VISIT]->(p:Page)
    WHERE p.structuralEmbedding IS NOT NULL 
      AND v.active_time IS NOT NULL 
      AND v.total_open_time IS NOT NULL
    RETURN p.structuralEmbedding AS emb, 
           (coalesce(toFloat(v.active_time), 0.0) + 0.1 * coalesce(toFloat(v.total_open_time), 0.0)) AS w
    """
    try:
        records = neo4j_client.run_query(FETCH_Q, {'user_id': user_id})
    except Exception as e:
        print(f"Error fetching visits for recompute: {e}")
        return None

    # ( ... код агрегації без змін ... )
    embeddings: List[List[float]] = []
    weights: List[float] = []
    for r in records: 
        emb = r.get("emb")
        w = r.get("w")
        if emb:
            embeddings.append([float(x) for x in emb])
            weights.append(float(w or 0.0))
    if not embeddings:
        return None
    dim = len(embeddings[0])
    sum_weighted = [0.0] * dim
    total_w = 0.0
    for emb, w in zip(embeddings, weights):
        if len(emb) != dim:
            emb = emb[:dim] if len(emb) > dim else emb + [0.0] * (dim - len(emb))
        for i in range(dim):
            sum_weighted[i] += emb[i] * w
        total_w += w
    embedding = [x / total_w for x in sum_weighted] if total_w != 0.0 else sum_weighted
    # ( ... кінець коду агрегації ... )

    WRITE_Q = """
    MATCH (u:User {id: $user_id})
    SET u.sumWeightedStructuralEmbedding = $sum_weighted,
        u.totalStructuralWeight = $total_w,
        u.structuralEmbedding = $embedding
    RETURN u.id
    """
    try:
        return neo4j_client.run_query(WRITE_Q, {'user_id': user_id, 'sum_weighted': sum_weighted, 'total_w': total_w, 'embedding': embedding})
    except Exception as e:
        print(f"Error writing recomputed user: {e}")
        traceback.print_exc()
        return None


@app.task(bind=True, max_retries=3)
def update_user_embedding_incrementally(self, user_id: str, page_element_id: str, active_time: float):
    """
    Celery task: інкрементальне оновлення STRUCTURAL профілю.
    """
    try:
        try:
            res = run_update_cypher(neo4j_client, user_id, page_element_id, active_time)
            return f"User {user_id} STRUCTURAL profile updated via Cypher."
        except Exception as e_cy:
            print(f"Cypher (structural) update failed, falling back to Python update: {e_cy}")
            traceback.print_exc()
            res_py = apply_incremental_update_via_python(neo4j_client, user_id, page_element_id, active_time)
            if res_py is None:
                raise RuntimeError("Both cypher and python (structural) update failed")
            return f"User {user_id} STRUCTURAL profile updated via Python."
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)



@app.task(bind=True, max_retries=3)
def task_update_structural_profile_batch(self, user_id: str, hours_ago: int = 24):
    """
    Celery task: Інкрементально оновлює structural профіль на основі
    відвідувань за останні 'hours_ago' годин.
    """
    try:
        result = incrementally_update_structural_profile_from_recent(neo4j_client, user_id, hours_ago)
        return f"Пакетне оновлення (Structural) для {user_id} завершено. Результат: {result}"
    except Exception as exc:
        print(f"Помилка таска (Structural Batch) для {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


    
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

def incrementally_update_structural_profile_from_recent(neo4j_client: Any, user_id: str, hours_ago: int = 24) -> Any:
    """
    ІНКРЕМЕНТАЛЬНО оновлює STRUCTURAL профіль, додаючи всі відвідування
    за останні 'hours_ago' годин до існуючого профілю.
    """
    print(f"Запуск пакетного інкрементального оновлення (Structural) для {user_id}...")
    
    # --- [ВИПРАВЛЕНО 9: Видалено коментарі] ---
    FETCH_Q = """
    MATCH (u:User {id: $user_id})-[v:VISIT]->(p:Page)
    WHERE p.structuralEmbedding IS NOT NULL 
      AND v.active_time IS NOT NULL 
      AND v.total_open_time IS NOT NULL
      AND v.visitedAt IS NOT NULL
      AND any(ts IN v.visitedAt WHERE datetime(ts) >= datetime() - duration({hours: $hours_ago}))
    RETURN p.structuralEmbedding AS emb, 
           (coalesce(toFloat(v.active_time), 0.0) + 0.1 * coalesce(toFloat(v.total_open_time), 0.0)) AS w
    """
    # --- [КІНЕЦЬ ВИПРАВЛЕННЯ] ---
    try:
        records = neo4j_client.run_query(FETCH_Q, {'user_id': user_id, 'hours_ago': hours_ago})
    except Exception as e:
        print(f"Помилка (Structural) зчитування відвідувань для {user_id}: {e}")
        return None

    (batch_sum_weighted, batch_total_w, dim) = _aggregate_visits(records)
    if not batch_sum_weighted:
        return "Немає нових відвідувань (Structural) для оновлення."

    try:
        old_profile = neo4j_client.run_one(
            "MATCH (u:User {id: $user_id}) RETURN u.sumWeightedStructuralEmbedding AS old_sum, u.totalStructuralWeight AS old_total",
            {'user_id': user_id}
        )
    except Exception as e:
        print(f"Помилка (Structural) зчитування старого профілю для {user_id}: {e}")
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
    SET u.sumWeightedStructuralEmbedding = $sum,
        u.totalStructuralWeight = $total,
        u.structuralEmbedding = $embedding
    RETURN u.id
    """
    try:
        return neo4j_client.run_query(WRITE_Q, {'user_id': user_id, 'sum': new_sum, 'total': new_total, 'embedding': new_embedding})
    except Exception as e:
        print(f"Помилка (Structural) запису оновленого профілю для {user_id}: {e}")
        traceback.print_exc()
        return None
