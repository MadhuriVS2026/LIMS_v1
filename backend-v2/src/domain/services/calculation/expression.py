"""
Safe expression evaluator for analytical test-template formulas.

Deliberately NOT built on `eval()`. Template definitions are user-editable
configuration and the values they produce are GxP-reportable, so the engine is
a purpose-built tokenizer + recursive-descent parser + tree evaluator. That
gives three properties `eval()` cannot: no code-execution surface, a closed set
of permitted operations, and Excel-compatible blank/error semantics.

Grammar (lowest to highest precedence):

    expr        := or_expr
    or_expr     := and_expr ( 'or' and_expr )*
    and_expr    := cmp_expr ( 'and' cmp_expr )*
    cmp_expr    := add_expr ( ( '=' | '==' | '<>' | '!=' | '<' | '<=' | '>' | '>=' ) add_expr )?
    add_expr    := mul_expr ( ( '+' | '-' ) mul_expr )*
    mul_expr    := unary ( ( '*' | '/' ) unary )*
    unary       := ( '-' | '+' | 'not' ) unary | power
    power       := primary ( '^' unary )?
    primary     := NUMBER | STRING | 'true' | 'false' | reference
                 | function '(' args ')' | '[' list ']' | '(' expr ')'
    reference   := NAME ( '.' NAME | '[' expr ']' )*

Blank semantics: the source sheets wrap nearly every formula in
`IFERROR(..., "")`, so a missing input or a division by zero yields a blank
rather than an exception. `EMPTY` is that blank. It propagates through
arithmetic, is skipped by aggregate functions, and is what the caller persists
as "no result yet".
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence


class ExpressionError(ValueError):
    """Raised when an expression is malformed or references something unusable."""


class Empty:
    """
    The blank sentinel, mirroring Excel's `IFERROR(..., "")` result.

    Singleton — use the module-level `EMPTY`. Falsy, and propagates through
    arithmetic so a partially-filled worksheet shows blanks rather than errors.
    """

    _instance: "Empty | None" = None

    def __new__(cls) -> "Empty":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "EMPTY"


EMPTY = Empty()

# ─────────────────────────── Tokenizer ───────────────────────────

_PUNCT = ("<=", ">=", "<>", "!=", "==", "+", "-", "*", "/", "^", "(", ")", "[", "]", ",", ".", "<", ">", "=")
_KEYWORDS = {"and", "or", "not", "true", "false"}


@dataclass(frozen=True)
class _Token:
    kind: str  # NUMBER | STRING | NAME | KEYWORD | PUNCT | END
    value: Any
    pos: int


def _tokenize(src: str) -> list[_Token]:
    tokens: list[_Token] = []
    i, n = 0, len(src)

    while i < n:
        ch = src[i]

        if ch.isspace():
            i += 1
            continue

        if ch.isdigit() or (ch == "." and i + 1 < n and src[i + 1].isdigit()):
            start = i
            seen_dot = False
            seen_exp = False
            while i < n:
                c = src[i]
                if c.isdigit():
                    i += 1
                elif c == "." and not seen_dot and not seen_exp:
                    seen_dot = True
                    i += 1
                elif c in "eE" and not seen_exp and i + 1 < n and (src[i + 1].isdigit() or src[i + 1] in "+-"):
                    seen_exp = True
                    i += 2
                else:
                    break
            tokens.append(_Token("NUMBER", float(src[start:i]), start))
            continue

        if ch in "'\"":
            quote = ch
            i += 1
            start = i
            buf: list[str] = []
            while i < n and src[i] != quote:
                if src[i] == "\\" and i + 1 < n:
                    buf.append(src[i + 1])
                    i += 2
                else:
                    buf.append(src[i])
                    i += 1
            if i >= n:
                raise ExpressionError(f"Unterminated string literal at position {start}")
            i += 1
            tokens.append(_Token("STRING", "".join(buf), start))
            continue

        if ch.isalpha() or ch == "_":
            start = i
            while i < n and (src[i].isalnum() or src[i] == "_"):
                i += 1
            word = src[start:i]
            kind = "KEYWORD" if word.lower() in _KEYWORDS else "NAME"
            tokens.append(_Token(kind, word.lower() if kind == "KEYWORD" else word, start))
            continue

        for punct in _PUNCT:
            if src.startswith(punct, i):
                tokens.append(_Token("PUNCT", punct, i))
                i += len(punct)
                break
        else:
            raise ExpressionError(f"Unexpected character {ch!r} at position {i}")

    tokens.append(_Token("END", None, n))
    return tokens


# ─────────────────────────── AST ───────────────────────────


class _Node:
    __slots__ = ()


@dataclass(frozen=True)
class _Literal(_Node):
    value: Any


@dataclass(frozen=True)
class _Ref(_Node):
    """A dotted / indexed reference such as `standard.weight_mg` or `areas[2]`."""

    parts: tuple[Any, ...]  # str for attribute access, _Node for computed index


@dataclass(frozen=True)
class _Unary(_Node):
    op: str
    operand: _Node


@dataclass(frozen=True)
class _Binary(_Node):
    op: str
    left: _Node
    right: _Node


@dataclass(frozen=True)
class _Call(_Node):
    name: str
    args: tuple[_Node, ...]


@dataclass(frozen=True)
class _ListNode(_Node):
    items: tuple[_Node, ...]


# ─────────────────────────── Parser ───────────────────────────


class _Parser:
    def __init__(self, tokens: Sequence[_Token]) -> None:
        self._tokens = tokens
        self._i = 0

    @property
    def _cur(self) -> _Token:
        return self._tokens[self._i]

    def _advance(self) -> _Token:
        tok = self._tokens[self._i]
        self._i += 1
        return tok

    def _accept(self, kind: str, value: Any = None) -> _Token | None:
        tok = self._cur
        if tok.kind == kind and (value is None or tok.value == value):
            return self._advance()
        return None

    def _expect(self, kind: str, value: Any = None) -> _Token:
        tok = self._accept(kind, value)
        if tok is None:
            expected = value or kind
            raise ExpressionError(
                f"Expected {expected!r} at position {self._cur.pos}, got {self._cur.value!r}"
            )
        return tok

    def parse(self) -> _Node:
        node = self._or_expr()
        if self._cur.kind != "END":
            raise ExpressionError(
                f"Unexpected trailing input {self._cur.value!r} at position {self._cur.pos}"
            )
        return node

    def _or_expr(self) -> _Node:
        node = self._and_expr()
        while self._accept("KEYWORD", "or"):
            node = _Binary("or", node, self._and_expr())
        return node

    def _and_expr(self) -> _Node:
        node = self._cmp_expr()
        while self._accept("KEYWORD", "and"):
            node = _Binary("and", node, self._cmp_expr())
        return node

    def _cmp_expr(self) -> _Node:
        node = self._add_expr()
        for op in ("<=", ">=", "<>", "!=", "==", "<", ">", "="):
            if self._accept("PUNCT", op):
                return _Binary(op, node, self._add_expr())
        return node

    def _add_expr(self) -> _Node:
        node = self._mul_expr()
        while True:
            if self._accept("PUNCT", "+"):
                node = _Binary("+", node, self._mul_expr())
            elif self._accept("PUNCT", "-"):
                node = _Binary("-", node, self._mul_expr())
            else:
                return node

    def _mul_expr(self) -> _Node:
        node = self._unary()
        while True:
            if self._accept("PUNCT", "*"):
                node = _Binary("*", node, self._unary())
            elif self._accept("PUNCT", "/"):
                node = _Binary("/", node, self._unary())
            else:
                return node

    def _unary(self) -> _Node:
        if self._accept("PUNCT", "-"):
            return _Unary("-", self._unary())
        if self._accept("PUNCT", "+"):
            return self._unary()
        if self._accept("KEYWORD", "not"):
            return _Unary("not", self._unary())
        return self._power()

    def _power(self) -> _Node:
        node = self._primary()
        if self._accept("PUNCT", "^"):
            return _Binary("^", node, self._unary())
        return node

    def _primary(self) -> _Node:
        tok = self._cur

        if tok.kind == "NUMBER":
            self._advance()
            return _Literal(tok.value)

        if tok.kind == "STRING":
            self._advance()
            return _Literal(tok.value)

        if tok.kind == "KEYWORD" and tok.value in ("true", "false"):
            self._advance()
            return _Literal(tok.value == "true")

        if self._accept("PUNCT", "("):
            node = self._or_expr()
            self._expect("PUNCT", ")")
            return node

        if self._accept("PUNCT", "["):
            items: list[_Node] = []
            if not self._accept("PUNCT", "]"):
                items.append(self._or_expr())
                while self._accept("PUNCT", ","):
                    items.append(self._or_expr())
                self._expect("PUNCT", "]")
            return _ListNode(tuple(items))

        if tok.kind == "NAME":
            self._advance()
            name = tok.value
            # Function call
            if self._cur.kind == "PUNCT" and self._cur.value == "(":
                self._advance()
                args: list[_Node] = []
                if not self._accept("PUNCT", ")"):
                    args.append(self._or_expr())
                    while self._accept("PUNCT", ","):
                        args.append(self._or_expr())
                    self._expect("PUNCT", ")")
                return _Call(name.lower(), tuple(args))
            # Reference with optional dotted / indexed path
            parts: list[Any] = [name]
            while True:
                if self._accept("PUNCT", "."):
                    parts.append(self._expect("NAME").value)
                elif self._accept("PUNCT", "["):
                    parts.append(self._or_expr())
                    self._expect("PUNCT", "]")
                else:
                    break
            return _Ref(tuple(parts))

        raise ExpressionError(f"Unexpected token {tok.value!r} at position {tok.pos}")


# ─────────────────────────── Evaluator ───────────────────────────


def _is_blank(value: Any) -> bool:
    """Blank in the Excel sense: EMPTY, None, or an empty/whitespace string."""
    if value is EMPTY or value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _numeric(values: Iterable[Any]) -> list[float]:
    """Coerce an iterable to the numbers in it, skipping blanks — matches the
    source sheets' blank-tolerant `AVERAGE`/`STDEV` over padded ranges."""
    out: list[float] = []
    for v in _flatten(values):
        if _is_blank(v):
            continue
        if isinstance(v, bool):
            out.append(1.0 if v else 0.0)
        elif isinstance(v, (int, float)):
            out.append(float(v))
        # Non-numeric strings are ignored, as Excel's AVERAGE does.
    return out


def _flatten(values: Any) -> list[Any]:
    out: list[Any] = []
    if isinstance(values, (list, tuple)):
        for v in values:
            out.extend(_flatten(v))
    else:
        out.append(values)
    return out


def _as_number(value: Any, ctx: str) -> float | Empty:
    if _is_blank(value):
        return EMPTY
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raise ExpressionError(f"{ctx} expected a number, got {value!r}")


class _Evaluator:
    def __init__(self, context: dict[str, Any]) -> None:
        self._ctx = context

    def eval(self, node: _Node) -> Any:
        if isinstance(node, _Literal):
            return node.value
        if isinstance(node, _ListNode):
            return [self.eval(item) for item in node.items]
        if isinstance(node, _Ref):
            return self._resolve(node)
        if isinstance(node, _Unary):
            return self._unary(node)
        if isinstance(node, _Binary):
            return self._binary(node)
        if isinstance(node, _Call):
            return self._call(node)
        raise ExpressionError(f"Unsupported node {node!r}")

    def _resolve(self, node: _Ref) -> Any:
        current: Any = self._ctx
        for part in node.parts:
            key = part if isinstance(part, str) else self.eval(part)
            if _is_blank(current):
                return EMPTY
            if isinstance(current, dict):
                if key not in current:
                    return EMPTY
                current = current[key]
            elif isinstance(current, (list, tuple)):
                idx = _as_number(key, "List index")
                if idx is EMPTY:
                    return EMPTY
                i = int(idx)
                if i < 0 or i >= len(current):
                    return EMPTY
                current = current[i]
            else:
                current = getattr(current, str(key), EMPTY)
        return current

    def _unary(self, node: _Unary) -> Any:
        value = self.eval(node.operand)
        if node.op == "not":
            return not bool(value)
        num = _as_number(value, "Unary minus")
        if num is EMPTY:
            return EMPTY
        return -num if node.op == "-" else num

    def _binary(self, node: _Binary) -> Any:
        op = node.op

        if op == "and":
            return bool(self.eval(node.left)) and bool(self.eval(node.right))
        if op == "or":
            return bool(self.eval(node.left)) or bool(self.eval(node.right))

        left = self.eval(node.left)
        right = self.eval(node.right)

        if op in ("=", "==", "<>", "!="):
            equal = self._loose_equal(left, right)
            return equal if op in ("=", "==") else not equal

        ln = _as_number(left, f"Operator {op!r}")
        rn = _as_number(right, f"Operator {op!r}")
        if ln is EMPTY or rn is EMPTY:
            return EMPTY

        if op == "+":
            return ln + rn
        if op == "-":
            return ln - rn
        if op == "*":
            return ln * rn
        if op == "/":
            # Excel-compatible: division by zero yields blank, not an exception.
            return EMPTY if rn == 0 else ln / rn
        if op == "^":
            try:
                return float(ln) ** float(rn)
            except (OverflowError, ValueError):
                return EMPTY
        if op == "<":
            return ln < rn
        if op == "<=":
            return ln <= rn
        if op == ">":
            return ln > rn
        if op == ">=":
            return ln >= rn

        raise ExpressionError(f"Unsupported operator {op!r}")

    @staticmethod
    def _loose_equal(left: Any, right: Any) -> bool:
        if _is_blank(left) and _is_blank(right):
            return True
        if _is_blank(left) or _is_blank(right):
            return False
        if isinstance(left, str) or isinstance(right, str):
            return str(left).strip().lower() == str(right).strip().lower()
        try:
            return float(left) == float(right)
        except (TypeError, ValueError):
            return left == right

    def _call(self, node: _Call) -> Any:
        fn = _FUNCTIONS.get(node.name)
        if fn is None:
            raise ExpressionError(f"Unknown function {node.name!r}")
        # `if` is lazy so an erroring branch that isn't taken cannot poison the result.
        if node.name == "if":
            if len(node.args) not in (2, 3):
                raise ExpressionError("if() takes 2 or 3 arguments")
            condition = self.eval(node.args[0])
            if bool(condition) and condition is not EMPTY:
                return self.eval(node.args[1])
            return self.eval(node.args[2]) if len(node.args) == 3 else EMPTY
        args = [self.eval(a) for a in node.args]
        return fn(args)


# ─────────────────────────── Built-in functions ───────────────────────────


def _f_mean(args: list[Any]) -> Any:
    nums = _numeric(args)
    return sum(nums) / len(nums) if nums else EMPTY


def _f_sum(args: list[Any]) -> Any:
    """
    Sum, with Excel's semantics for an empty range: 0, not blank.

    This matters at the first row of a dissolution sequence, where
    `sum(prior.correction)` has nothing to add up — the release value must be
    the uncorrected value, not blank. (`mean` differs: the average of an empty
    range is genuinely undefined, so it returns blank.)
    """
    return sum(_numeric(args))


def _f_count(args: list[Any]) -> Any:
    return float(len(_numeric(args)))


def _f_sd(args: list[Any]) -> Any:
    """Sample standard deviation (n-1), matching Excel's STDEV."""
    nums = _numeric(args)
    if len(nums) < 2:
        return EMPTY
    mean = sum(nums) / len(nums)
    variance = sum((x - mean) ** 2 for x in nums) / (len(nums) - 1)
    return math.sqrt(variance)


def _f_rsd(args: list[Any]) -> Any:
    """Relative standard deviation as a percentage: sd / mean * 100."""
    nums = _numeric(args)
    if len(nums) < 2:
        return EMPTY
    mean = sum(nums) / len(nums)
    if mean == 0:
        return EMPTY
    variance = sum((x - mean) ** 2 for x in nums) / (len(nums) - 1)
    return math.sqrt(variance) / mean * 100.0


def _f_min(args: list[Any]) -> Any:
    nums = _numeric(args)
    return min(nums) if nums else EMPTY


def _f_max(args: list[Any]) -> Any:
    nums = _numeric(args)
    return max(nums) if nums else EMPTY


def _digits(args: list[Any], index: int) -> int:
    if len(args) <= index:
        return 0
    value = _as_number(args[index], "Rounding digits")
    return 0 if value is EMPTY else int(value)


def _f_round(args: list[Any]) -> Any:
    if not args:
        raise ExpressionError("round() requires at least 1 argument")
    value = _as_number(args[0], "round()")
    if value is EMPTY:
        return EMPTY
    digits = _digits(args, 1)
    # Excel rounds half away from zero; Python's round() is banker's rounding.
    factor = 10.0**digits
    scaled = value * factor
    rounded = math.floor(abs(scaled) + 0.5) * (1 if scaled >= 0 else -1)
    return rounded / factor


def _f_trunc(args: list[Any]) -> Any:
    if not args:
        raise ExpressionError("trunc() requires at least 1 argument")
    value = _as_number(args[0], "trunc()")
    if value is EMPTY:
        return EMPTY
    digits = _digits(args, 1)
    factor = 10.0**digits
    return math.trunc(value * factor) / factor


def _f_abs(args: list[Any]) -> Any:
    value = _as_number(args[0], "abs()") if args else EMPTY
    return EMPTY if value is EMPTY else abs(value)


def _f_sqrt(args: list[Any]) -> Any:
    value = _as_number(args[0], "sqrt()") if args else EMPTY
    if value is EMPTY or value < 0:
        return EMPTY
    return math.sqrt(value)


def _f_ln(args: list[Any]) -> Any:
    value = _as_number(args[0], "ln()") if args else EMPTY
    if value is EMPTY or value <= 0:
        return EMPTY
    return math.log(value)


def _f_log10(args: list[Any]) -> Any:
    value = _as_number(args[0], "log10()") if args else EMPTY
    if value is EMPTY or value <= 0:
        return EMPTY
    return math.log10(value)


def _f_exp(args: list[Any]) -> Any:
    value = _as_number(args[0], "exp()") if args else EMPTY
    if value is EMPTY:
        return EMPTY
    try:
        return math.exp(value)
    except OverflowError:
        return EMPTY


def _xy_pairs(args: list[Any]) -> tuple[list[float], list[float]] | None:
    """Align two series pairwise, dropping any pair where either side is blank."""
    if len(args) < 2:
        return None
    ys_raw = _flatten(args[0])
    xs_raw = _flatten(args[1])
    xs: list[float] = []
    ys: list[float] = []
    for y, x in zip(ys_raw, xs_raw):
        if _is_blank(y) or _is_blank(x):
            continue
        if isinstance(y, (int, float)) and isinstance(x, (int, float)):
            ys.append(float(y))
            xs.append(float(x))
    if len(xs) < 2:
        return None
    return xs, ys


def _f_slope(args: list[Any]) -> Any:
    """Least-squares slope of y on x. Argument order matches Excel: SLOPE(ys, xs)."""
    pair = _xy_pairs(args)
    if pair is None:
        return EMPTY
    xs, ys = pair
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return EMPTY
    return sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n)) / denom


def _f_intercept(args: list[Any]) -> Any:
    pair = _xy_pairs(args)
    if pair is None:
        return EMPTY
    xs, ys = pair
    slope = _f_slope(args)
    if slope is EMPTY:
        return EMPTY
    return sum(ys) / len(ys) - slope * (sum(xs) / len(xs))


def _f_correl(args: list[Any]) -> Any:
    pair = _xy_pairs(args)
    if pair is None:
        return EMPTY
    xs, ys = pair
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return EMPTY
    return cov / math.sqrt(var_x * var_y)


def _f_blank(args: list[Any]) -> Any:
    return EMPTY


def _f_isblank(args: list[Any]) -> Any:
    return _is_blank(args[0]) if args else True


def _f_coalesce(args: list[Any]) -> Any:
    """First non-blank argument, or EMPTY."""
    for value in args:
        if not _is_blank(value):
            return value
    return EMPTY


def _f_pool(args: list[Any]) -> Any:
    """
    Flatten several ranges into one series.

    This is the bracketing-standard pattern: block *k*'s statistics are computed
    over the initial standard replicates pooled with bracketing blocks 1..k, so
    templates express it as e.g. `rsd(pool(std_areas, bkt1, bkt2))`.
    """
    return [v for v in _flatten(args) if not _is_blank(v)]


def _f_cumsum(args: list[Any]) -> Any:
    """Running total of a series, blanks treated as zero. Used by the
    dissolution cumulative-release correction chains."""
    total = 0.0
    out: list[float] = []
    for v in _flatten(args):
        num = 0.0 if _is_blank(v) else _as_number(v, "cumsum()")
        total += 0.0 if num is EMPTY else num
        out.append(total)
    return out


_FUNCTIONS: dict[str, Callable[[list[Any]], Any]] = {
    "mean": _f_mean,
    "average": _f_mean,
    "sum": _f_sum,
    "count": _f_count,
    "sd": _f_sd,
    "stdev": _f_sd,
    "rsd": _f_rsd,
    "min": _f_min,
    "max": _f_max,
    "round": _f_round,
    "trunc": _f_trunc,
    "abs": _f_abs,
    "sqrt": _f_sqrt,
    "ln": _f_ln,
    "log10": _f_log10,
    "exp": _f_exp,
    "slope": _f_slope,
    "intercept": _f_intercept,
    "correl": _f_correl,
    "blank": _f_blank,
    "isblank": _f_isblank,
    "coalesce": _f_coalesce,
    "pool": _f_pool,
    "cumsum": _f_cumsum,
    "if": _f_blank,  # handled lazily in _Evaluator._call; entry marks it as known
}


# ─────────────────────────── Public API ───────────────────────────

_PARSE_CACHE: dict[str, _Node] = {}


def _parse(expression: str) -> _Node:
    cached = _PARSE_CACHE.get(expression)
    if cached is None:
        cached = _Parser(_tokenize(expression)).parse()
        _PARSE_CACHE[expression] = cached
    return cached


def evaluate(expression: str, context: dict[str, Any] | None = None) -> Any:
    """
    Evaluate a template formula against `context`.

    Returns a float, bool, str, list, or `EMPTY`. Raises `ExpressionError` only
    for malformed expressions or unknown functions — missing data and division
    by zero yield `EMPTY`, matching the source sheets' `IFERROR(..., "")`.
    """
    if not expression or not expression.strip():
        return EMPTY
    return _Evaluator(context or {}).eval(_parse(expression))


def referenced_names(expression: str) -> set[str]:
    """
    The root identifiers an expression depends on.

    Used to build the dependency graph so calculated fields evaluate in the
    right order and circular references can be detected.
    """
    if not expression or not expression.strip():
        return set()

    names: set[str] = set()

    def walk(node: _Node) -> None:
        if isinstance(node, _Ref):
            root = node.parts[0]
            if isinstance(root, str):
                names.add(root)
            for part in node.parts[1:]:
                if isinstance(part, _Node):
                    walk(part)
        elif isinstance(node, _Unary):
            walk(node.operand)
        elif isinstance(node, _Binary):
            walk(node.left)
            walk(node.right)
        elif isinstance(node, _Call):
            for arg in node.args:
                walk(arg)
        elif isinstance(node, _ListNode):
            for item in node.items:
                walk(item)

    walk(_parse(expression))
    return names


def referenced_paths(expression: str) -> set[tuple[str, ...]]:
    """
    The dotted reference paths an expression depends on, e.g. `{("stats", "mean_std")}`.

    `referenced_names` only reports root identifiers, which forces the dependency
    graph to assume a reference to `group.field` depends on *everything* calculated
    in that group. That over-approximation reports circular references that do not
    exist — a field summing an input column (`sum(peaks.area)`) appears to depend on
    calculated fields in `peaks` that in turn depend on it.

    Returning the leading string chain lets the caller resolve dependencies to the
    exact field. A path is truncated at the first non-name part, so `peaks.area[0]`
    yields `("peaks", "area")` — indexing does not change what is depended upon.
    """
    if not expression or not expression.strip():
        return set()

    paths: set[tuple[str, ...]] = set()

    def walk(node: _Node) -> None:
        if isinstance(node, _Ref):
            chain: list[str] = []
            for part in node.parts:
                if isinstance(part, str):
                    chain.append(part)
                else:
                    #  A computed index; walk it for its own references and stop
                    #  extending this path.
                    if isinstance(part, _Node):
                        walk(part)
                    break
            if chain:
                paths.add(tuple(chain))
        elif isinstance(node, _Unary):
            walk(node.operand)
        elif isinstance(node, _Binary):
            walk(node.left)
            walk(node.right)
        elif isinstance(node, _Call):
            for arg in node.args:
                walk(arg)
        elif isinstance(node, _ListNode):
            for item in node.items:
                walk(item)

    walk(_parse(expression))
    return paths
