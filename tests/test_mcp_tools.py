"""One contract test per MCP tool, called through FastMCP. Each checks the shape and the numbers that matter."""
import asyncio
import socket
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pandas")
pytest.importorskip("chromadb")
uvicorn = pytest.importorskip("uvicorn")

ROOT = Path(__file__).parent.parent
if not (ROOT / "data/rag/chroma").exists():
    pytest.skip("run make data first", allow_module_level=True)

from scout_platform.mcp_server import models, server  # noqa: E402
from sensing.blackboard_service import app as blackboard  # noqa: E402

SKU = "FOODS_3_363"


def call(tool, args, model):
    result = asyncio.run(server.mcp.call_tool(tool, args))
    structured = result[1] if isinstance(result, tuple) else result
    return model.model_validate(structured)


def test_get_sales_history():
    out = call("get_sales_history", {"sku": SKU, "location": "retail_dc", "days": 7}, models.SalesHistory)
    assert len(out.days) == 7 and out.days[-1].date == "2016-05-22"


def test_get_inventory_differs_by_persona():
    plant = call("get_inventory", {"sku": SKU, "location": "plant"}, models.Inventory)
    retail = call("get_inventory", {"sku": SKU, "location": "retail_dc"}, models.Inventory)
    assert plant.days_of_cover < 3.5 < 20 < retail.days_of_cover
    assert plant.avg_daily_demand_90d > retail.avg_daily_demand_90d


def test_lookup_vendor_has_primary_and_alternate():
    out = call("lookup_vendor", {"sku": "FOODS_3_230"}, models.VendorList)
    assert {v.role for v in out.vendors} == {"primary", "alternate"}
    assert any(v.tier == 3 for v in out.vendors)


def test_get_policy_limits_is_persona_specific():
    plant = call("get_policy_limits", {"persona": "plant"}, models.PolicyLimits)
    ids = {r.rule_id for r in plant.rules}
    assert "POL-02" in ids and "POL-01" not in ids


def test_forecast_uses_configured_multiplier():
    out = call(
        "forecast",
        {"sku": SKU, "location": "retail_dc", "horizon_days": 14, "disruption_type": "port_delay", "severity": 3},
        models.Forecast,
    )
    assert out.multiplier == 1.10 and out.delta_pct == pytest.approx(10.0)
    assert out.revised_daily_demand == pytest.approx(out.baseline_daily_demand * 1.10, abs=0.01)


def test_rag_search_filters_to_sku_and_persona():
    out = call("rag_search", {"query": "lead time", "persona": "plant", "sku": SKU, "k": 5}, models.RagResults)
    assert len(out.hits) == 5
    assert "SOP-DISRUPTION-RETAIL-DC" not in {h.doc_id for h in out.hits}


@pytest.mark.parametrize(
    "tool,args",
    [
        ("forecast", {"sku": SKU, "location": "plant", "horizon_days": 14, "disruption_type": "port_delay", "severity": 9}),
        ("get_sales_history", {"sku": "'; DROP TABLE vendors; --", "location": "plant", "days": 7}),
        ("get_inventory", {"sku": SKU, "location": "../../.env"}),
        ("rag_search", {"query": "x", "persona": "admin", "sku": SKU}),
    ],
)
def test_bad_arguments_raise(tool, args):
    with pytest.raises(Exception):
        asyncio.run(server.mcp.call_tool(tool, args))


@pytest.fixture(scope="module")
def live_blackboard(tmp_path_factory):
    blackboard.STORE_DIR = tmp_path_factory.mktemp("blackboard")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    uv = uvicorn.Server(uvicorn.Config(blackboard.app, port=port, log_level="error"))
    thread = threading.Thread(target=uv.run, daemon=True)
    thread.start()
    while not uv.started:
        time.sleep(0.05)
    server.BLACKBOARD_URL = f"http://127.0.0.1:{port}"
    yield
    uv.should_exit = True
    thread.join(5)


def test_blackboard_write_and_read_by_topic_and_cursor(live_blackboard):
    args = {"run_id": "r1", "author": "a", "payload": {"n": 1}, "trust_level": "untrusted", "source_domain": "x.example"}
    call("blackboard_write", {**args, "topic": "signals"}, models.BlackboardEntry)
    call("blackboard_write", {**args, "topic": "other"}, models.BlackboardEntry)
    first = call("blackboard_read", {"run_id": "r1", "topic": "signals"}, models.BlackboardPage)
    assert len(first.entries) == 1 and first.cursor == 2
    later = call("blackboard_read", {"run_id": "r1", "topic": "signals", "cursor": first.cursor}, models.BlackboardPage)
    assert later.entries == []


def test_blackboard_runs_are_isolated(live_blackboard):
    page = call("blackboard_read", {"run_id": "r2", "topic": "signals"}, models.BlackboardPage)
    assert page.entries == []
