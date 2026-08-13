"""
Hyperparameter tuning and multi-seed ablation support.

Deliberately built as a thin wrapper around TrainingService rather than a
separate training path — this guarantees tuning/ablation runs go through
the exact same pipeline (same cleaning, same OpenMax fitting, same metric
computation) as a single manual run, so results are directly comparable.

Two capabilities:
  - grid_search(): tries a small hyperparameter grid for ONE architecture,
    keeps every result, reports the best by a chosen metric.
  - multi_seed_ablation(): trains the SAME architecture + hyperparameters
    across N seeds, so you can report mean +/- std instead of a single
    run's number — the statistical rigor a capstone eval needs.
"""
import itertools
import statistics
import uuid
from dataclasses import dataclass

from app.models.ml_model import ModelArchitecture
from app.schemas.ml_model import TrainingRequest
from app.services.training_service import TrainingService


@dataclass
class TuningResult:
    hyperparameters: dict
    metrics: dict
    run_id: uuid.UUID


@dataclass
class AblationSummary:
    architecture: str
    seeds: list[int]
    per_seed_metrics: list[dict]
    mean_metrics: dict
    std_metrics: dict


class HyperparameterTuningService:
    def __init__(self, training_service: TrainingService):
        self._training_service = training_service

    async def grid_search(
        self,
        dataset_id: uuid.UUID,
        architecture: ModelArchitecture,
        triggered_by: uuid.UUID,
        learning_rates: list[float] = (1e-3, 1e-4),
        batch_sizes: list[int] = (64, 128),
        epochs: int = 10,
        rank_by: str = "unknown_attack_recall",
    ) -> list[TuningResult]:
        """
        Runs every combination in the grid SEQUENTIALLY (not parallel — a
        capstone-scale deployment doesn't need concurrent GPU contention,
        and sequential keeps memory usage predictable). Returns every
        result so the caller/frontend can render a full leaderboard, not
        just the winner.
        """
        results: list[TuningResult] = []

        for lr, batch_size in itertools.product(learning_rates, batch_sizes):
            request = TrainingRequest(
                dataset_id=dataset_id, architecture=architecture,
                epochs=epochs, batch_size=batch_size, learning_rate=lr,
            )
            run = await self._training_service.queue_training_run(request, triggered_by)
            await self._training_service.execute_training_run(run.id)

            models = await self._training_service.list_models_for_dataset(dataset_id)
            matching = [m for m in models if m.training_run_id == run.id]
            if not matching:
                continue  # run failed; skip from leaderboard rather than crash the whole search
            model = matching[0]

            results.append(TuningResult(
                hyperparameters={"learning_rate": lr, "batch_size": batch_size, "epochs": epochs},
                metrics=_extract_metric_dict(model),
                run_id=run.id,
            ))

        results.sort(key=lambda r: r.metrics.get(rank_by) or 0, reverse=True)
        return results

    async def multi_seed_ablation(
        self,
        dataset_id: uuid.UUID,
        architecture: ModelArchitecture,
        triggered_by: uuid.UUID,
        seeds: list[int] = (1, 2, 3, 4, 5),
        epochs: int = 20,
        batch_size: int = 128,
        learning_rate: float = 1e-3,
    ) -> AblationSummary:
        """
        The statistical-rigor piece: a single run's "0.72 unknown recall"
        is one sample from a noisy process (weight init, batch order,
        train/val split). Report mean +/- std across seeds instead.
        """
        per_seed_metrics = []

        for seed in seeds:
            request = TrainingRequest(
                dataset_id=dataset_id, architecture=architecture,
                epochs=epochs, batch_size=batch_size, learning_rate=learning_rate, seed=seed,
            )
            run = await self._training_service.queue_training_run(request, triggered_by)
            await self._training_service.execute_training_run(run.id)

            models = await self._training_service.list_models_for_dataset(dataset_id)
            matching = [m for m in models if m.training_run_id == run.id]
            if matching:
                per_seed_metrics.append(_extract_metric_dict(matching[0]))

        mean_metrics = _mean_of_dicts(per_seed_metrics)
        std_metrics = _std_of_dicts(per_seed_metrics)

        return AblationSummary(
            architecture=architecture.value,
            seeds=list(seeds),
            per_seed_metrics=per_seed_metrics,
            mean_metrics=mean_metrics,
            std_metrics=std_metrics,
        )


METRIC_FIELDS = [
    "accuracy", "precision", "recall", "f1", "mcc", "roc_auc",
    "false_positive_rate", "unknown_attack_recall",
    "training_time_seconds", "inference_time_ms_per_sample",
]


def _extract_metric_dict(model) -> dict:
    return {field: getattr(model, field) for field in METRIC_FIELDS}


def _mean_of_dicts(dicts: list[dict]) -> dict:
    result = {}
    for field in METRIC_FIELDS:
        values = [d[field] for d in dicts if d.get(field) is not None]
        result[field] = statistics.mean(values) if values else None
    return result


def _std_of_dicts(dicts: list[dict]) -> dict:
    result = {}
    for field in METRIC_FIELDS:
        values = [d[field] for d in dicts if d.get(field) is not None]
        result[field] = statistics.stdev(values) if len(values) > 1 else 0.0 if values else None
    return result
