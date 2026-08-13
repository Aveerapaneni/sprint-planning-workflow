"""US-7: adjust team velocity for OOO/resource availability during the sprint window."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Resource:
    team_id: str
    engineer_name: str
    ooo_start: Optional[str] = None
    ooo_end: Optional[str] = None


@dataclass
class VelocityAdjustment:
    baseline_velocity: int
    adjusted_velocity: int
    total_engineers: int
    ooo_engineers: list[str]
    data_missing: bool  # True if no resource records exist for this team


def _parse(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _is_ooo_during_window(resource: Resource, window_start: date, window_end: date) -> bool:
    ooo_start = _parse(resource.ooo_start)
    ooo_end = _parse(resource.ooo_end)
    if ooo_start is None or ooo_end is None:
        return False
    return ooo_start <= window_end and ooo_end >= window_start


def compute_adjusted_velocity(
    team_id: str,
    baseline_velocity: int,
    resources: list[Resource],
    window_start: date,
    window_end: date,
) -> VelocityAdjustment:
    """Reduce baseline velocity proportionally for engineers OOO during the sprint
    window, split evenly across the team's headcount: each OOO engineer loses
    their 1/N share of velocity. The final adjusted number is floored, so
    capacity is never overestimated. Missing/absent resource data for a team
    falls back to full baseline velocity, flagged via `data_missing`, rather
    than guessing (PRD Section 7).
    """
    team_resources = [r for r in resources if r.team_id == team_id]
    total = len(team_resources)

    if total == 0:
        return VelocityAdjustment(
            baseline_velocity=baseline_velocity,
            adjusted_velocity=baseline_velocity,
            total_engineers=0,
            ooo_engineers=[],
            data_missing=True,
        )

    ooo = [r for r in team_resources if _is_ooo_during_window(r, window_start, window_end)]
    available = total - len(ooo)
    adjusted = math.floor(baseline_velocity * available / total)

    return VelocityAdjustment(
        baseline_velocity=baseline_velocity,
        adjusted_velocity=adjusted,
        total_engineers=total,
        ooo_engineers=[r.engineer_name for r in ooo],
        data_missing=False,
    )
