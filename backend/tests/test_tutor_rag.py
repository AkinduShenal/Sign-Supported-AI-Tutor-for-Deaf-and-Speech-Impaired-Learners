"""Local retrieval and mocked generation regressions; no provider/DB writes."""

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import app
from app.core.config import settings
from app.modules.tutor import rag
from app.modules.tutor.knowledge import LessonKnowledgeIndex, get_knowledge_index, terms

client = TestClient(app)


@pytest.fixture(autouse=True)
def local_only(monkeypatch):
    monkeypatch.setattr(settings, "rag_enabled", True)
    monkeypatch.setattr(settings, "rag_generation_enabled", False)
    monkeypatch.setattr(settings, "openai_api_key", None)


def ask(question="Why do we subtract from both sides?", **extra):
    return client.post("/api/v1/tutor/rag/answer", json={
        "question": question, "level": "foundation", "strategy": "step_by_step",
        "example_problem": "x + 3 = 7", "step_index": 2, **extra,
    })


def test_retrieves_inverse_operation_with_sources_and_known_gestures():
    result = ask()
    assert result.status_code == 200
    body = result.json()
    assert body["supported"] is True
    assert body["mode"] == "extractive"
    assert "inverse-add-subtract" in {source["id"] for source in body["sources"]}
    assert body["review_status"] == "teacher_review_required"
    assert all(paragraph["text_si"] for paragraph in body["paragraphs"])
    assert body["avatar_segments"]


def test_sinhala_combining_marks_and_retrieval():
    assert "දෙපසින්ම" in terms("දෙපසින්ම 3 අඩු කරන්න")
    sources = get_knowledge_index().search("දෙපසින්ම 3 අඩු කරන්නේ ඇයි?")
    assert "inverse-add-subtract" in {source.id for source in sources}


def test_unknown_question_does_not_use_current_step_as_fake_evidence():
    body = ask("Who won the football match?").json()
    assert body["supported"] is False
    assert body["sources"] == []
    assert body["avatar_segments"] == []


def test_generic_question_uses_checked_current_context():
    body = ask("Explain this step.").json()
    assert body["supported"] is True
    assert any(source["id"].startswith("worked-example:") for source in body["sources"])


@pytest.mark.parametrize("extra", [
    {"example_problem": "__import__('os')"}, {"step_index": 50},
    {"concept_id": "biology"}, {"question": " "}, {"student_id": "STU001"},
])
def test_refuses_unknown_context_blank_questions_and_extra_diagnostics(extra):
    assert ask(**extra).status_code == 422


def test_disabled_help_keeps_existing_preview_available(monkeypatch):
    monkeypatch.setattr(settings, "rag_enabled", False)
    assert ask().json()["mode"] == "disabled"
    lesson = client.get("/api/v1/tutor/grade10/foundation").json()
    assert lesson["worked_examples"][0]["problem"] == "x + 3 = 7"
    assert all(step["knowledge_notes"] == [] for step in lesson["worked_examples"][0]["steps"])


def test_missing_corpus_falls_back_without_breaking_lessons(monkeypatch):
    def unavailable():
        raise OSError("missing corpus")
    monkeypatch.setattr(rag, "get_knowledge_index", unavailable)
    assert ask().json()["mode"] == "unavailable"


def mock_generation(monkeypatch, generated, status=200):
    import json

    monkeypatch.setattr(settings, "rag_generation_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("test-key-not-real"))
    real_client = httpx.AsyncClient

    def respond(request):
        payload = json.loads(request.content)
        assert payload["store"] is False
        assert payload["text"]["format"]["type"] == "json_schema"
        assert "student_id" not in request.content.decode()
        return httpx.Response(status, json={"status": "completed", "output": [{
            "type": "message", "content": [{"type": "output_text", "text": json.dumps(generated)}],
        }]})
    monkeypatch.setattr(rag.httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(respond), **kwargs))


def test_generates_with_retrieved_citations_and_no_student_payload(monkeypatch):
    mock_generation(monkeypatch, {"supported": True, "paragraphs": [{
        "text_en": "Subtracting the same amount preserves equality.",
        "text_si": "දෙපසින්ම එකම ප්‍රමාණය අඩු කළ විට සමානතාව රැකෙනවා.",
        "source_ids": ["inverse-add-subtract"],
    }]})
    body = ask().json()
    assert body["mode"] == "openai"
    assert [source["id"] for source in body["sources"]] == ["inverse-add-subtract"]


@pytest.mark.parametrize("source_ids", [[], ["invented-source"]])
def test_untrusted_citations_use_extractively_grounded_fallback(monkeypatch, source_ids):
    mock_generation(monkeypatch, {"supported": True, "paragraphs": [{
        "text_en": "Unsupported response", "text_si": "පිළිතුර", "source_ids": source_ids,
    }]})
    body = ask().json()
    assert body["mode"] == "fallback"
    assert all("Unsupported response" != paragraph["text_en"] for paragraph in body["paragraphs"])


def test_provider_failure_uses_local_notes(monkeypatch):
    mock_generation(monkeypatch, {}, status=503)
    assert ask().json()["mode"] == "fallback"


def test_malformed_generated_schema_uses_local_notes(monkeypatch):
    mock_generation(monkeypatch, ["not an answer object"])
    assert ask().json()["mode"] == "fallback"


def test_knowledge_notes_augment_without_altering_equation_steps():
    lesson = client.get("/api/v1/tutor/grade10/foundation").json()
    steps = lesson["worked_examples"][0]["steps"]
    assert steps[1]["instruction"] == "Subtract 3 from both sides."
    assert steps[1]["knowledge_notes"]
    assert steps[-1]["expression"] == "x = 4"


def test_retriever_context_never_creates_a_match_for_unknown_terms():
    assert LessonKnowledgeIndex().search("astronaut spaceship weather") == []
