"""Generate RAG documents as clause-level chunks. Text states procedure only and holds no scenario labels."""
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).parents[2]

TYPE_NAMES = {"port_delay": "a port delay", "strike": "a labour strike", "weather": "a weather disruption"}
ACTION_TEXT = {
    "reorder": "place a reorder with the primary vendor at standard lead time",
    "reorder_expedited": "place an expedited reorder with the primary vendor",
    "switch_supplier": "switch to an alternate vendor with an approved contract whose lead time is shorter than the disruption horizon",
    "stock_transfer": "request a stock transfer from a peer DC with slack",
    "monitor": "take no purchasing action and monitor the situation",
}
SEVERITY_TEXT = {
    2: "severity 1 or 2 (local or single route affected)",
    3: "severity 3 (several routes or a regional hub affected)",
    4: "severity 4 (major hub or corridor closed)",
}
PERSONA_NAMES = {"plant": "Plant", "retail_dc": "Retail DC"}


def chunk(doc_id, n, doc_class, text, sku="all", vendor_id="all", persona_scope="all"):
    return {
        "chunk_id": f"{doc_id}#c{n}",
        "doc_id": doc_id,
        "doc_class": doc_class,
        "sku": sku,
        "vendor_id": vendor_id,
        "persona_scope": persona_scope,
        "text": text,
    }


def contract_chunks(v):
    doc_id, sku, vid = v.contract_id, v.sku, v.vendor_id
    clauses = [
        f"Supply agreement {doc_id}. Vendor {vid} is the {v.role} supplier of {sku}, classified Tier {v.tier}.",
        f"Lead time. Vendor {vid} delivers {sku} within {v.lead_time_days} days of a confirmed order.",
        f"Order terms. Minimum order quantity for {sku} from vendor {vid} is {v.moq} units at {v.unit_cost_usd} USD per unit.",
        f"Penalty. Cancelling a confirmed order for {sku} with vendor {vid} costs {v.penalty_pct}% of order value.",
        f"Status. Contract {doc_id} is {'approved' if v.approved_contract else 'not approved'} for use.",
    ]
    return [chunk(doc_id, i, "contract", t, sku=sku, vendor_id=vid) for i, t in enumerate(clauses, 1)]


def procedure_chunks(persona, table):
    doc_id = f"SOP-DISRUPTION-{persona.upper().replace('_', '-')}"
    name = PERSONA_NAMES[persona]
    chunks = []
    for severity, by_type in table.items():
        for dtype, action in by_type.items():
            text = f"{name} procedure for {TYPE_NAMES[dtype]} at {SEVERITY_TEXT[severity]}: {ACTION_TEXT[action]}."
            chunks.append(chunk(doc_id, len(chunks) + 1, "sop", text, persona_scope=persona))
    chunks.append(
        chunk(doc_id, len(chunks) + 1, "sop",
              f"{name} procedure at severity 5 (systemic, no near-term alternate): do not act alone, escalate to a human.",
              persona_scope=persona)
    )
    return chunks


def policy_chunks(policy):
    return [chunk(pid, 1, "policy", f"{pid}. {rule['text']}.") for pid, rule in policy["rules"].items()]


def transfer_and_escalation_chunks(policy):
    limit = f"{policy['PO_APPROVAL_LIMIT']} {policy['CURRENCY']}"
    return [
        chunk("SOP-TRANSFER", 1, "sop", "Stock transfer. A peer DC may donate stock only if it keeps at least 10 days of cover after the transfer.", persona_scope="retail_dc"),
        chunk("SOP-TRANSFER", 2, "sop", "Stock transfer is a Retail DC option. Plant sites cannot receive transfers from peer DCs.", persona_scope="retail_dc"),
        chunk("SOP-ESCALATION", 1, "sop", f"Finance approval. A single purchase order above {limit} must be escalated for approval."),
        chunk("SOP-ESCALATION", 2, "sop", "Corroboration. Actions at severity 4 or higher need signals from at least two independent source domains. Until then, monitor."),
    ]


def main():
    params = yaml.safe_load((ROOT / "data/synth/doc_params.yaml").read_text(encoding="utf-8"))
    policy = yaml.safe_load((ROOT / "configs/policy.yaml").read_text(encoding="utf-8"))
    vendors = pd.read_csv(ROOT / "data/synth/vendors.csv")

    chunks = [c for v in vendors.itertuples() for c in contract_chunks(v)]
    for persona, table in params["procedure"].items():
        chunks += procedure_chunks(persona, table)
    chunks += policy_chunks(policy) + transfer_and_escalation_chunks(policy)

    out = ROOT / "data/synth/documents.jsonl"
    out.write_text("".join(json.dumps(c) + "\n" for c in chunks), encoding="utf-8")
    print("wrote documents.jsonl chunks", len(chunks), "docs", len({c["doc_id"] for c in chunks}))


if __name__ == "__main__":
    main()
