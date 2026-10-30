# Progress log

Format: date | task | command | pass or fail | one line of output.

2026-10-30 | B0.2 | pip install -r <service>/requirements.in (3 environments) | pass | pip check: No broken requirements found (all three)
2026-10-30 | B0.2 | pip install --dry-run -r <service>/requirements.txt in fresh environments | pass | exit 0 for all three
2026-10-30 | B0.3 | scan of pinned files for other agent frameworks | pass | no other agent framework (all three)
2026-10-30 | B0.4 | python -m pytest (recipe of make test) in all three environments | pass | 13 passed
2026-10-30 | B0.4 | python -m contracts.export_schemas | pass | 6 schemas written
2026-10-30 | S4 | bash spikes/run_keyless.sh | pass | S4 PASS crewai 1.15.33 verdict plan-for-asm-001 approve
2026-10-30 | S5 | bash spikes/run_keyless.sh | pass | adk 2.13.0 and crewai 1.15.33 both listed and called MCP tools
2026-10-30 | S6 | bash spikes/run_keyless.sh | pass | read through MCP returned both framework entries, cursor 2
2026-10-30 | S1 | python spikes/s1_news.py | pass | 10 articles, replay offline ok
2026-10-30 | S2 | python spikes/s2_crewai.py | pass | Classification object, hooks fired, 16.0s
2026-10-30 | S3 | python spikes/s3_adk.py | pass | tool and output_schema together, 6.8s
2026-10-30 | S7 | python spikes/s7_probe.py | pass | gemini-3.1-flash-lite ok, 1.3s
2026-10-30 | make | make test | pass | 13 passed
2026-10-30 | S1 GNews | python spikes/s1c_gnews.py | pass for current news, fail for 2016 | 2804 counted, 10 returned; 2016 window 0
2026-10-30 | B2.1 | make m5-extract | pass | CA_3, 15 SKUs, 16425 rows, simulated_today 2016-05-22
2026-10-30 | B2.2 | make inventory | pass | 60 rows, 4 locations
2026-10-30 | B2.1-2 | make test | pass | 15 passed
2026-10-30 | B2.3 | make vendors | pass | 32 vendors, 15 SKUs, 1 Tier 3
2026-10-30 | B2.4 | git log data/scenarios/ground_truth.yaml | pass | 4884e29 precedes contract text; 18 cells match procedure
2026-10-30 | B2.5 | make docs | pass | 193 chunks, 45 docs
2026-10-30 | B2.6 | make rag-probe | pass with deviation | hit 1.00, precision 0.64 of ceiling 0.68, exact clause 18/18
2026-10-30 | B2.7 | make forecast | pass | 15 SKUs cached
2026-10-30 | B2.8 | make news-snapshot, offline replay | pass | 29 articles, 22 domains
2026-10-30 | B2.9 | pytest tests/test_news_and_tracing.py | pass | 8 scenarios, 12 poison items
2026-10-30 | B2.10-11 | make up, make check | pass | 8 tools, blackboard through MCP, entries 1
2026-10-30 | B2.12 | make test | pass | 37 passed
2026-10-30 | G2 | wipe generated files, make data, make test | pass | rebuilt from scratch, 37 passed
2026-10-30 | B2.3 rework | make vendors docs rag-index rag-probe, make test | pass | 8 vendors, 32 agreements
