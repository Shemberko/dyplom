import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

print(f"NEO4J_URI: {NEO4J_URI}")
print(f"NEO4J_USERNAME: {NEO4J_USERNAME}")
print(f"NEO4J_PASSWORD: {NEO4J_PASSWORD}")

from neo4j import GraphDatabase

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def get_driver():
    return driver
