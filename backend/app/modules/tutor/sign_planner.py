from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SIGN_PACKAGE_ROOT = REPOSITORY_ROOT / "avatar-sign-package"
MANIFEST_PATH = SIGN_PACKAGE_ROOT / "manifest" / "signs.json"
PHRASE_MAP_PATH = SIGN_PACKAGE_ROOT / "manifest" / "phrase_map.json"
EXPRESSION_TOKEN_PATTERN = re.compile(r"\d+|[A-Za-z]+|[+\-−×*/÷=()]|[^\s]")
NUMBER_PATTERN = re.compile(r"\b\d+\b")


@dataclass(frozen=True)
class SignPlan:
    """A semantic sign request plus its production playback availability."""

    sign_actions: tuple[str, ...]
    playable_actions: tuple[str, ...]
    unavailable_actions: tuple[str, ...]
    unsupported_actions: tuple[str, ...]
    unsupported_tokens: tuple[str, ...]

    @property
    def is_fully_supported(self) -> bool:
        return not (
            self.unavailable_actions
            or self.unsupported_actions
            or self.unsupported_tokens
        )


@lru_cache(maxsize=1)
def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_phrase_map() -> dict[str, Any]:
    return json.loads(PHRASE_MAP_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _manifest_by_id() -> dict[str, dict[str, Any]]:
    return {entry["id"]: entry for entry in _load_manifest()["signs"]}


class MathSignPlanner:
    """Plan short manifest-backed sign sequences for mathematics teaching.

    The teaching instruction is preferred over raw expression tokens. The
    planner never creates motion and never treats an unreviewed lexical clip as
    production-playable. sign_actions stays as the semantic API contract;
    playable_actions contains only actions approved by the manifest.
    """

    def __init__(self) -> None:
        sequence_policy = _load_phrase_map()["sequence_policy"]
        self.max_sign_actions = int(sequence_policy["max_actions_per_step"])

    def plan(
        self,
        *,
        instruction: str = "",
        expression: str | None = None,
        context_actions: tuple[str, ...] = (),
    ) -> SignPlan:
        instruction_actions = self._actions_from_instruction(instruction)
        unsupported_tokens: list[str] = []

        if instruction_actions:
            candidates = instruction_actions
        elif context_actions:
            candidates = list(context_actions)
        elif expression:
            candidates, unsupported_tokens = self._actions_from_expression(
                expression
            )
            candidates = self._compact_expression_actions(candidates)
        else:
            candidates = []

        candidates = self._unique(candidates)
        if "BOTH_SIDES" in candidates and "BALANCE" in candidates:
            candidates = [action for action in candidates if action != "BALANCE"]
        candidates = candidates[: self.max_sign_actions]
        manifest = _manifest_by_id()
        sign_actions: list[str] = []
        playable_actions: list[str] = []
        unavailable_actions: list[str] = []
        unsupported_actions: list[str] = []

        for action in candidates:
            entry = manifest.get(action)
            if entry is None:
                unsupported_actions.append(action)
                continue

            sign_actions.append(action)
            if self._is_playable(entry):
                playable_actions.append(action)
            else:
                unavailable_actions.append(action)

        return SignPlan(
            sign_actions=tuple(sign_actions),
            playable_actions=tuple(playable_actions),
            unavailable_actions=tuple(unavailable_actions),
            unsupported_actions=tuple(self._unique(unsupported_actions)),
            unsupported_tokens=tuple(self._unique(unsupported_tokens)),
        )

    def manifest_entry(self, sign_id: str) -> dict[str, Any] | None:
        """Return a copy so callers cannot mutate the cached manifest."""
        entry = _manifest_by_id().get(sign_id)
        return dict(entry) if entry else None

    def _actions_from_instruction(self, instruction: str) -> list[str]:
        matches: list[tuple[int, int, str]] = []
        phrase_map = _load_phrase_map()

        for rule_index, rule in enumerate(phrase_map["rules"]):
            for match in re.finditer(
                rule["pattern"], instruction, flags=re.IGNORECASE
            ):
                for action_index, action in enumerate(rule["actions"]):
                    priority = rule_index * 10 + action_index
                    matches.append((match.start(), priority, action))

        for match in NUMBER_PATTERN.finditer(instruction):
            for digit_index, action in enumerate(self._number_actions(match.group())):
                matches.append((match.start(), 1_000 + digit_index, action))

        for token, action in phrase_map["expression_tokens"].items():
            if not token.isalpha():
                continue
            token_pattern = rf"\b{re.escape(token)}\b"
            for match in re.finditer(token_pattern, instruction, flags=re.IGNORECASE):
                matches.append((match.start(), 2_000, action))

        matches.sort(key=lambda item: (item[0], item[1]))
        return self._unique([action for _, _, action in matches])

    def _actions_from_expression(
        self,
        expression: str,
    ) -> tuple[list[str], list[str]]:
        actions: list[str] = []
        unsupported_tokens: list[str] = []
        token_map = _load_phrase_map()["expression_tokens"]

        for token in EXPRESSION_TOKEN_PATTERN.findall(expression):
            if token.isdigit():
                actions.extend(self._number_actions(token))
            elif token in token_map:
                actions.append(token_map[token])
            elif token.lower() in token_map:
                actions.append(token_map[token.lower()])
            elif token in {"(", ")"}:
                actions.append("BRACKET")
            else:
                unsupported_tokens.append(token)

        return actions, unsupported_tokens

    @staticmethod
    def _is_playable(entry: dict[str, Any]) -> bool:
        status = entry.get("validation_status")
        return status == "validated" or (
            entry.get("category") == "system" and status == "technical_only"
        )

    @staticmethod
    def _compact_expression_actions(actions: list[str]) -> list[str]:
        unique = MathSignPlanner._unique(actions)
        concept_actions = [
            action
            for action in unique
            if not action.startswith("NUMBER_") and action != "VARIABLE"
        ]
        return concept_actions or unique[:1]

    @staticmethod
    def _number_actions(number: str) -> list[str]:
        return [f"NUMBER_{digit}" for digit in number]

    @staticmethod
    def _unique(values: list[str] | tuple[str, ...]) -> list[str]:
        return list(dict.fromkeys(values))
