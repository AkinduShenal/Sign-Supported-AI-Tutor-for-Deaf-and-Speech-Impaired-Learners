"""Small bilingual BM25 lesson index; no DB writes or embedding service."""

import json
import math
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

KNOWLEDGE_PATH = Path(__file__).parent / "knowledge/linear_equations.json"
STOP_WORDS = set("a an the is are do does why how i we you to of in on by at it this that me please explain step can what about for and or must will would".split()) | {
    "ඇයි", "කොහොමද", "මට", "මම", "අපි", "මෙම", "මේ", "කරන්නේ", "කරන්න", "කියන්නේ", "කියලා", "ද", "පැහැදිලි", "පියවර",
    "මෙහෙම", "එහෙම", "වෙන්නේ", "කරමු",
}


class KnowledgeTeachingPart(BaseModel):
    text: str = Field(min_length=1)
    text_si: str = Field(min_length=1)
    sign_actions: list[str]


class KnowledgeSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title_en: str
    title_si: str
    text_en: str
    text_si: str
    source_ref: str
    review_status: str = "teacher_review_required"
    sign_actions: list[str] = Field(default_factory=list)
    avatar_parts: list[KnowledgeTeachingPart] = Field(default_factory=list)
    score: float = 0


def terms(text: str) -> list[str]:
    # Sinhala vowel/diacritic marks must stay with letters; \w alone drops them.
    words, word = [], []
    for char in unicodedata.normalize("NFC", text).casefold():
        if unicodedata.category(char)[0] in {"L", "N", "M"}:
            word.append(char)
        elif word:
            words.append("".join(word))
            word = []
    if word:
        words.append("".join(word))
    return [word for word in words if word not in STOP_WORDS and not word.isdecimal()]


class LessonKnowledgeIndex:
    def __init__(self, path: Path = KNOWLEDGE_PATH):
        corpus = json.loads(path.read_text(encoding="utf-8"))
        self.version = corpus["version"]
        self.review_status = corpus["review_status"]
        self.documents = corpus["chunks"]
        ids = [document["id"] for document in self.documents]
        if len(set(ids)) != len(ids) or not ids or any(not id for id in ids):
            raise ValueError("Knowledge chunk IDs must be nonempty and unique")
        self.tokens = [Counter(terms(" ".join([
            document["title_en"], document["title_si"], document["text_en"],
            document["text_si"], " ".join(document["search_terms"]),
        ]))) for document in self.documents]
        self.lengths = [sum(tokens.values()) for tokens in self.tokens]
        self.average_length = sum(self.lengths) / len(self.lengths)
        if self.average_length <= 0:
            raise ValueError("Knowledge documents must contain searchable text")
        self.frequency = Counter(token for tokens in self.tokens for token in tokens)
        self.anchor_terms = set(terms(" ".join(term for document in self.documents for term in document["search_terms"])))

    def search(self, query: str, level: str = "foundation", strategy: str = "step_by_step", limit: int = 3) -> list[KnowledgeSource]:
        query_terms = set(terms(query))
        if not query_terms & self.anchor_terms:
            return []
        ranked = []
        count = len(self.documents)
        for document, tokens, length in zip(self.documents, self.tokens, self.lengths, strict=True):
            score = 0.0
            for token in query_terms:
                occurrence = tokens[token]
                if not occurrence:
                    continue
                frequency = self.frequency[token]
                inverse_frequency = math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
                score += inverse_frequency * occurrence * 2.5 / (occurrence + 1.5 * (0.25 + 0.75 * length / self.average_length))
            # Context re-ranks real matches; it never creates an unrelated hit.
            if score > 0:
                score *= (1.1 if level in document["levels"] else 1) * (1.1 if strategy in document["strategies"] else 1)
                ranked.append((score, document))
        ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
        return [KnowledgeSource(
            **{key: document[key] for key in ("id", "title_en", "title_si", "text_en", "text_si", "source_ref", "sign_actions")},
            avatar_parts=document.get("avatar_parts", []),
            score=round(score, 4), review_status=self.review_status,
        ) for score, document in ranked[:limit]]


@lru_cache(maxsize=1)
def get_knowledge_index() -> LessonKnowledgeIndex:
    return LessonKnowledgeIndex()


def lesson_notes(query: str, level: str, strategy: str, limit: int = 1) -> list[KnowledgeSource]:
    """Optional enrichment must never make the existing lesson unavailable."""
    from app.core.config import settings

    if not settings.rag_enabled:
        return []
    try:
        return get_knowledge_index().search(query, level, strategy, limit)
    except (OSError, ValueError, KeyError, TypeError):
        return []
