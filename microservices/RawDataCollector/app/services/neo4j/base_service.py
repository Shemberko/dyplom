import os
from typing import Dict, Any, Optional
from neo4j import GraphDatabase, Driver

class BaseService:

    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        uri = uri or os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        user = user or os.getenv("NEO4J_USER", "neo4j")
        password = password or os.getenv("NEO4J_PASSWORD", "password")
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def create_or_update_node(self, label: str, key_name: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a node with given label and properties or update existing node matched by key_name.
        - label: node label (e.g. "Article")
        - key_name: unique property name used for MERGE (e.g. "id" or "url")
        - properties: dict of properties to set (must include key_name)
        Returns node properties as dict.
        """
        if key_name not in properties:
            raise ValueError(f"properties must include the key '{key_name}'")

        cypher = f"""
        MERGE (n:{label} {{{key_name}: $key_val}})
        SET n += $props
        RETURN n
        """
        key_val = properties[key_name]

        with self._driver.session() as session:
            record = session.execute_write(lambda tx: tx.run(cypher, key_val=key_val, props=properties).single())
        node = record["n"]
        return dict(node)

    def get_node(self, label: str, key_name: str, key_val: Any) -> Optional[Dict[str, Any]]:
        """
        Fetch node by label and key property value. Returns dict or None.
        """
        cypher = f"MATCH (n:{label} {{{key_name}: $key_val}}) RETURN n"
        with self._driver.session() as session:
            rec = session.execute_read(lambda tx: tx.run(cypher, key_val=key_val).single())
        if not rec:
            return None
        return dict(rec["n"])

    def create_relationship(self,
                            start_label: str, start_key: str, start_val: Any,
                            end_label: str, end_key: str, end_val: Any,
                            rel_type: str,
                            rel_properties: Optional[Dict[str, Any]] = None,
                            additive_metrics: Optional[list] = None) -> Optional[Dict[str, Any]]:
        
        if rel_properties is None:
            rel_properties = {}
        if additive_metrics is None:
            additive_metrics = []

        static_props = {k: v for k, v in rel_properties.items() if k not in additive_metrics}
        additive_props = {k: v for k, v in rel_properties.items() if k in additive_metrics}

        cypher = f"""
        MATCH (a:{start_label} {{{start_key}: $start_val}})
        MATCH (b:{end_label} {{{end_key}: $end_val}})
        MERGE (a)-[r:{rel_type}]->(b)
        
        // 1. Оновлюємо тільки статичні поля (вони безпечно перезаписуються)
        SET r += $static_props
        
        // 2. Додаємо адитивні метрики
        // Ми проходимось по ключах переданих адитивних властивостей
        FOREACH (k IN keys($additive_props) | 
            SET r[k] = coalesce(r[k], 0) + $additive_props[k]
        )
        
        RETURN r
        """

        with self._driver.session() as session:
            record = session.execute_write(
                lambda tx: tx.run(
                    cypher,
                    start_val=start_val,
                    end_val=end_val,
                    static_props=static_props,
                    additive_props=additive_props
                ).single()
            )

        if not record:
            return None
        return dict(record["r"])