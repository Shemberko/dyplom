import traceback
from typing import List, Optional, Tuple, Any, Dict
from services.asyn.celery_worker import app
from services.neo4j.query_runner import query_runner as neo4j_client

# Параметри
HYBRID_DIM = 128  # Розмірність вихідного вектора GraphSAGE

# ==============================================================================
# 1. ОСНОВНА ЛОГІКА GRAPHSAGE (Винесена в окрему функцію)
# ==============================================================================

def _execute_graphsage_logic(client: Any) -> str:
    """
    Внутрішня функція, яка виконує логіку GraphSAGE (drop, project, train, stream, write).
    Повертає рядок-результат.
    """
    graph_name = "hybridUserPageGraph"
    model_name = "hybridModel"
    
    # Очищення старих проекцій та моделей
    try:
        client.run_query(f"CALL gds.graph.drop('{graph_name}', false)")
        client.run_query(f"CALL gds.beta.model.drop('{model_name}', false)")
    except Exception:
        pass

    # Крок 1: Проєкція графа
    # Текст (text_embedding) використовується як вхідні ознаки (features).
    PROJECTION_QUERY = f"""
    CALL gds.graph.project.cypher(
        '{graph_name}',
        'MATCH (n) WHERE n:User OR n:Page 
         RETURN id(n) AS id, labels(n) AS labels, 
                coalesce(n.text_embedding, [i IN range(1, 384) | 0.0]) AS features',
        'MATCH (u:User)-[v:VISIT]->(p:Page) RETURN id(u) AS source, id(p) AS target',
        {{validateRelationships: false}} 
    )
    """

    # Крок 2: Навчання моделі GraphSAGE (Content-Driven параметри)
    TRAIN_QUERY = f"""
    CALL gds.beta.graphSage.train('{graph_name}', {{
        modelName: '{model_name}',
        featureProperties: ['features'],
        embeddingDimension: {HYBRID_DIM},
        
        aggregator: 'pool',       
        activationFunction: 'relu',
        sampleSizes: [5, 5],      
        epochs: 5,                
        learningRate: 0.01
    }})
    """

    # Крок 3: Стрімінг та запис результатів
    STREAM_QUERY = f"""
    CALL gds.beta.graphSage.stream('{graph_name}', {{
        modelName: '{model_name}'
    }})
    YIELD nodeId, embedding
    WITH gds.util.asNode(nodeId) AS n, embedding
    WHERE n:Page
    RETURN elementId(n) AS elementId, embedding
    """

    WRITE_QUERY = """
    UNWIND $streamResult AS row
    MATCH (p:Page) WHERE elementId(p) = row.elementId
    SET p.hybridEmbedding = row.embedding
    RETURN count(p) AS nodesUpdated
    """

    try:
        print("GDS: Проєктування гібридного графа...")
        client.run_query(PROJECTION_QUERY)
        
        print("GDS: Навчання GraphSAGE (Content-Focused)...")
        client.run_query(TRAIN_QUERY)
        
        print("GDS: Запис гібридних ембедінгів...")
        stream_result = client.run_query(STREAM_QUERY)
        
        if stream_result:
            write_res = client.run_query(WRITE_QUERY, {'streamResult': stream_result})
            count = write_res[0]['nodesUpdated'] if write_res else 0
            return f"Оновлено {count} сторінок гібридними ембедінгами."
        
        return "Немає результатів GraphSAGE для запису."

    except Exception as e:
        traceback.print_exc()
        raise e # Прокидаємо помилку наверх


# ==============================================================================
# 2. АГРЕГАЦІЯ ПРОФІЛЮ (Допоміжні функції)
# ==============================================================================

def validate_vector(vec: Optional[List[float]]) -> Optional[List[float]]:
    if vec is None: return None
    return [float(x) for x in vec]

def aggregate_hybrid_visits(visit_records: List[Dict[str, Any]]) -> Tuple[List[float], float, int]:
    """Агрегує гібридні вектори сторінок у зважену суму."""
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
    sum_w_emb = [0.0] * dim
    total_w = 0.0
    
    for emb, w in zip(embeddings, weights):
        if len(emb) != dim:
            emb = (emb + [0.0] * dim)[:dim]
        
        for i in range(dim):
            sum_w_emb[i] += emb[i] * w
        total_w += w

    return (sum_w_emb, total_w, dim)

def update_user_hybrid_profile_batch(neo4j_client_arg: Any, user_id: str, hours_ago: int = 24) -> str:
    """
    Пакетне оновлення ЄДИНОГО гібридного профілю користувача.
    """
    client = neo4j_client_arg if neo4j_client_arg else neo4j_client
    print(f"Оновлення гібридного профілю для {user_id}...")

    FETCH_Q = """
    MATCH (u:User {id: $user_id})-[v:VISIT]->(p:Page)
    WHERE p.hybridEmbedding IS NOT NULL
      AND v.active_time IS NOT NULL 
      AND any(ts IN v.visitedAt WHERE datetime(ts) >= datetime() - duration({hours: $hours_ago}))
    RETURN p.hybridEmbedding AS emb, 
           (coalesce(toFloat(v.active_time), 0.0) + 0.1 * coalesce(toFloat(v.total_open_time), 0.0)) AS w
    """
    
    try:
        records = client.run_query(FETCH_Q, {'user_id': user_id, 'hours_ago': hours_ago})
        (batch_sum, batch_w, dim) = aggregate_hybrid_visits(records)
        
        if not batch_sum:
            return "Немає нових відвідувань з гібридними ембедінгами."

        STATE_Q = """
        MATCH (u:User {id: $user_id}) 
        RETURN u.sumWeightedHybridEmbedding AS old_sum, u.totalHybridWeight AS old_w
        """
        old_profile = client.run_one(STATE_Q, {'user_id': user_id}) or {}
        
        old_sum = validate_vector(old_profile.get("old_sum")) or [0.0] * dim
        old_w = float(old_profile.get("old_w") or 0.0)

        new_sum = [s_o + s_b for s_o, s_b in zip(old_sum, batch_sum)]
        new_w = old_w + batch_w
        new_emb = [x / new_w for x in new_sum] if new_w > 0 else new_sum

        WRITE_Q = """
        MATCH (u:User {id: $user_id})
        SET u.sumWeightedHybridEmbedding = $sum,
            u.totalHybridWeight = $total_w,
            u.hybridEmbedding = $embedding
        RETURN u.id
        """
        client.run_query(WRITE_Q, {
            'user_id': user_id, 
            'sum': new_sum, 
            'total_w': new_w, 
            'embedding': new_emb
        })
        return "Профіль оновлено."

    except Exception as e:
        traceback.print_exc()
        raise e


# ==============================================================================
# 3. CELERY ТАСКИ
# ==============================================================================

# @app.task
# def run_gds_graphsage(neo4j_client_arg: Any = None) -> str:
#     """Окрема таска для запуску лише GraphSAGE."""
#     client = neo4j_client_arg if neo4j_client_arg else neo4j_client
#     try:
#         return _execute_graphsage_logic(client)
#     except Exception as e:
#         return f"Помилка GraphSAGE: {e}"

# @app.task(bind=True, max_retries=3)
# def task_update_hybrid_profile(self, user_id: str, hours_ago: int = 24):
#     """Окрема таска для оновлення лише юзера."""
#     try:
#         return update_user_hybrid_profile_batch(neo4j_client, user_id, hours_ago)
#     except Exception as exc:
#         raise self.retry(exc=exc, countdown=60)


# ==============================================================================
# 3. ОСНОВНА ТАСКА (ОНОВЛЕНА ДЛЯ ВСІХ КОРИСТУВАЧІВ)
# ==============================================================================

@app.task(bind=True, max_retries=3)
def task_build_graph_and_update_user(self, user_id: str = None, hours_ago: int = 24):
    """
    ПОВНИЙ ПАЙПЛАЙН:
    1. Будує/Оновлює гібридні ембедінги сторінок (GraphSAGE) для ВСЬОГО ГРАФА.
    2. Якщо передано user_id -> оновлює тільки цього користувача.
    3. Якщо user_id=None -> оновлює ВСІХ користувачів у базі.
    """
    try:
        print(f"=== ЗАПУСК ПАЙПЛАЙНУ (User: {user_id if user_id else 'ALL'}) ===")
        
        # Етап 1: GraphSAGE (Глобально)
        print(">> Етап 1: Генерація ембедінгів сторінок...")
        sage_result = _execute_graphsage_logic(neo4j_client)
        print(f">> GraphSAGE завершено: {sage_result}")
        
        # Етап 2: Оновлення профілів
        updated_users_count = 0
        
        if user_id:
            # Оновлюємо конкретного користувача (для тестів)
            print(f">> Етап 2: Оновлення одного користувача {user_id}...")
            res = update_user_hybrid_profile_batch(neo4j_client, user_id, hours_ago)
            print(f"   User {user_id}: {res}")
            updated_users_count = 1
        else:
            # Оновлюємо ВСІХ користувачів (для продакшену/розкладу)
            print(">> Етап 2: Отримання списку всіх користувачів...")
            
            # Знаходимо всіх юзерів
            users_query = "MATCH (u:User) RETURN u.id as id"
            users = neo4j_client.run_query(users_query)
            
            print(f">> Знайдено {len(users)} користувачів. Починаємо оновлення...")
            
            for u in users:
                uid = u['id']
                try:
                    res = update_user_hybrid_profile_batch(neo4j_client, uid, hours_ago)
                    # Можна логувати тільки помилки або успіхи, щоб не забивати консоль
                    # print(f"   User {uid}: {res}") 
                    updated_users_count += 1
                except Exception as e:
                    print(f"!!! Помилка оновлення для user {uid}: {e}")
                    
        return f"SUCCESS. Graph: {sage_result} | Updated Users: {updated_users_count}"
        
    except Exception as exc:
        print(f"!!! Помилка в пайплайні: {exc}")
        raise self.retry(exc=exc, countdown=60)