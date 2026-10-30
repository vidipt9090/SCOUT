import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts import ALL_MODELS, DisruptionAssessment, GuardrailVerdict, MitigationPlan

FIXTURES = Path(__file__).parent.parent / "contracts" / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda m: m.__name__)
def test_fixture_validates_and_round_trips(model):
    obj = model.model_validate_json((FIXTURES / f"{model.__name__}.json").read_text(encoding="utf-8"))
    assert model.model_validate_json(obj.model_dump_json()) == obj


@pytest.mark.parametrize("severity", [0, 6])
def test_severity_out_of_range_raises(severity):
    with pytest.raises(ValidationError):
        DisruptionAssessment.model_validate({**fixture("DisruptionAssessment"), "severity": severity})


def test_vote_out_of_range_raises():
    with pytest.raises(ValidationError):
        DisruptionAssessment.model_validate({**fixture("DisruptionAssessment"), "severity_votes": [3, 9]})


def test_plan_without_citations_raises():
    with pytest.raises(ValidationError):
        MitigationPlan.model_validate({**fixture("MitigationPlan"), "cited_doc_ids": []})


def test_plan_quantity_is_not_coerced():
    with pytest.raises(ValidationError):
        MitigationPlan.model_validate({**fixture("MitigationPlan"), "quantity": "500"})


def test_payload_is_immutable():
    plan = MitigationPlan.model_validate(fixture("MitigationPlan"))
    with pytest.raises(ValidationError):
        plan.quantity = 1.0


def test_counter_verdict_requires_counter_plan():
    with pytest.raises(ValidationError):
        GuardrailVerdict.model_validate({**fixture("GuardrailVerdict"), "decision": "counter"})
