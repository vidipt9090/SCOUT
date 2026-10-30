"""S5/S6, CrewAI side: resolve MCP tools through Agent.get_mcp_tools, write then read, no LLM call."""
import crewai
from crewai import Agent
from crewai.mcp import MCPServerHTTP

agent = Agent(role="spike", goal="spike", backstory="spike", llm="gpt-4o-mini")
tools = {t.name: t for t in agent.get_mcp_tools([MCPServerHTTP(url="http://127.0.0.1:8102/mcp")])}
print("crewai", crewai.__version__, "tools", sorted(tools))
write = next(t for n, t in tools.items() if n.endswith("blackboard_write"))
read = next(t for n, t in tools.items() if n.endswith("blackboard_read"))
print("S5 CREWAI write", write.run(run_id="spike-s5", author="crewai", topic="t", payload={"from": "crewai"}, trust_level="trusted"))
print("S6 read", read.run(run_id="spike-s5", topic="t", cursor=0))
