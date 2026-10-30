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
