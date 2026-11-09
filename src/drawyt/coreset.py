"""Coreset selection (pruning level 2): k-center greedy coverage.

Greedily pick the frame farthest from everything already picked. The
result covers the visual space of the corpus with a bounded number of
points, instead of over-representing whatever scene is most common.
"""

from __future__ import annotations

import numpy as np


def kcenter_greedy(embeddings: np.ndarray, budget: int, seed_index: int = 0) -> list[int]:
    """Indices of up to `budget` points forming a k-center cover.

    Deterministic: the first pick is `seed_index` (callers pass the point
    closest to the corpus mean for a stable, representative start).
    """
    n = len(embeddings)
    if n == 0 or budget <= 0:
        return []
    budget = min(budget, n)
    chosen = [seed_index]
    # distance from each point to the nearest chosen point
    diff = embeddings - embeddings[seed_index]
    min_dist = np.sqrt((diff * diff).sum(axis=1))
    min_dist[seed_index] = -1.0  # never re-pick
    while len(chosen) < budget:
        nxt = int(np.argmax(min_dist))
        chosen.append(nxt)
        diff = embeddings - embeddings[nxt]
        dist = np.sqrt((diff * diff).sum(axis=1))
        min_dist = np.minimum(min_dist, dist)
        min_dist[nxt] = -1.0
    return chosen


def assign_clusters(embeddings: np.ndarray, centers: list[int]) -> np.ndarray:
    """Assign each point to its nearest center; returns cluster id per point."""
    if not centers:
        return np.full(len(embeddings), -1)
    center_vecs = embeddings[centers]
    # (n, k) distances
    dists = np.sqrt(((embeddings[:, None, :] - center_vecs[None, :, :]) ** 2).sum(axis=2))
    return np.argmin(dists, axis=1)


def medoid_index(embeddings: np.ndarray) -> int:
    """Index of the point closest to the corpus mean (a stable seed)."""
    mean = embeddings.mean(axis=0)
    dists = np.sqrt(((embeddings - mean) ** 2).sum(axis=1))
    return int(np.argmin(dists))
