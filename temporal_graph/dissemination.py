"""Information spreading over a temporal graph, round by round.

Each instant is a round. In flooding every informed node tells all its
neighbours; in token forwarding every node broadcasts a single token it
knows, chosen without seeing the round's topology (the online model).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import (
    Callable,
    Dict,
    FrozenSet,
    Hashable,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Union,
)

from .graph import TemporalGraph
from .journeys import _check_nodes, _default_start, foremost_search

Token = Hashable
Policy = Callable[[str, FrozenSet[Token], int], Optional[Token]]


def flooding_times(
    graph: TemporalGraph, sources: Iterable[str], start: Optional[int] = None
) -> Dict[str, int]:
    """Instant at which each node first learns a message held by ``sources``.

    Equivalent to a multi-source foremost search; uninformed nodes are absent.
    """
    origins = list(sources)
    _check_nodes(graph, *origins)
    begin = _default_start(graph, start, strict=True)
    arrival, _ = foremost_search(graph, {s: begin for s in origins})
    return arrival


@dataclass(frozen=True)
class DisseminationResult:
    completion: Optional[int]                 # first round after which all know all
    knowledge: Dict[str, FrozenSet[Token]]    # what each node knows at the end
    progress: List[Tuple[int, int]]           # (round, total node-token pairs known)


def _round_robin(node: str, known: FrozenSet[Token], round_: int) -> Optional[Token]:
    if not known:
        return None
    ordered = sorted(known, key=repr)
    return ordered[round_ % len(ordered)]


def k_token_dissemination(
    graph: TemporalGraph,
    tokens: Mapping[str, Iterable[Token]],
    policy: Union[str, Policy] = "round_robin",
    start: Optional[int] = None,
    rounds: Optional[int] = None,
    seed: Optional[int] = None,
) -> DisseminationResult:
    """Simulate token forwarding until every node knows every token.

    ``tokens`` gives the initial tokens of each node. ``policy`` chooses what
    a node broadcasts: ``"round_robin"`` (cycles through what it knows),
    ``"random"`` (uniform, reproducible with ``seed``) or a callable
    ``policy(node, known, round) -> token``. Rounds run from ``start + 1`` up
    to the last recorded instant, or for ``rounds`` rounds if given.
    """
    _check_nodes(graph, *tokens)
    rng = random.Random(seed)
    if policy == "round_robin":
        choose: Policy = _round_robin
    elif policy == "random":
        def choose(node: str, known: FrozenSet[Token], round_: int) -> Optional[Token]:
            return rng.choice(sorted(known, key=repr)) if known else None
    elif callable(policy):
        choose = policy
    else:
        raise ValueError(f"Unknown policy {policy!r}")

    knowledge: Dict[str, FrozenSet[Token]] = {
        n: frozenset(tokens.get(n, ())) for n in graph.nodes
    }
    everything: FrozenSet[Token] = frozenset().union(*knowledge.values())
    begin = _default_start(graph, start, strict=True)
    timesteps = graph.timesteps
    last = begin + rounds if rounds is not None else (timesteps[-1] if timesteps else begin)

    def total() -> int:
        return sum(len(known) for known in knowledge.values())

    progress: List[Tuple[int, int]] = [(begin, total())]
    if all(known == everything for known in knowledge.values()):
        return DisseminationResult(begin, knowledge, progress)
    for t in range(begin + 1, last + 1):
        sent = {node: choose(node, known, t) for node, known in knowledge.items()}
        try:
            edges = graph.edges_at(t)
        except KeyError:
            edges = []
        received: Dict[str, Set[Token]] = {}
        for edge in edges:
            pairs = [(edge.u, edge.v)] if edge.directed else [(edge.u, edge.v), (edge.v, edge.u)]
            for a, b in pairs:
                token = sent[a]
                if token is not None:
                    received.setdefault(b, set()).add(token)
        for node, new in received.items():
            knowledge[node] = knowledge[node] | new
        progress.append((t, total()))
        if all(known == everything for known in knowledge.values()):
            return DisseminationResult(t, knowledge, progress)
    return DisseminationResult(None, knowledge, progress)


def harmonic_potential(k: int) -> float:
    """H_k = 1 + 1/2 + ... + 1/k: the per-node potential at the end of the
    k-token lower-bound argument, which grows as Θ(log k)."""
    if k < 1:
        raise ValueError("k must be >= 1")
    return sum(1 / j for j in range(1, k + 1))
