"""Small, safe recursive-descent search language. Never evaluates Python code.

Grammar (highest precedence first):
    atom := '(' expression ')' | field operator value
    unary := '!' unary | atom
    conjunction := unary ('&&' unary)*
    expression := conjunction ('||' conjunction)*
Values may be JSON double-quoted strings; unquoted simple values are allowed.
"""

from dataclasses import dataclass
from datetime import datetime
import json
import re

from .errors import CriteriaError, ValidationError
from .records import RECORD_TYPES, TEXT_FIELDS, TIME_FIELDS, Record, parse_time

MAX_EXPRESSION_LENGTH = 4096
MAX_NESTING = 50
TOKEN = re.compile(r'\s*(?:("(?:[^"\\]|\\.)*")|(&&|\|\||!|\(|\)|<|>|=)|([^\s()!<>=&|"\\]+))')


@dataclass(frozen=True)
class Predicate:
    field: str
    operator: str
    value: str | datetime

    def matches(self, record: Record) -> bool:
        actual = record.kind if self.field == "type" else getattr(record, self.field, None)
        if actual is None:
            return False
        if self.operator == "contains":
            return self.value.casefold() in actual.casefold()
        if self.operator == "<":
            return actual < self.value
        if self.operator == ">":
            return actual > self.value
        return actual == self.value


@dataclass(frozen=True)
class Negation:
    operand: object

    def matches(self, record: Record) -> bool:
        return not self.operand.matches(record)


@dataclass(frozen=True)
class Junction:
    operator: str
    operands: tuple

    def matches(self, record: Record) -> bool:
        results = (operand.matches(record) for operand in self.operands)
        return all(results) if self.operator == "&&" else any(results)


class Parser:
    def __init__(self, expression: str):
        if not isinstance(expression, str) or not expression.strip():
            raise CriteriaError("Search expression cannot be empty.")
        if len(expression) > MAX_EXPRESSION_LENGTH:
            raise CriteriaError(f"Search expression exceeds {MAX_EXPRESSION_LENGTH} characters.")
        self.tokens = []
        position = 0
        while position < len(expression):
            if not expression[position:].strip():
                break
            match = TOKEN.match(expression, position)
            if not match:
                raise CriteriaError(f"Invalid search syntax at character {position + 1}.")
            quoted, operator, bare = match.groups()
            if quoted is not None:
                try:
                    self.tokens.append((json.loads(quoted), True))
                except json.JSONDecodeError as exc:
                    raise CriteriaError("Invalid escape in quoted search value.") from exc
            else:
                self.tokens.append((operator or bare, False))
            position = match.end()
        self.position = 0

    def accept(self, token: str) -> bool:
        if self.position < len(self.tokens) and self.tokens[self.position] == (token, False):
            self.position += 1
            return True
        return False

    def take(self) -> tuple[str, bool]:
        if self.position >= len(self.tokens):
            raise CriteriaError("Unexpected end of search expression.")
        result = self.tokens[self.position]
        self.position += 1
        return result

    def parse(self):
        result = self.expression(0)
        if self.position != len(self.tokens):
            raise CriteriaError(f"Unexpected token: {self.tokens[self.position][0]!r}.")
        return result

    def expression(self, depth: int):
        operands = [self.conjunction(depth)]
        while self.accept("||"):
            operands.append(self.conjunction(depth))
        return operands[0] if len(operands) == 1 else Junction("||", tuple(operands))

    def conjunction(self, depth: int):
        operands = [self.unary(depth)]
        while self.accept("&&"):
            operands.append(self.unary(depth))
        return operands[0] if len(operands) == 1 else Junction("&&", tuple(operands))

    def unary(self, depth: int):
        if depth > MAX_NESTING:
            raise CriteriaError(f"Search nesting exceeds {MAX_NESTING} levels.")
        if self.accept("!"):
            return Negation(self.unary(depth + 1))
        if self.accept("("):
            result = self.expression(depth + 1)
            if not self.accept(")"):
                raise CriteriaError("Missing closing parenthesis.")
            return result
        return self.predicate()

    def predicate(self) -> Predicate:
        field, quoted = self.take()
        if quoted or field not in TEXT_FIELDS | TIME_FIELDS | {"type"}:
            raise CriteriaError(f"Unknown search field: {field!r}.")
        operator, quoted = self.take()
        permitted = {"contains"} if field in TEXT_FIELDS else {"<", ">", "="}
        if field == "type":
            permitted = {"="}
        if quoted or operator not in permitted:
            raise CriteriaError(f"Operator for {field} must be: {', '.join(sorted(permitted))}.")
        value, quoted = self.take()
        if not quoted and value in {"&&", "||", "!", "(", ")", "<", ">", "="}:
            raise CriteriaError("Missing predicate value; quote text values containing symbols.")
        if field == "type" and value not in RECORD_TYPES:
            raise CriteriaError("Type must be note, task, event, or contact.")
        if field in TIME_FIELDS:
            try:
                value = parse_time(value)
            except ValidationError as exc:
                raise CriteriaError(str(exc)) from exc
        return Predicate(field, operator, value)


def parse_criteria(expression: str):
    """Compile a criterion once; returned immutable tree can match many PIRs."""
    return Parser(expression).parse()
