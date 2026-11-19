"""Deterministic conveyor physics, independent of ADS and UI.

A sorting arm transfers rejected parcels at x=DIVERTER_X onto a perpendicular
belt. Reject parcels then move along y (downwards), not diagonally along x.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass

ENTRY_X = 0.26
EXIT_X = 0.86
DIVERTER_X = 0.66
REJECT_SENSOR_Y = 0.62
BELT_SPEED = 0.19
REJECT_SPEED = 0.35
PACKAGE_WIDTH = 0.070
REJECT_PACKAGE_WIDTH = 0.13  # along perpendicular belt (normalized)
MAX_QUEUE = 24


@dataclass
class Package:
    id: int
    kind: str
    x: float = 0.055
    lane: str = 'main'
    y: float = 0.0  # reject belt travel, zero at transfer; increases downwards

    def as_dict(self) -> dict:
        return {'id': self.id, 'kind': self.kind, 'x': round(self.x, 5),
                'lane': self.lane, 'y': round(self.y, 5)}


class ConveyorWorld:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.packages: list[Package] = []
        self.queue: deque[str] = deque()
        self.next_id = 1
        self.normal_count = 0
        self.reject_count = 0
        self.auto_feed = False
        self._auto_kind = 'standard'
        self._auto_timer = 0.0

    def enqueue(self, kind: str) -> None:
        if kind not in {'standard', 'reject'}:
            raise ValueError('Onbekend pakkettype; gebruik standard of reject.')
        if len(self.queue) >= MAX_QUEUE:
            raise ValueError('De wachtrij is vol (maximaal 24 pakketten).')
        self.queue.append(kind)

    def set_auto_feed(self, enabled: bool) -> None:
        self.auto_feed = bool(enabled)
        self._auto_timer = 0.0

    @staticmethod
    def _overlaps(package: Package, sensor_x: float) -> bool:
        return package.lane == 'main' and abs(package.x - sensor_x) <= PACKAGE_WIDTH / 2

    def inputs(self) -> dict[str, bool]:
        entry_packages = [p for p in self.packages if self._overlaps(p, ENTRY_X)]
        return {
            'sensor_entry': bool(entry_packages),
            'sensor_exit': any(self._overlaps(p, EXIT_X) for p in self.packages),
            'reject_type': any(p.kind == 'reject' for p in entry_packages),
            'sensor_reject': any(p.lane == 'reject' and
                                 abs(p.y - REJECT_SENSOR_Y) <= REJECT_PACKAGE_WIDTH / 2
                                 for p in self.packages),
        }

    def step(self, dt: float, motor: bool, diverter: bool) -> None:
        dt = max(0.0, min(float(dt), 0.10))
        if self.auto_feed:
            self._auto_timer += dt
            if self._auto_timer >= 2.3 and not self.queue and not self.packages:
                self.queue.append(self._auto_kind)
                self._auto_kind = 'reject' if self._auto_kind == 'standard' else 'standard'
                self._auto_timer = 0.0
        # Preserve the introductory single-package-at-a-time setup.
        if not self.packages and self.queue:
            self.packages.append(Package(self.next_id, self.queue.popleft()))
            self.next_id += 1
        # The reject belt is mechanically coupled to the main belt in this
        # introductory exercise: same existing PLC motor output runs both.
        if not motor:
            return
        for package in self.packages:
            if package.lane == 'reject':
                package.y += REJECT_SPEED * dt
            else:
                old_x = package.x
                package.x += BELT_SPEED * dt
                if old_x < DIVERTER_X <= package.x and diverter:
                    package.x = DIVERTER_X
                    package.y = 0.0
                    package.lane = 'reject'
        remaining = []
        for package in self.packages:
            if package.lane == 'reject' and package.y >= 1.06:
                self.reject_count += 1
            elif package.lane == 'main' and package.x >= 1.03:
                self.normal_count += 1
            else:
                remaining.append(package)
        self.packages = remaining

    def snapshot(self) -> dict:
        return {
            'packages': [p.as_dict() for p in self.packages],
            'queue': list(self.queue), 'queue_count': len(self.queue),
            'normal_count': self.normal_count, 'reject_count': self.reject_count,
            'auto_feed': self.auto_feed, 'speed': BELT_SPEED,
            'reject_speed': REJECT_SPEED, 'inputs': self.inputs(),
        }
