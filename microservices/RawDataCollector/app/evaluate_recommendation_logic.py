"""
Offline evaluation script for the hybrid recommendation pipeline.

It creates synthetic users, masks 20% of their visits, and compares three
rankers at K=5 and K=10:
- popularity baseline
- content-based text embedding baseline
- hybrid text + GraphSAGE model

The script reuses the project's existing Neo4j wrapper, so it uses the official
Neo4j driver already configured for RawDataCollector.
"""

from __future__ import annotations

import argparse
import math
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from services.neo4j.history_service import HistoryService


PREFERRED_TOPIC_SEEDS = [
    "artificial intelligence",
    "software engineering",
    "computer science theory",
    "hardware & infrastructure",
    "space & aerospace",
    "business & management",
    "economics & finance",
    "marketing & advertising",
    "psychology & sociology",
    "philosophy & ethics",
    "arts & media",
    "education & health",
    "law & politics",
    "earth & physical sciences"
]


@dataclass(frozen=True)
class PageRecord:
    url: str
    title: str
    text_embedding: np.ndarray
    hybrid_embedding: np.ndarray
    categories: Tuple[str, ...]
    visit_count: int


@dataclass(frozen=True)
class CategoryBucket:
    label: str
    urls: Tuple[str, ...]


@dataclass(frozen=True)
class MockUserScenario:
    user_id: str
    categories: Tuple[str, ...]
    train_urls: Tuple[str, ...]
    test_urls: Tuple[str, ...]


def normalize_vector(vector: Sequence[float] | np.ndarray | None) -> np.ndarray | None:
    if vector is None:
        return None
    array = np.asarray(vector, dtype=float)
    if array.size == 0:
        return None
    norm = np.linalg.norm(array)
    if norm == 0:
        return None
    return array / norm


def mean_vector(vectors: Sequence[Sequence[float] | np.ndarray]) -> np.ndarray | None:
    cleaned = [np.asarray(vector, dtype=float) for vector in vectors if vector is not None]
    if not cleaned:
        return None
    return normalize_vector(np.mean(cleaned, axis=0))


def precision_at_k(recommended_urls: Sequence[str], relevant_urls: Iterable[str], k: int) -> float:
    if k <= 0:
        return 0.0
    relevant_set = set(relevant_urls)
    hits = sum(1 for url in recommended_urls[:k] if url in relevant_set)
    return hits / float(k)


def ndcg_at_k(recommended_urls: Sequence[str], relevant_urls: Iterable[str], k: int) -> float:
    if k <= 0:
        return 0.0

    relevant_set = set(relevant_urls)
    gains = [1.0 if url in relevant_set else 0.0 for url in recommended_urls[:k]]
    if not gains:
        return 0.0

    dcg = 0.0
    for index, gain in enumerate(gains, start=1):
        if gain > 0:
            dcg += gain / math.log2(index + 1)

    ideal_hits = min(len(relevant_set), k)
    if ideal_hits == 0:
        return 0.0

    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def _category_jaccard_distance(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = {value.lower() for value in left if value}
    right_set = {value.lower() for value in right if value}
    if not left_set and not right_set:
        return 0.0
    union = left_set | right_set
    if not union:
        return 0.0
    return 1.0 - (len(left_set & right_set) / float(len(union)))


def intra_list_diversity(recommended_urls: Sequence[str], page_lookup: Mapping[str, PageRecord], k: int) -> float:
    selected = [page_lookup[url].categories for url in recommended_urls[:k] if url in page_lookup]
    if len(selected) < 2:
        return 0.0
    distances = [_category_jaccard_distance(left, right) for left, right in combinations(selected, 2)]
    return float(np.mean(distances)) if distances else 0.0


def format_ascii_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    string_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(str(header)) for header in headers]
    for row in string_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def border() -> str:
        return "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def render_row(row: Sequence[str]) -> str:
        cells = [f" {cell.ljust(widths[index])} " for index, cell in enumerate(row)]
        return "|" + "|".join(cells) + "|"

    lines = [border(), render_row(headers), border()]
    lines.extend(render_row(row) for row in string_rows)
    lines.append(border())
    return "\n".join(lines)


class RecommendationEvaluator:
    def __init__(
        self,
        service: HistoryService,
        seed: int = 42,
        user_count: int = 10,
        visits_min: int = 15,
        visits_max: int = 20,
        holdout_ratio: float = 0.2,
        top_ks: Sequence[int] = (5, 10),
    ) -> None:
        self.service = service
        self.seed = seed
        self.random = random.Random(seed)
        self.user_count = user_count
        self.visits_min = visits_min
        self.visits_max = visits_max
        self.holdout_ratio = holdout_ratio
        self.top_ks = tuple(sorted(set(top_ks)))
        self.run_id = uuid.uuid4().hex[:10]
        self.synthetic_prefix = f"eval_mock_{self.run_id}_"

    def run(self) -> None:
        self._cleanup_previous_synthetic_users()

        initial_catalog = self._fetch_page_catalog()
        if not initial_catalog:
            raise RuntimeError("No pages with both embeddings were found in Neo4j.")

        category_buckets = self._build_category_buckets(initial_catalog)
        if not category_buckets:
            raise RuntimeError("No categories with pages were found in Neo4j.")

        scenarios = self._create_mock_users(category_buckets)
        self._mask_holdout_visits(scenarios)

        final_catalog = self._fetch_page_catalog()
        if not final_catalog:
            raise RuntimeError("The final catalog is empty after masking the hold-out set.")

        metrics, diversity_scores = self._evaluate_scenarios(scenarios, final_catalog)
        self._print_report(metrics, diversity_scores)

    def _cleanup_previous_synthetic_users(self) -> None:
        query = """
        MATCH (u:User)
        WHERE coalesce(u.synthetic_evaluation, false) = true
           OR u.id STARTS WITH $prefix
        DETACH DELETE u
        """
        self.service.run_query(query, {"prefix": "eval_mock_"})

    def _fetch_page_catalog(self) -> List[PageRecord]:
        query = """
        MATCH (p:Page)
        WHERE p.text_embedding IS NOT NULL
          AND p.hybridEmbedding IS NOT NULL
        OPTIONAL MATCH (p)-[:IN_CATEGORY]->(c:Category)
        WITH p, collect(DISTINCT c.name) AS categories
        OPTIONAL MATCH (p)<-[v:VISIT]-()
        WITH p, categories, count(DISTINCT v) AS visit_count
        RETURN
            p.url AS url,
            p.title AS title,
            p.text_embedding AS text_embedding,
            p.hybridEmbedding AS hybrid_embedding,
            categories,
            visit_count
        ORDER BY p.url
        """

        rows = self.service.run_query(query)
        catalog: List[PageRecord] = []
        for row in rows:
            text_embedding = normalize_vector(row.get("text_embedding"))
            hybrid_embedding = normalize_vector(row.get("hybrid_embedding"))
            if text_embedding is None or hybrid_embedding is None:
                continue

            categories = tuple(sorted({name.strip() for name in row.get("categories", []) if name and name.strip()}))
            catalog.append(
                PageRecord(
                    url=row.get("url", ""),
                    title=row.get("title", ""),
                    text_embedding=text_embedding,
                    hybrid_embedding=hybrid_embedding,
                    categories=categories,
                    visit_count=int(row.get("visit_count", 0) or 0),
                )
            )
        return catalog

    def _build_category_buckets(self, catalog: Sequence[PageRecord]) -> Dict[str, CategoryBucket]:
        label_map: Dict[str, str] = {}
        urls_map: Dict[str, set[str]] = {}

        for page in catalog:
            for category in page.categories:
                key = category.strip().lower()
                if not key:
                    continue
                label_map.setdefault(key, category.strip())
                urls_map.setdefault(key, set()).add(page.url)

        return {
            key: CategoryBucket(label=label_map[key], urls=tuple(sorted(urls)))
            for key, urls in urls_map.items()
        }

    def _matches_preferred_seed(self, category_name: str) -> bool:
        lower_name = category_name.lower()
        return any(seed in lower_name or lower_name in seed for seed in PREFERRED_TOPIC_SEEDS)

    def _ordered_categories(self, buckets: Mapping[str, CategoryBucket]) -> List[CategoryBucket]:
        preferred = [bucket for bucket in buckets.values() if self._matches_preferred_seed(bucket.label)]
        if preferred:
            return sorted(preferred, key=lambda bucket: len(bucket.urls), reverse=True)
        return sorted(buckets.values(), key=lambda bucket: len(bucket.urls), reverse=True)

    def _create_mock_users(self, category_buckets: Mapping[str, CategoryBucket]) -> List[MockUserScenario]:
        ordered_categories = self._ordered_categories(category_buckets)
        if not ordered_categories:
            raise RuntimeError("Could not derive any usable categories for synthetic users.")

        scenarios: List[MockUserScenario] = []
        for _ in range(self.user_count):
            user_id = f"{self.synthetic_prefix}{uuid.uuid4().hex[:8]}"

            first_bucket = self.random.choice(ordered_categories)
            selected_buckets = [first_bucket]
            if len(ordered_categories) > 1 and self.random.random() < 0.6:
                alternatives = [bucket for bucket in ordered_categories if bucket.label != first_bucket.label]
                if alternatives:
                    selected_buckets.append(self.random.choice(alternatives))

            selected_buckets = sorted({bucket.label: bucket for bucket in selected_buckets}.values(), key=lambda bucket: bucket.label)
            target_visits = self.random.randint(self.visits_min, self.visits_max)
            chosen_urls = self._sample_visit_urls(category_buckets, selected_buckets, target_visits)

            self._create_user_and_visits(user_id, selected_buckets, chosen_urls)

            holdout_count = max(1, int(round(len(chosen_urls) * self.holdout_ratio)))
            holdout_count = min(holdout_count, len(chosen_urls) - 1)
            holdout_urls = tuple(sorted(self.random.sample(chosen_urls, holdout_count)))
            train_urls = tuple(sorted(url for url in chosen_urls if url not in holdout_urls))

            scenarios.append(
                MockUserScenario(
                    user_id=user_id,
                    categories=tuple(bucket.label for bucket in selected_buckets),
                    train_urls=train_urls,
                    test_urls=holdout_urls,
                )
            )

        return scenarios

    def _sample_visit_urls(
        self,
        category_buckets: Mapping[str, CategoryBucket],
        selected_buckets: Sequence[CategoryBucket],
        desired_size: int,
    ) -> List[str]:
        pool: List[str] = []
        for bucket in selected_buckets:
            pool.extend(bucket.urls)

        unique_pool = sorted(set(pool))
        if len(unique_pool) >= desired_size:
            return self.random.sample(unique_pool, desired_size)

        expanded_pool = sorted({url for bucket in category_buckets.values() for url in bucket.urls})
        if len(expanded_pool) >= desired_size:
            return self.random.sample(expanded_pool, desired_size)

        return expanded_pool

    def _create_user_and_visits(
        self,
        user_id: str,
        selected_buckets: Sequence[CategoryBucket],
        urls: Sequence[str],
    ) -> None:
        user_query = """
        MERGE (u:User {id: $user_id})
        ON CREATE SET u.createdAt = datetime()
        SET u.synthetic_evaluation = true,
            u.evaluation_run = $run_id,
            u.assigned_categories = $assigned_categories
        RETURN u.id AS id
        """
        self.service.run_query(
            user_query,
            {
                "user_id": user_id,
                "run_id": self.run_id,
                "assigned_categories": [bucket.label for bucket in selected_buckets],
            },
        )

        visits: List[Dict[str, Any]] = []
        for index, url in enumerate(urls, start=1):
            active_time = round(self.random.uniform(0.8, 15.0), 2)
            total_open_time = round(active_time + self.random.uniform(0.0, 5.0), 2)
            visited_at = (datetime.now(timezone.utc) - timedelta(hours=self.random.randint(1, 24 * 14))).isoformat()
            visits.append(
                {
                    "url": url,
                    "visited_at": [visited_at],
                    "active_time": active_time,
                    "total_open_time": total_open_time,
                    "split": "train",
                    "rank": index,
                }
            )

        visit_query = """
        MATCH (u:User {id: $user_id})
        UNWIND $visits AS visit
        MATCH (p:Page {url: visit.url})
        MERGE (u)-[v:VISIT]->(p)
        SET v.visitedAt = visit.visited_at,
            v.active_time = visit.active_time,
            v.total_open_time = visit.total_open_time,
            v.source = 'synthetic_evaluation',
            v.split = visit.split,
            v.synthetic_rank = visit.rank
        RETURN count(v) AS created
        """
        self.service.run_query(visit_query, {"user_id": user_id, "visits": visits})

    def _mask_holdout_visits(self, scenarios: Sequence[MockUserScenario]) -> None:
        delete_query = """
        MATCH (u:User {id: $user_id})-[v:VISIT]->(p:Page)
        WHERE p.url IN $holdout_urls
        DELETE v
        """
        for scenario in scenarios:
            self.service.run_query(
                delete_query,
                {
                    "user_id": scenario.user_id,
                    "holdout_urls": list(scenario.test_urls),
                },
            )

    def _evaluate_scenarios(
        self,
        scenarios: Sequence[MockUserScenario],
        final_catalog: Sequence[PageRecord],
    ) -> Tuple[Dict[str, Dict[int, Dict[str, List[float]]]], Dict[str, List[float]]]:
        page_lookup = {page.url: page for page in final_catalog}
        candidate_urls = [page.url for page in final_catalog]
        candidate_popularity = np.array([page.visit_count for page in final_catalog], dtype=float)
        candidate_text_matrix = np.vstack([page.text_embedding for page in final_catalog])
        candidate_hybrid_matrix = np.vstack([page.hybrid_embedding for page in final_catalog])

        model_names = ["Popularity", "Content-Based", "Hybrid"]
        metrics: Dict[str, Dict[int, Dict[str, List[float]]]] = {
            model: {k: {"precision": [], "ndcg": []} for k in self.top_ks} for model in model_names
        }
        diversity_scores: Dict[str, List[float]] = {model: [] for model in model_names}

        for scenario in scenarios:
            train_set = set(scenario.train_urls)
            test_set = set(scenario.test_urls)
            candidate_indices = [index for index, url in enumerate(candidate_urls) if url not in train_set]
            if not candidate_indices:
                continue

            train_text_vectors = [page_lookup[url].text_embedding for url in scenario.train_urls if url in page_lookup]
            train_hybrid_vectors = [page_lookup[url].hybrid_embedding for url in scenario.train_urls if url in page_lookup]
            text_profile = mean_vector(train_text_vectors)
            hybrid_profile = mean_vector(train_hybrid_vectors)

            rankings = {
                "Popularity": self._rank_by_popularity(candidate_urls, candidate_popularity, candidate_indices),
                "Content-Based": self._rank_by_text_similarity(candidate_urls, candidate_text_matrix, candidate_indices, text_profile),
                "Hybrid": self._rank_by_hybrid_similarity(
                    candidate_urls,
                    candidate_text_matrix,
                    candidate_hybrid_matrix,
                    candidate_indices,
                    text_profile,
                    hybrid_profile,
                    weight_text=0.5,
                    weight_hybrid=0.5,
                ),
            }

            for model_name, ranking in rankings.items():
                ranked_urls = [url for url, _ in ranking]
                for k in self.top_ks:
                    metrics[model_name][k]["precision"].append(precision_at_k(ranked_urls, test_set, k))
                    metrics[model_name][k]["ndcg"].append(ndcg_at_k(ranked_urls, test_set, k))
                diversity_scores[model_name].append(intra_list_diversity(ranked_urls, page_lookup, max(self.top_ks)))

        return metrics, diversity_scores

    def _rank_by_popularity(
        self,
        candidate_urls: Sequence[str],
        popularity_scores: np.ndarray,
        candidate_indices: Sequence[int],
    ) -> List[Tuple[str, float]]:
        scored = [(candidate_urls[index], float(popularity_scores[index])) for index in candidate_indices]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored

    def _rank_by_text_similarity(
        self,
        candidate_urls: Sequence[str],
        candidate_matrix: np.ndarray,
        candidate_indices: Sequence[int],
        profile: np.ndarray | None,
    ) -> List[Tuple[str, float]]:
        if profile is None:
            return self._rank_by_popularity(candidate_urls, np.zeros(len(candidate_urls), dtype=float), candidate_indices)

        scores = cosine_similarity(candidate_matrix[candidate_indices], profile.reshape(1, -1)).ravel()
        scored = [(candidate_urls[index], float(score)) for index, score in zip(candidate_indices, scores)]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored

    def _rank_by_hybrid_similarity(
        self,
        candidate_urls: Sequence[str],
        candidate_text_matrix: np.ndarray,
        candidate_hybrid_matrix: np.ndarray,
        candidate_indices: Sequence[int],
        text_profile: np.ndarray | None,
        hybrid_profile: np.ndarray | None,
        weight_text: float = 0.5,
        weight_hybrid: float = 0.5,
    ) -> List[Tuple[str, float]]:
        if text_profile is None or hybrid_profile is None:
            return self._rank_by_text_similarity(candidate_urls, candidate_text_matrix, candidate_indices, text_profile)

        text_scores = cosine_similarity(candidate_text_matrix[candidate_indices], text_profile.reshape(1, -1)).ravel()
        hybrid_scores = cosine_similarity(candidate_hybrid_matrix[candidate_indices], hybrid_profile.reshape(1, -1)).ravel()
        scores = (weight_text * text_scores) + (weight_hybrid * hybrid_scores)
        scored = [(candidate_urls[index], float(score)) for index, score in zip(candidate_indices, scores)]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored

    def _print_report(
        self,
        metrics: Mapping[str, Dict[int, Dict[str, List[float]]]],
        diversity_scores: Mapping[str, List[float]],
    ) -> None:
        model_names = ["Popularity", "Content-Based", "Hybrid"]
        rows: List[List[Any]] = []

        for model_name in model_names:
            row = [model_name]
            for metric_name in ("precision", "ndcg"):
                for k in self.top_ks:
                    values = metrics[model_name][k][metric_name]
                    row.append(f"{float(np.mean(values)):.4f}" if values else "0.0000")
            rows.append(row)

        print()
        print("Evaluation summary")
        print(format_ascii_table(["Model", "Precision@5", "Precision@10", "NDCG@5", "NDCG@10"], rows))

        diversity_rows = []
        for model_name in model_names:
            values = diversity_scores.get(model_name, [])
            diversity_rows.append([model_name, f"{float(np.mean(values)):.4f}" if values else "0.0000"])

        print()
        print("Intra-list diversity at K=10 (lower means tighter topical focus)")
        print(format_ascii_table(["Model", "ILD@10"], diversity_rows))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the recommendation logic on synthetic users.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed used for reproducible sampling.")
    parser.add_argument("--users", type=int, default=10, help="Number of synthetic users to generate.")
    parser.add_argument("--visits-min", type=int, default=15, help="Minimum number of visits per synthetic user.")
    parser.add_argument("--visits-max", type=int, default=20, help="Maximum number of visits per synthetic user.")
    parser.add_argument("--holdout-ratio", type=float, default=0.2, help="Fraction of visits to hide as the test set.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = HistoryService()
    try:
        evaluator = RecommendationEvaluator(
            service=service,
            seed=args.seed,
            user_count=args.users,
            visits_min=args.visits_min,
            visits_max=args.visits_max,
            holdout_ratio=args.holdout_ratio,
        )
        evaluator.run()
    finally:
        service.close()


if __name__ == "__main__":
    main()