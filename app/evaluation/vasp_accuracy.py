from typing import List, Dict, Any
from pydantic import BaseModel, Field


class GroundTruthTestCase(BaseModel):
    case_id: str
    target_wallet: str
    true_vasp_name: str
    true_vasp_address: str
    true_paths: List[List[str]] = Field(default_factory=list)
    has_high_velocity: bool = True


class VASPAccuracyMetrics(BaseModel):
    total_eval_cases: int
    top_1_accuracy: float = Field(..., ge=0.0, le=1.0)
    top_3_accuracy: float = Field(..., ge=0.0, le=1.0)
    path_reconstruction_success_rate: float = Field(..., ge=0.0, le=1.0)
    false_attribution_rate: float = Field(..., ge=0.0, le=1.0)


class VASPAccuracyEvaluator:
    """Evaluates VASP attribution top-1/top-3 accuracy and path reconstruction success against ground truth."""

    def evaluate_vasp_attribution(
        self,
        ground_truth_cases: List[GroundTruthTestCase],
        predictions: List[Dict[str, Any]],
    ) -> VASPAccuracyMetrics:
        if not ground_truth_cases:
            return VASPAccuracyMetrics(
                total_eval_cases=0,
                top_1_accuracy=0.0,
                top_3_accuracy=0.0,
                path_reconstruction_success_rate=0.0,
                false_attribution_rate=0.0,
            )

        top_1_correct = 0
        top_3_correct = 0
        paths_reconstructed = 0
        false_attributions = 0
        total = len(ground_truth_cases)

        pred_map = {p["case_id"]: p for p in predictions}

        for gt in ground_truth_cases:
            pred = pred_map.get(gt.case_id)
            if not pred:
                continue

            candidates = pred.get("candidate_vasps", [])
            candidate_names = [c.get("vasp_name") for c in candidates]

            if candidate_names:
                if candidate_names[0] == gt.true_vasp_name:
                    top_1_correct += 1
                if gt.true_vasp_name in candidate_names[:3]:
                    top_3_correct += 1
                if candidate_names[0] != gt.true_vasp_name and gt.true_vasp_name != "NONE":
                    false_attributions += 1
            else:
                if gt.true_vasp_name != "NONE":
                    false_attributions += 1

            found_paths = pred.get("discovered_paths", [])
            if found_paths and len(found_paths) >= len(gt.true_paths):
                paths_reconstructed += 1

        return VASPAccuracyMetrics(
            total_eval_cases=total,
            top_1_accuracy=round(top_1_correct / total, 4),
            top_3_accuracy=round(top_3_correct / total, 4),
            path_reconstruction_success_rate=round(paths_reconstructed / total, 4),
            false_attribution_rate=round(false_attributions / total, 4),
        )
