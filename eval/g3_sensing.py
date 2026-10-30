"""G3 check, Sensing crew: each agent alone against a planted scenario and a live LLM. Run in the sensing environment."""
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from scout_platform.tracing.writer import TraceWriter  # noqa: E402
from sensing import hooks  # noqa: E402
from sensing.crew import run_scout, run_theme_analyst  # noqa: E402
from sensing.news import replay  # noqa: E402

scenario = sys.argv[1] if len(sys.argv) > 1 else "strike_medium"
run_id = f"g3-sens-{scenario.replace('_', '-')}-{int(time.time())}"
tracer = TraceWriter(run_id, "crewai")
hooks.use_trace(tracer, "scout_cot_v1")
feed = replay.planted(scenario)

start = time.perf_counter()
signals = run_scout("A", feed, run_id, tracer) + run_scout("B", feed, run_id, tracer, "scout_few_shot_v1")
print(f"scouts {time.perf_counter() - start:.1f}s signals {len(signals)}")
for s in signals:
    print(" ", s.scout_id, s.is_relevant, s.disruption_type, s.confidence, s.source_domain)

start = time.perf_counter()
hooks.use_trace(tracer, "theme_v1")
assessment = run_theme_analyst(run_id, ["FOODS_3_363"], tracer)
print(f"theme {time.perf_counter() - start:.1f}s")
print(assessment.model_dump_json() if assessment else "no disruption")
print("trace", tracer.path)
