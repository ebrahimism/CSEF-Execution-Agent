"""S2 overlap: prove two existing independent API adapters feed one S1 planner."""
import json
from pathlib import Path

from csef_gate.engineering.task_graph import generate_graph
from csef_gate.project import ProjectBook
from csef_gate.providers.direct import DirectAPI


def test_both_independent_api_protocols_produce_same_scoped_plan(tmp_path):
    book = ProjectBook.create(
        tmp_path / "book", "Build one simple order service",
        answers={
            "users": "Store operators", "workflow": "Save order and inspect stock",
            "success": "Working order program", "constraints": "Local-only test",
        },
        facts=[{"id": "REQ-001", "kind": "requirement",
                "text": "Persist order entries and verify reading them back"}],
    )
    graph = {"tasks": [
        {"id": "CODE", "title": "Write one order service", "kind": "code",
         "fact_ids": ["GOAL", "REQ-001"], "depends_on": [],
         "scope": "Create local order file with validation",
         "inputs": ["Approved order brief"], "outputs": ["Order service source"],
         "acceptance": ["Order can be saved and read from new store"],
         "files": ["app.py"]},
        {"id": "INTEG", "title": "Verify the complete order flow", "kind": "integration",
         "fact_ids": ["GOAL", "REQ-001"], "depends_on": ["CODE"],
         "scope": "Exercise persisted store with two sample orders",
         "inputs": ["Working app source"], "outputs": ["Integration result"],
         "acceptance": ["Two orders remain after process restart"],
         "files": ["tests/test_orders.py"]},
        {"id": "DELIVER", "title": "Prepare reproducible source bundle", "kind": "delivery",
         "fact_ids": ["GOAL", "REQ-001"], "depends_on": ["INTEG"],
         "scope": "Generate a reproducible installation guide",
         "inputs": ["Passing integration result"], "outputs": ["Delivery package"],
         "acceptance": ["Fresh environment can run the application"],
         "files": ["README.md"]},
    ]}
    seen = []
    def openai_send(url, headers, payload, timeout):
        seen.append(("openai", url, headers, payload))
        return {"status": "completed", "model": "openai-simulated",
                "output": [{"type": "message",
                            "content": [{"type": "output_text", "text": json.dumps(graph)}]}],
                "usage": {"input_tokens": 200, "output_tokens": 120}}
    def anthropic_send(url, headers, payload, timeout):
        seen.append(("anthropic", url, headers, payload))
        return {"stop_reason": "end_turn", "model": "anthropic-simulated",
                "content": [{"type": "text", "text": json.dumps(graph)}],
                "usage": {"input_tokens": 201, "output_tokens": 119}}
    openai = DirectAPI("openai", "model-a", api_key="dummy-test-a", send=openai_send)
    anthropic = DirectAPI("anthropic", "model-b", api_key="dummy-test-b", send=anthropic_send)
    first = generate_graph(book, openai)
    second = generate_graph(book, anthropic)
    assert first["proposal_id"] == second["proposal_id"]
    assert first["replayed"] is False and second["replayed"] is True
    assert len(seen) == 2
    assert seen[0][1].endswith("/v1/responses")
    assert seen[1][1].endswith("/v1/messages")
    assert seen[0][3]["model"] == "model-a"
    assert seen[1][3]["model"] == "model-b"
    with book.connection() as con:
        assert con.execute("SELECT count(*) FROM calls WHERE status='completed'").fetchone()[0] == 2
        assert con.execute("SELECT count(*) FROM changes WHERE status='proposed'").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 0
    for path in (book.root / "planning_calls").rglob("*"):
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            assert "dummy-test-a" not in content and "dummy-test-b" not in content
