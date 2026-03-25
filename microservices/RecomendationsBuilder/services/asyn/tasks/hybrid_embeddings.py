import numpy as np
import traceback
from typing import List, Any, Dict, Tuple
from services.asyn.celery_worker import app
from services.neo4j.query_runner import query_runner as neo4j_client


HOURS_AGO = 1
HYBRID_DIM = 128
EMBEDDING_SIZE = 384
MODEL_NAME = "production_graphsage_model"
GRAPH_NAME = "temp_projection_graph"

def _check_model_exists(client: Any, model_name: str) -> bool:
    """Перевіряє, чи існує навчена модель у пам'яті GDS."""
    try:
        res = client.run_query(f"CALL gds.model.exists('{model_name}') YIELD exists RETURN exists")
        return res[0]['exists'] if res else False
    except Exception:
        return False

# TODO maybe add "HAS_TAG" also
def _project_graph(client: Any):
    """Створює проєкцію графа в пам'яті. Використовується і для Train, і для Predict."""
    try: client.run_query(f"CALL gds.graph.drop('{GRAPH_NAME}', false)")
    except: pass

    PROJECTION_QUERY = f"""
        CALL gds.graph.project.cypher(
            '{GRAPH_NAME}',
            'MATCH (n) WHERE n:User OR n:Page OR n:Category
             RETURN id(n) AS id, labels(n) AS labels, 
                    coalesce(n.text_embedding, [i IN range(1, {EMBEDDING_SIZE}) | 0.0]) AS features',
            'MATCH (s)-[r]-(t) 
             WHERE type(r) IN ["VISIT", "IN_CATEGORY"]
             RETURN id(s) AS source, id(t) AS target, 
                    CASE type(r)
                        WHEN "VISIT" THEN log10(coalesce(r.active_time, 1.0) + 9.0)
                        ELSE 1.0
                    END AS weight',
            {{validateRelationships: false}} 
        )
    """
    print(f"GDS: Проєктування графа '{GRAPH_NAME}' (Undirected через Cypher)...")
    client.run_query(PROJECTION_QUERY)

def _train_graphsage(client: Any):
    """
    ПОВНЕ ПЕРЕНАВЧАННЯ з адаптивними гіперпараметрами.
    """
    print("GDS: Аналіз розміру графа для вибору параметрів...")
    
    stats_query = f"CALL gds.graph.list('{GRAPH_NAME}') YIELD nodeCount, relationshipCount RETURN nodeCount, relationshipCount"
    res = client.run_query(stats_query)
    
    node_count = res[0]['nodeCount'] if res else 0
    rel_count = res[0]['relationshipCount'] if res else 0
    print(f"GDS: Розмір графа: {node_count} вузлів, {rel_count} зв'язків.")

    if node_count < 1000:
        epochs = 3
        sample_sizes = "[5, 2]"
        aggregator = "pool"
    elif node_count < 5000:
        epochs = 10
        sample_sizes = "[10, 5]"
        aggregator = "pool"
    else:
        epochs = 20
        sample_sizes = "[15, 10]"
        aggregator = "pool"

    print(f"GDS: Обрано параметри -> epochs: {epochs}, sampleSizes: {sample_sizes}, aggregator: {aggregator}")

    try: 
        client.run_query(f"CALL gds.beta.model.drop('{MODEL_NAME}', false)")
    except: 
        pass

    TRAIN_QUERY = f"""
    CALL gds.beta.graphSage.train('{GRAPH_NAME}', {{
        modelName: '{MODEL_NAME}',
        featureProperties: ['features'],
        relationshipWeightProperty: 'weight',
        negativeSampleWeight: 5,
        embeddingDimension: {HYBRID_DIM},
        aggregator: '{aggregator}',       
        activationFunction: 'relu',
        sampleSizes: {sample_sizes},
        epochs: {epochs},              
        learningRate: 0.001
    }})
    """
    print("GDS: Почнемо тренування моделі...")
    client.run_query(TRAIN_QUERY)
    print("GDS: Модель успішно навчена.")


def _apply_graphsage(client: Any) -> int:
    """
    ІНКРЕМЕНТАЛЬНЕ ОНОВЛЕННЯ.
    Використовує ВЖЕ НАВЧЕНУ модель, щоб згенерувати вектори для нових сторінок.
    """
    print("GDS: Генерація векторів (Inference)...")
    
    WRITE_QUERY = f"""
        CALL gds.beta.graphSage.write('{GRAPH_NAME}', {{
            modelName: '{MODEL_NAME}',
            writeProperty: 'hybridEmbedding'
        }})
        YIELD nodePropertiesWritten
    """
    res = client.run_query(WRITE_QUERY)
    count = res[0]['nodePropertiesWritten'] if res else 0
    return count

def run_graphsage_pipeline(client: Any, force_retrain: bool = False) -> str:
    """
    Розумний пайплайн:
    1. Проєктує граф.
    2. Якщо моделі немає або force_retrain=True -> Тренує.
    3. Якщо модель є -> Просто застосовує її (це в 100 разів швидше).
    """
    try:
        _project_graph(client)
        
        model_exists = _check_model_exists(client, MODEL_NAME)
        
        if force_retrain or not model_exists:
            _train_graphsage(client)
            action = "TRAINED & APPLIED"
        else:
            action = "APPLIED ONLY (Fast Mode)"
            
        count = _apply_graphsage(client)
        
        client.run_query(f"CALL gds.graph.drop('{GRAPH_NAME}', false)")
        
        return f"{action}: Оновлено {count} вузлів."
    except Exception as e:
        traceback.print_exc()
        raise e


# FUTURE OPTIMIZATION POSSIBILITIES
# # Замість MATCH (u:User) RETURN u.id ...
# # Беремо ТІЛЬКИ тих, хто щось читав за час від останнього оновлення
# query = """
# MATCH (u:User)-[v:VISIT]->(p:Page)
# WHERE datetime(v.visitedAt[-1]) >= datetime() - duration('PT24H')
# RETURN DISTINCT u.id AS id
# """
# active_users = neo4j_client.run_query(query)
# for u in active_users:
#     update_user_text_profile_batch(neo4j_client, u['id'])
def update_user_text_profile_batch(neo4j_client_arg: Any, user_id: str, hours_ago: int = HOURS_AGO) -> str:
    """
    Оновлює профіль користувача.
    
    ПОКРАЩЕННЯ:
    1. Reward Signal: Якщо це був перехід з рекомендації, множимо вагу на 2.0.
    2. Text Focus: Базова вага залежить від active_time.
    3. Tracking: Ставить мітку `tracked = true` на візити, щоб потім їх можна було відняти при видаленні.
    """
    client = neo4j_client_arg if neo4j_client_arg else neo4j_client

    FETCH_Q = """
    MATCH (u:User {id: $user_id})-[v:VISIT]->(p:Page)
    WHERE p.text_embedding IS NOT NULL
      AND v.visitedAt IS NOT NULL
    WITH u, p, v, 
         datetime(v.visitedAt[-1]) AS last_visit_time,
         coalesce(v.active_time, 0.5) AS reading_time
    
    // Фільтруємо за часом і беремо ТІЛЬКИ ті, що ще НЕ враховані
    WHERE last_visit_time >= datetime() - duration({hours: $hours_ago})
      AND coalesce(v.tracked, false) = false
    
    WITH p.text_embedding AS emb,
         (reading_time * exp(-0.05 * duration.inDays(last_visit_time, datetime()).days) *
          CASE WHEN v.source = 'recommendation' THEN 2.0 ELSE 1.0 END
         ) AS w,
         elementId(v) AS visit_id
    
    RETURN emb, w, visit_id
    """
    
    try:
        records = client.run_query(FETCH_Q, {'user_id': user_id, 'hours_ago': hours_ago})
        
        visit_ids = [r["visit_id"] for r in records if r.get("visit_id")]
        
        (batch_sum, batch_w, dim) = aggregate_hybrid_visits(records)
        
        if not batch_sum: return "No updates."

        STATE_Q = """MATCH (u:User {id: $user_id}) 
                     RETURN u.sumWeightedTextEmbedding AS old_sum, u.totalWeight AS old_w"""
        old_profile = client.run_one(STATE_Q, {'user_id': user_id}) or {}
        
        old_sum = validate_vector(old_profile.get("old_sum")) or [0.0] * dim
        old_w = float(old_profile.get("old_w") or 0.0)

        DECAY = 0.98
        
        new_sum = [(s_o * DECAY) + s_b for s_o, s_b in zip(old_sum, batch_sum)]
        new_w = (old_w * DECAY) + batch_w

        v = np.array(new_sum)
        norm = np.linalg.norm(v)

        new_emb = (v / norm).tolist() if norm > 0 else [0.0] * dim

        WRITE_Q = """
        MATCH (u:User {id: $user_id})
        SET u.sumWeightedTextEmbedding = $sum,
            u.totalWeight = $total_w,
            u.text_embedding = $embedding,
            u.profileUpdatedAt = datetime()
        WITH u
        
        // Знаходимо щойно оброблені зв'язки та позначаємо їх як враховані
        UNWIND $visit_ids AS vid
        MATCH (u)-[v:VISIT]->() WHERE elementId(v) = vid
        SET v.tracked = true
        """
        
        client.run_query(WRITE_Q, {
            'user_id': user_id, 
            'sum': new_sum, 
            'total_w': new_w, 
            'embedding': new_emb,
            'visit_ids': visit_ids
        })
        
        return f"Profile Updated. Tracked {len(visit_ids)} new visits."

    except Exception as e:
        traceback.print_exc()
        raise e

def validate_vector(vec): return [float(x) for x in vec] if vec else None

def normalize_vector(vec):
    norm = np.linalg.norm(vec)
    if norm == 0: 
        return vec
    return (vec / norm).tolist()

def aggregate_hybrid_visits(records):
    embeddings = []; weights = []
    for r in records:
        if r.get("emb"):
            embeddings.append([float(x) for x in r.get("emb")])
            weights.append(float(r.get("w") or 0.0))
    if not embeddings: return ([], 0.0, 0)
    dim = len(embeddings[0])
    sum_emb = [0.0]*dim; total_w=0.0
    for emb, w in zip(embeddings, weights):
        for i in range(dim): sum_emb[i] += emb[i]*w
        total_w += w
    return (sum_emb, total_w, dim)



@app.task(bind=True, max_retries=3)
def task_build_graph_and_update_user(self, user_id: str = None, force_retrain: bool = True):
    """
    Розумний пайплайн (ВИПРАВЛЕНИЙ ПОРЯДОК):
    1. Оновлюємо текстові центроїди користувачів (щоб GraphSAGE мав актуальні базові фічі).
    2. Запускаємо GraphSAGE (який використає ці фічі для побудови графа).
    """
    try:
        print(">> Крок 1: Оновлення текстових векторів користувачів...")
        if user_id:
            update_user_text_profile_batch(neo4j_client, user_id)
        else:
            query = """
            MATCH (u:User)-[v:VISIT]->(p:Page)
            WHERE datetime(v.visitedAt[-1]) >= datetime() - duration('PT1H')
            RETURN DISTINCT u.id AS id
            """
            active_users = neo4j_client.run_query(query)
            if active_users:
                print(f">> Знайдено {len(active_users)} активних користувачів.")
                for u in active_users:
                    update_user_text_profile_batch(neo4j_client, u['id'], hours_ago=1)
            else:
                print(">> Активних користувачів за останню годину немає.")

        print(">> Крок 2: Запуск GraphSAGE пайплайну...")
        sage_msg = run_graphsage_pipeline(neo4j_client, force_retrain=force_retrain)
        print(f">> GraphSAGE: {sage_msg}")
        
        return "Pipeline Done"
    except Exception as exc:
        traceback.print_exc()
        raise self.retry(exc=exc, countdown=60)