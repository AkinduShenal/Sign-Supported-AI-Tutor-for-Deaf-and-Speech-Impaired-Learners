import re
from dataclasses import dataclass


SUPPORTED_ANIMATION_ACTIONS = frozenset(
    {
        "ADDITION",
        "ALGEBRA",
        "BALANCE",
        "EQUATION",
        "NUMBER_3",
        "NUMBER_4",
        "NUMBER_5",
        "NUMBER_7",
        "SUBSTITUTION",
        "SUBTRACTION",
    }
)

EXPRESSION_TOKEN_PATTERN = re.compile(r"\d+|[A-Za-z]+|[+\-−×*/÷=()]|[^\s]")

TEXT_SIGN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bsubstitut(?:e|ed|ion)\b", re.IGNORECASE), "SUBSTITUTION"),
    (re.compile(r"\b(?:subtract|subtracted|minus)\b", re.IGNORECASE), "SUBTRACTION"),
    (re.compile(r"\b(?:add|added|addition|plus)\b", re.IGNORECASE), "ADDITION"),
    (
        re.compile(r"\b(?:multiply|multiplied|multiplication|times)\b", re.IGNORECASE),
        "MULTIPLICATION",
    ),
    (re.compile(r"\b(?:divide|divided|division)\b", re.IGNORECASE), "DIVISION"),
    (re.compile(r"\b(?:equation|equal|equals)\b", re.IGNORECASE), "EQUATION"),
    (
        re.compile(
            r"\b(?:balance|balanced|both sides|same operation)\b", re.IGNORECASE
        ),
        "BALANCE",
    ),
    (re.compile(r"\b(?:algebra|variable|x)\b", re.IGNORECASE), "ALGEBRA"),
    (re.compile(r"\d+"), "NUMBER"),
)


@dataclass(frozen=True)
class SignPlan:
    sign_actions: tuple[str, ...]
    unsupported_actions: tuple[str, ...]
    unsupported_tokens: tuple[str, ...]

    @property
    def is_fully_supported(self) -> bool:
        return not self.unsupported_actions and not self.unsupported_tokens


class MathSignPlanner:
    """Convert supported mathematics text and expressions into sign actions."""

    def plan(
        self,
        *,
        instruction: str = "",
        expression: str | None = None,
        context_actions: tuple[str, ...] = (),
    ) -> SignPlan:
        text_actions = self._actions_from_text(instruction)
        expression_actions: list[str] = []
        unsupported_tokens: list[str] = []

        if expression:
            expression_actions, unsupported_tokens = self._actions_from_expression(
                expression
            )
            expression_action_set = set(expression_actions)
            text_actions = [
                action
                for action in text_actions
                if action not in expression_action_set
                and not action.startswith("NUMBER_")
            ]

        sign_actions = self._unique([*context_actions, *text_actions])
        sign_actions.extend(expression_actions)
        unsupported_actions = self._unique(
            [
                action
                for action in sign_actions
                if action not in SUPPORTED_ANIMATION_ACTIONS
            ]
        )

        return SignPlan(
            sign_actions=tuple(sign_actions),
            unsupported_actions=tuple(unsupported_actions),
            unsupported_tokens=tuple(self._unique(unsupported_tokens)),
        )

    def _actions_from_text(self, text: str) -> list[str]:
        matches: list[tuple[int, int, str]] = []
        for priority, (pattern, action) in enumerate(TEXT_SIGN_PATTERNS):
            for match in pattern.finditer(text):
                if action == "NUMBER":
                    for number_action in self._number_actions(match.group()):
                        matches.append((match.start(), priority, number_action))
                else:
                    matches.append((match.start(), priority, action))

        matches.sort(key=lambda item: (item[0], item[1]))
        return self._unique([action for _, _, action in matches])

    def _actions_from_expression(
        self,
        expression: str,
    ) -> tuple[list[str], list[str]]:
        actions: list[str] = []
        unsupported_tokens: list[str] = []

        for token in EXPRESSION_TOKEN_PATTERN.findall(expression):
            if token.isdigit():
                actions.extend(self._number_actions(token))
            elif token.lower() == "x":
                actions.append("ALGEBRA")
            elif token == "+":
                actions.append("ADDITION")
            elif token in {"-", "−"}:
                actions.append("SUBTRACTION")
            elif token in {"*", "×"}:
                actions.append("MULTIPLICATION")
            elif token in {"/", "÷"}:
                actions.append("DIVISION")
            elif token == "=":
                actions.append("EQUATION")
            elif token in {"(", ")"}:
                continue
            else:
                unsupported_tokens.append(token)

        return actions, unsupported_tokens

    @staticmethod
    def _number_actions(number: str) -> list[str]:
        return [f"NUMBER_{digit}" for digit in number]

    @staticmethod
    def _unique(values: list[str] | tuple[str, ...]) -> list[str]:
        return list(dict.fromkeys(values))
