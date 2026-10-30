#!/usr/bin/env bash
# Runs S4, S5 and S6 across the three environments. No API keys needed.
cd "$(dirname "$0")/.."
export PYTHONPATH=. PYTHONUTF8=1 OPENAI_API_KEY=not-used CREWAI_TRACING_ENABLED=false
rm -f runs/blackboard/spike-s5.jsonl
.venvs/scout_platform/Scripts/python.exe -m uvicorn sensing.blackboard_service.app:app --port 8101 --log-level warning &
.venvs/scout_platform/Scripts/python.exe -m scout_platform.mcp_server.server &
.venvs/decision/Scripts/python.exe spikes/s4_a2a_server.py &
sleep 10
echo "##### S4"; .venvs/sensing/Scripts/python.exe spikes/s4_a2a_client.py 2>&1 | tail -6
echo "##### S5 ADK"; .venvs/decision/Scripts/python.exe spikes/s5_adk_client.py 2>&1 | tail -6
echo "##### S5/S6 CREWAI"; .venvs/sensing/Scripts/python.exe spikes/s5_crewai_client.py 2>&1 | tail -8
for p in 8101 8102 8103; do
  netstat -ano | grep "127.0.0.1:$p " | grep LISTENING | awk '{print $NF}' | sort -u | xargs -r -I{} taskkill //F //PID {} >/dev/null 2>&1
done
echo "##### blackboard log"; cat runs/blackboard/spike-s5.jsonl
