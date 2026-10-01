from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PACKAGE_ROOT / "manifest" / "signs.json"
PHRASE_MAP_PATH = PACKAGE_ROOT / "manifest" / "phrase_map.json"


@dataclass(frozen=True)
class SignPlan:
    sign_actions: tuple[str, ...]
    skipped_actions: tuple[str, ...]
    unsupported_tokens: tuple[str, ...]


@lru_cache(maxsize=1)
def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


@lru_cache(maxsize=1)
def _load_phrase_map() -> dict:
    return json.loads(PHRASE_MAP_PATH.read_text())


def _available_ids() -> set[str]:
    return {item["id"] for item in _load_manifest()["signs"]}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def plan_signs(
    *,
    instruction: str = "",
    expression: str | None = None,
    context_actions: tuple[str, ...] = (),
) -> SignPlan:
    cfg = _load_phrase_map()
    available = _available_ids()
    actions: list[str] = []

    # Prefer the actual teaching instruction over raw expression tokens.
    for rule in cfg["rules"]:
        if re.search(rule["pattern"], instruction, flags=re.IGNORECASE):
            actions.extend(rule["actions"])

    if not actions:
        actions.extend(context_actions)

    unsupported_tokens: list[str] = []
    if not actions and expression:
        token_map = cfg["expression_tokens"]
        for token in re.findall(r"\d+|[A-Za-z]+|[+\-−×*/÷=()]|[^\s]", expression):
            if token.isdigit():
                actions.extend(f"NUMBER_{digit}" for digit in token)
            elif token in token_map:
                actions.append(token_map[token])
            elif token.lower() in token_map:
                actions.append(token_map[token.lower()])
            elif token in {"(", ")"}:
                actions.append("BRACKET")
            else:
                unsupported_tokens.append(token)

    actions = _unique(actions)
    max_actions = int(cfg["sequence_policy"]["max_actions_per_step"])
    actions = actions[:max_actions]

    supported: list[str] = []
    skipped: list[str] = []
    for action in actions:
        if action in available:
            supported.append(action)
        else:
            skipped.append(action)

    return SignPlan(
        sign_actions=tuple(supported),
        skipped_actions=tuple(skipped),
        unsupported_tokens=tuple(_unique(unsupported_tokens)),
    )
