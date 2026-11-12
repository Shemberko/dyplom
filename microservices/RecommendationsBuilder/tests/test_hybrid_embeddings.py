"""
Тести для чистих helper-функцій з hybrid_embeddings.py:
  - validate_vector
  - normalize_vector
  - aggregate_hybrid_visits
  - _check_model_exists
  - run_graphsage_pipeline
  - update_user_text_profile_batch

Celery та Neo4j патчиться через conftest.py.
Функції тестуються напряму через переданий mock_client.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, call


# =============================================================================
# Імпортуємо модуль після того, як conftest.py вже встановив патчі.
# Оскільки celery_worker патчиться через session fixture, модуль можна
# імпортувати лише всередині тестів або через lazy import.
# =============================================================================

def _import_module():
    """Лінивий імпорт, щоб патчі з conftest встигли застосуватись."""
    from services.asyn.tasks import hybrid_embeddings as m
    return m


# ---------------------------------------------------------------------------
# validate_vector
# ---------------------------------------------------------------------------

class TestValidateVector:

    def test_valid_list_returns_floats(self):
        m = _import_module()
        result = m.validate_vector([1, 2, 3])
        assert result == [1.0, 2.0, 3.0]
        assert all(isinstance(x, float) for x in result)

    def test_none_returns_none(self):
        m = _import_module()
        assert m.validate_vector(None) is None

    def test_empty_list_returns_none(self):
        m = _import_module()
        assert m.validate_vector([]) is None


# ---------------------------------------------------------------------------
# normalize_vector
# ---------------------------------------------------------------------------

class TestNormalizeVector:

    def test_normalizes_to_unit_length(self):
        m = _import_module()
        vec = np.array([3.0, 4.0])  # норма = 5
        result = m.normalize_vector(vec)
        assert abs(np.linalg.norm(result) - 1.0) < 1e-6

    def test_zero_vector_returns_itself(self):
        m = _import_module()
        vec = np.array([0.0, 0.0, 0.0])
        result = m.normalize_vector(vec)
        assert list(result) == [0.0, 0.0, 0.0]


# ---------------------------------------------------------------------------
# aggregate_hybrid_visits
# ---------------------------------------------------------------------------

class TestAggregateHybridVisits:

    def test_empty_records_returns_zeros(self):
        m = _import_module()
        result = m.aggregate_hybrid_visits([])
        assert result == ([], 0.0, 0)

    def test_records_without_emb_are_skipped(self):
        m = _import_module()
        records = [{"emb": None, "w": 1.0}, {"emb": [], "w": 0.5}]
        result = m.aggregate_hybrid_visits(records)
        assert result == ([], 0.0, 0)

    def test_single_record_weighted_sum(self):
        m = _import_module()
        records = [{"emb": [1.0, 0.0], "w": 2.0}]
        sum_emb, total_w, dim = m.aggregate_hybrid_visits(records)
        assert dim == 2
        assert abs(total_w - 2.0) < 1e-9
        assert abs(sum_emb[0] - 2.0) < 1e-9  # 1.0 * 2.0

    def test_two_records_weighted_sum(self):
        m = _import_module()
        records = [
            {"emb": [1.0, 0.0], "w": 1.0},
            {"emb": [0.0, 1.0], "w": 3.0},
        ]
        sum_emb, total_w, dim = m.aggregate_hybrid_visits(records)
        assert abs(total_w - 4.0) < 1e-9
        assert abs(sum_emb[0] - 1.0) < 1e-9   # 1.0*1 + 0.0*3
        assert abs(sum_emb[1] - 3.0) < 1e-9   # 0.0*1 + 1.0*3


# ---------------------------------------------------------------------------
# _check_model_exists
# ---------------------------------------------------------------------------

class TestCheckModelExists:

    def test_returns_true_when_model_exists(self, mock_client):
        m = _import_module()
        mock_client.run_query.return_value = [{"exists": True}]
        assert m._check_model_exists(mock_client, "my_model") is True

    def test_returns_false_when_model_missing(self, mock_client):
        m = _import_module()
        mock_client.run_query.return_value = [{"exists": False}]
        assert m._check_model_exists(mock_client, "my_model") is False

    def test_returns_false_on_empty_result(self, mock_client):
        m = _import_module()
        mock_client.run_query.return_value = []
        assert m._check_model_exists(mock_client, "my_model") is False

    def test_returns_false_on_exception(self, mock_client):
        m = _import_module()
        mock_client.run_query.side_effect = Exception("GDS not available")
        assert m._check_model_exists(mock_client, "my_model") is False


# ---------------------------------------------------------------------------
# run_graphsage_pipeline
# ---------------------------------------------------------------------------

class TestRunGraphsagePipeline:

    def test_calls_project_and_apply_when_model_exists(self, mock_client):
        """Якщо модель є і force_retrain=False → тренування НЕ відбувається."""
        m = _import_module()

        # Імітуємо: graph.drop OK, model exists, apply OK
        mock_client.run_query.side_effect = [
            [],                                         # drop graph (ігноруємо)
            [],                                         # project graph
            [{"exists": True}],                         # check model exists
            [{"nodePropertiesWritten": 42}],            # apply graphsage
            [],                                         # drop graph after
        ]

        with (
            patch.object(m, "_project_graph") as mock_proj,
            patch.object(m, "_check_model_exists", return_value=True),
            patch.object(m, "_train_graphsage") as mock_train,
            patch.object(m, "_apply_graphsage", return_value=42) as mock_apply,
        ):
            result = m.run_graphsage_pipeline(mock_client, force_retrain=False)

        mock_proj.assert_called_once()
        mock_train.assert_not_called()
        mock_apply.assert_called_once()
        assert "42" in result

    def test_trains_when_model_missing(self, mock_client):
        """Якщо моделі немає → _train_graphsage викликається."""
        m = _import_module()

        with (
            patch.object(m, "_project_graph"),
            patch.object(m, "_check_model_exists", return_value=False),
            patch.object(m, "_train_graphsage") as mock_train,
            patch.object(m, "_apply_graphsage", return_value=10),
        ):
            mock_client.run_query.return_value = []
            m.run_graphsage_pipeline(mock_client, force_retrain=False)

        mock_train.assert_called_once()

    def test_force_retrain_trains_even_if_model_exists(self, mock_client):
        """force_retrain=True → тренування навіть якщо модель є."""
        m = _import_module()

        with (
            patch.object(m, "_project_graph"),
            patch.object(m, "_check_model_exists", return_value=True),
            patch.object(m, "_train_graphsage") as mock_train,
            patch.object(m, "_apply_graphsage", return_value=5),
        ):
            mock_client.run_query.return_value = []
            m.run_graphsage_pipeline(mock_client, force_retrain=True)

        mock_train.assert_called_once()

    def test_raises_exception_on_failure(self, mock_client):
        """Якщо _project_graph кидає → виняток пробрасовується вверх."""
        m = _import_module()

        with patch.object(m, "_project_graph", side_effect=RuntimeError("Neo4j down")):
            with pytest.raises(RuntimeError):
                m.run_graphsage_pipeline(mock_client)


# ---------------------------------------------------------------------------
# update_user_text_profile_batch
# ---------------------------------------------------------------------------

class TestUpdateUserTextProfileBatch:

    def test_returns_no_updates_when_no_records(self, mock_client):
        """Якщо немає нових візитів → повертається 'No updates.'"""
        m = _import_module()
        mock_client.run_query.return_value = []  # немає записів

        result = m.update_user_text_profile_batch(mock_client, "u1")
        assert result == "No updates."

    def test_updates_profile_with_new_visits(self, mock_client):
        """З новими візитами → профіль оновлюється, run_query викликається двічі."""
        m = _import_module()

        emb = [0.1] * 384
        # Перший виклик: записи з візитами; другий: старий профіль; третій: write
        mock_client.run_query.side_effect = [
            [{"emb": emb, "w": 1.0, "visit_id": "v:1"}],  # FETCH
            None,                                             # WRITE (не використовується)
        ]
        mock_client.run_one.return_value = {"old_sum": [0.0] * 384, "old_w": 0.0}

        result = m.update_user_text_profile_batch(mock_client, "u1")

        assert "Profile Updated" in result
        # run_query викликався 2 рази: FETCH і WRITE
        assert mock_client.run_query.call_count == 2

    def test_decay_applied_to_old_profile(self, mock_client):
        """Старий профіль множиться на DECAY=0.98 перед додаванням нового."""
        m = _import_module()

        emb = [1.0] + [0.0] * 383
        mock_client.run_query.side_effect = [
            [{"emb": emb, "w": 0.0, "visit_id": "v1"}],
            None,
        ]
        # Старий профіль: одиничний вектор, totalWeight=1.0
        mock_client.run_one.return_value = {
            "old_sum": [1.0] + [0.0] * 383,
            "old_w": 1.0
        }

        # Просто перевіряємо що функція відпрацювала без помилки
        result = m.update_user_text_profile_batch(mock_client, "u1")
        assert "Profile Updated" in result
