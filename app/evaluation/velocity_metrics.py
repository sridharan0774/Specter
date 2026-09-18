from typing import List, Dict, Any
from pydantic import BaseModel, Field


class VelocityEvaluationMetrics(BaseModel):
    total_eval_cases: int
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)


class VelocityEvaluator:
    """Evaluates high-velocity movement alert precision, recall, and F1 score against ground truth benchmarks."""

    def evaluate_velocity_alerts(
        self,
        ground_truth_cases: List[Any],
        predictions: List[Dict[str, Any]],
    ) -> VelocityEvaluationMetrics:
        if not ground_truth_cases:
            return VelocityEvaluationMetrics(
                total_eval_cases=0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
            )

        true_positives = 0
        false_positives = 0
        false_negatives = 0
        pred_map = {p["case_id"]: p for p in predictions}

        for gt in ground_truth_cases:
            pred = pred_map.get(gt.case_id, {})
            predicted_flag = pred.get("has_high_velocity", False)
            actual_flag = getattr(gt, "has_high_velocity", True)

            if predicted_flag and actual_flag:
                true_positives += 1
            elif predicted_flag and not actual_flag:
                false_positives += 1
            elif not predicted_flag and actual_flag:
                false_negatives += 1

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 1.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 1.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return VelocityEvaluationMetrics(
            total_eval_cases=len(ground_truth_cases),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
        )
