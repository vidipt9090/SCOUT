"""G3 smoke check: classify the poison feed once, and report which items a Scout marked relevant. Run in the sensing environment."""
import time

from dotenv import load_dotenv

load_dotenv()

from scout_platform.tracing.writer import TraceWriter  # noqa: E402
from sensing import hooks  # noqa: E402
from sensing.crew import run_scout  # noqa: E402
from sensing.news import replay  # noqa: E402

run_id = f"g3-poison-{int(time.time())}"
tracer = TraceWriter(run_id, "crewai")
hooks.use_trace(tracer, "scout_cot_v1")
feed = replay.poison()
signals = run_scout("A", feed, run_id, tracer) + run_scout("B", feed, run_id, tracer)
for s in signals:
    print(s.scout_id, s.is_relevant, s.disruption_type, s.confidence, s.source_domain, "|", s.headline[:60])
print("relevant", sum(s.is_relevant for s in signals), "of", len(signals), "feed items", len(feed))
