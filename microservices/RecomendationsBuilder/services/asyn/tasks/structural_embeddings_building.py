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



@app.task
def run_gds_node2vec(neo4j_client: Any) -> str:
    """
    Celery Beat task: створює проєкцію і виконує gds.node2vec.
    Використовує 2-кроковий підхід (stream + write) та виправлені параметри.
    """
    graph_name = "userPageGraph_Node2Vec" # Використовуємо інше ім'я
    
    try:
        neo4j_client.run_query(f"CALL gds.graph.drop('{graph_name}')")
        print(f"Info: Attempted to drop graph '{graph_name}' (if exists).")
    except Exception as e:
        if "GraphNotFoundException" in str(e):
            print(f"Info: Graph '{graph_name}' did not exist. Drop ignored.")
        else:
            print(f"Warning: Error during graph drop (ignoring): {e}")
        pass 
    
    # Крок 1: Створити проєкцію (використовуємо id() для сумісності з GDS 2.23.0)
    PROJECTION_QUERY = f"""
    CALL gds.graph.project.cypher(
        '{graph_name}',
        'MATCH (n) WHERE n:User OR n:Page RETURN id(n) AS id, labels(n) AS labels',
        'MATCH (u:User)-[v:VISIT]->(p:Page) RETURN id(u) AS source, id(p) AS target, type(v) AS type',
        {{validateRelationships: false}} 
    )
    """

    # Крок 2: Запустити node2vec.stream
    # [ВИПРАВЛЕНО] 'p' та 'q' замінено на повні імена
    STREAM_QUERY = f"""
    CALL gds.node2vec.stream('{graph_name}', {{
        embeddingDimension: 384,
        iterations: 10,
        walkLength: 40,
        returnFactor: 1.0,
        inOutFactor: 1.0
    }})
    YIELD nodeId, embedding
    
    WITH gds.util.asNode(nodeId) AS n, embedding
    WHERE n:Page
    RETURN elementId(n) AS elementId, embedding
    """
    
    # Крок 3: Записати результати у нову властивість
    # (Використовуємо SET, а не gds.util.writeNodeProperty)
    WRITE_QUERY = f"""
    UNWIND $streamResult AS row
    MATCH (p:Page) WHERE elementId(p) = row.elementId
    SET p.structuralEmbedding = row.embedding  // <-- Записуємо в іншу властивість
    RETURN count(p) AS nodesUpdated
    """

    try:
        print(f"GDS (Node2Vec): Projecting graph '{graph_name}'...")
        neo4j_client.run_query(PROJECTION_QUERY)
        
        print(f"GDS (Node2Vec): Running Node2Vec stream on '{graph_name}'...")
        stream_result = neo4j_client.run_query(STREAM_QUERY)
        
        write_result = [{'nodesUpdated': 0}]
        if stream_result:
            print(f"GDS (Node2Vec): Stream complete. Writing {len(stream_result)} embeddings...")
            write_result = neo4j_client.run_query(WRITE_QUERY, {'streamResult': stream_result})
            print(f"GDS (Node2Vec): Write complete. Updated nodes: {write_result}")
        else:
            print("GDS (Node2Vec): Stream returned no results.")

    except Exception as e:
        print(f"Error during GDS Node2Vec execution: {e}")
        traceback.print_exc()
        return f"Error: {e}"
    
    nodes_updated = write_result[0].get('nodesUpdated', 0) if write_result else 0
    return f"GDS Node2Vec complete. {nodes_updated} embeddings written."

