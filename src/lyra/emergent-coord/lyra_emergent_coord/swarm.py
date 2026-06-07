"""Swarm intelligence patterns for emergent coordination.

Implements stigmergy, ant colony optimization, particle swarm optimization,
bee algorithm, and flocking/boids for agent coordination.
"""

from __future__ import annotations

import logging
import math
import random
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass
class Pheromone:
    """A pheromone trail in stigmergy-based coordination.

    Attributes:
        location: Position or identifier where the pheromone is deposited.
        intensity: Current strength of the pheromone.
        decay_rate: How quickly the pheromone evaporates.
        deposited_by: Which agent deposited it.
        deposited_at: When it was deposited.
    """

    location: str
    intensity: float = 1.0
    decay_rate: float = 0.1
    deposited_by: str = ""
    deposited_at: float = field(default_factory=_now)

    def decay(self, elapsed: float) -> None:
        """Evaporate pheromone over time."""
        self.intensity *= math.exp(-self.decay_rate * elapsed)

    @property
    def is_evaporated(self) -> bool:
        return self.intensity < 0.01


@dataclass
class Particle:
    """A particle in particle swarm optimization.

    Attributes:
        particle_id: Unique particle identifier.
        position: Current position vector in search space.
        velocity: Current velocity vector.
        best_position: Personal best position found.
        best_score: Score at personal best position.
    """

    particle_id: str = field(default_factory=_new_id)
    position: list[float] = field(default_factory=list)
    velocity: list[float] = field(default_factory=list)
    best_position: list[float] | None = None
    best_score: float = -float("inf")

    @property
    def dimension(self) -> int:
        return len(self.position)


@dataclass
class Boid:
    """A boid in a flocking simulation.

    Attributes:
        boid_id: Unique boid identifier.
        position: Current 2D position.
        velocity: Current velocity vector.
        max_speed: Maximum movement speed.
        perception_radius: How far the boid can see.
    """

    boid_id: str = field(default_factory=_new_id)
    position: tuple[float, float] = (0.0, 0.0)
    velocity: tuple[float, float] = (0.0, 0.0)
    max_speed: float = 1.0
    perception_radius: float = 5.0


@dataclass
class FoodSource:
    """A food source in the bee algorithm.

    Attributes:
        source_id: Unique source identifier.
        location: Position of the food source.
        quality: Quality/rating of the source (higher is better).
        trials_remaining: Tries remaining before abandonment.
    """

    source_id: str = field(default_factory=_new_id)
    location: str = ""
    quality: float = 0.0
    trials_remaining: int = 10


# ---------------------------------------------------------------------------
# Stigmergy System
# ---------------------------------------------------------------------------


class StigmergySystem:
    """Stigmergy-based indirect coordination through shared environment.

    Agents deposit pheromone trails that influence other agents' behavior,
    enabling decentralized, scalable coordination without direct communication.
    """

    def __init__(
        self,
        *,
        default_decay_rate: float = 0.1,
        evaporation_interval: float = 1.0,
    ) -> None:
        self._default_decay_rate = default_decay_rate
        self._evaporation_interval = evaporation_interval
        self._pheromones: dict[str, list[Pheromone]] = defaultdict(list)
        self._last_evaporation: float = _now()

    def deposit(
        self,
        location: str,
        agent_id: str,
        intensity: float = 1.0,
        decay_rate: float | None = None,
    ) -> Pheromone:
        """Deposit a pheromone at a location."""
        self._evaporate()
        pheromone = Pheromone(
            location=location,
            intensity=intensity,
            decay_rate=decay_rate or self._default_decay_rate,
            deposited_by=agent_id,
        )
        self._pheromones[location].append(pheromone)
        return pheromone

    def get_trail_strength(self, location: str) -> float:
        """Get the cumulative pheromone intensity at a location."""
        self._evaporate()
        trails = self._pheromones.get(location, [])
        return sum(p.intensity for p in trails if not p.is_evaporated)

    def get_best_location(self) -> str | None:
        """Find the location with the strongest pheromone trail."""
        if not self._pheromones:
            return None

        best_loc = None
        best_strength = -float("inf")
        for loc in self._pheromones:
            strength = self.get_trail_strength(loc)
            if strength > best_strength:
                best_strength = strength
                best_loc = loc
        return best_loc

    def reinforce(self, location: str, bonus: float = 0.5) -> None:
        """Reinforce pheromone trails at a location (positive feedback)."""
        self._evaporate()
        for pheromone in self._pheromones.get(location, []):
            pheromone.intensity = min(10.0, pheromone.intensity + bonus)

    def _evaporate(self) -> None:
        """Evaporate all pheromones based on elapsed time."""
        now = _now()
        elapsed = now - self._last_evaporation
        if elapsed < self._evaporation_interval:
            return

        for loc in list(self._pheromones.keys()):
            for pheromone in self._pheromones[loc]:
                pheromone.decay(elapsed)
            # Remove evaporated trails
            self._pheromones[loc] = [p for p in self._pheromones[loc] if not p.is_evaporated]
            if not self._pheromones[loc]:
                del self._pheromones[loc]

        self._last_evaporation = now

    def snapshot(self) -> dict[str, Any]:
        """Return current state snapshot."""
        self._evaporate()
        return {
            "active_locations": len(self._pheromones),
            "trails": {
                loc: sum(p.intensity for p in trails) for loc, trails in self._pheromones.items()
            },
        }


# ---------------------------------------------------------------------------
# Ant Colony Optimization
# ---------------------------------------------------------------------------


class AntColonyOptimizer:
    """Ant Colony Optimization for path finding and resource allocation.

    Virtual ants traverse a graph, depositing pheromones on good paths.
    Over time, the colony converges on optimal paths.
    """

    def __init__(
        self,
        *,
        num_ants: int = 20,
        evaporation_rate: float = 0.1,
        alpha: float = 1.0,  # pheromone influence
        beta: float = 2.0,  # heuristic influence
        iterations: int = 100,
    ) -> None:
        self._num_ants = num_ants
        self._evaporation_rate = evaporation_rate
        self._alpha = alpha
        self._beta = beta
        self._iterations = iterations

        # Graph representation: node -> {neighbor: (distance, pheromone)}
        self._graph: dict[str, dict[str, list[float]]] = {}
        self._nodes: set[str] = set()

    def add_edge(self, from_node: str, to_node: str, distance: float = 1.0) -> None:
        """Add an edge to the optimization graph."""
        self._nodes.add(from_node)
        self._nodes.add(to_node)

        if from_node not in self._graph:
            self._graph[from_node] = {}
        if to_node not in self._graph:
            self._graph[to_node] = {}

        # Store [distance, pheromone_level]
        self._graph[from_node][to_node] = [distance, 1.0]
        self._graph[to_node][from_node] = [distance, 1.0]

    def optimize(self, start: str, goal: str) -> list[str]:
        """Find the optimal path from start to goal using ACO.

        Returns the best path found.
        """
        best_path: list[str] = []
        best_distance = float("inf")

        for iteration in range(self._iterations):
            # All ants construct paths
            paths: list[tuple[list[str], float]] = []
            for _ in range(self._num_ants):
                path = self._construct_path(start, goal)
                if path:
                    distance = self._path_distance(path)
                    paths.append((path, distance))

                    if distance < best_distance:
                        best_distance = distance
                        best_path = path

            # Evaporate all pheromones
            self._evaporate_all()

            # Deposit pheromones on paths (better paths get more)
            for path, distance in paths:
                deposit = 1.0 / max(distance, 0.001)
                self._deposit_on_path(path, deposit)

            logger.debug("ACO iteration %d: best distance=%.2f", iteration, best_distance)

        return best_path

    def _construct_path(self, start: str, goal: str) -> list[str] | None:
        """Construct a path from start to goal using pheromone-biased random walk."""
        if start not in self._graph:
            return None

        path = [start]
        current = start
        visited: set[str] = {start}

        while current != goal:
            neighbors = self._graph.get(current, {})
            unvisited = {n: d for n, d in neighbors.items() if n not in visited}

            if not unvisited:
                return None  # dead end

            # Compute probabilities based on pheromone and heuristic
            total = 0.0
            probs: list[tuple[str, float]] = []
            for neighbor, (distance, pheromone) in unvisited.items():
                prob = (pheromone**self._alpha) * ((1.0 / distance) ** self._beta)
                probs.append((neighbor, prob))
                total += prob

            if total == 0:
                # Fallback to random
                chosen = random.choice(list(unvisited.keys()))
            else:
                # Roulette wheel selection
                r = random.random() * total
                cumulative = 0.0
                chosen = list(unvisited.keys())[0]
                for neighbor, prob in probs:
                    cumulative += prob
                    if r <= cumulative:
                        chosen = neighbor
                        break

            path.append(chosen)
            visited.add(chosen)
            current = chosen

        return path

    def _evaporate_all(self) -> None:
        """Evaporate pheromone across all edges."""
        for _node, edges in self._graph.items():
            for neighbor in edges:
                edges[neighbor][1] *= 1.0 - self._evaporation_rate

    def _deposit_on_path(self, path: list[str], deposit: float) -> None:
        """Deposit pheromone along a path."""
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            if b in self._graph.get(a, {}):
                self._graph[a][b][1] += deposit

    def _path_distance(self, path: list[str]) -> float:
        """Compute the total distance of a path."""
        total = 0.0
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            total += self._graph.get(a, {}).get(b, [1.0, 0.0])[0]
        return total

    def snapshot(self) -> dict[str, Any]:
        """Return current state snapshot."""
        return {
            "nodes": len(self._nodes),
            "edges": sum(len(edges) for edges in self._graph.values()),
            "iterations": self._iterations,
        }


# ---------------------------------------------------------------------------
# Particle Swarm Optimization
# ---------------------------------------------------------------------------


class ParticleSwarmOptimizer:
    """Particle Swarm Optimization for strategy search.

    A swarm of particles explores a parameter/strategy space, each
    adjusting its trajectory based on personal and global best positions.
    """

    def __init__(
        self,
        *,
        num_particles: int = 30,
        inertia: float = 0.7,
        cognitive_weight: float = 1.5,
        social_weight: float = 1.5,
        bounds: tuple[float, float] = (-10.0, 10.0),
    ) -> None:
        self._num_particles = num_particles
        self._inertia = inertia
        self._cognitive_weight = cognitive_weight
        self._social_weight = social_weight
        self._bounds = bounds

        self._particles: list[Particle] = []
        self._global_best_position: list[float] | None = None
        self._global_best_score: float = -float("inf")
        self._iteration: int = 0

    def initialize(self, dimensions: int) -> None:
        """Initialize particles with random positions and velocities."""
        lo, hi = self._bounds
        self._particles = []

        for _ in range(self._num_particles):
            position = [random.uniform(lo, hi) for _ in range(dimensions)]
            velocity = [random.uniform(-1, 1) for _ in range(dimensions)]
            particle = Particle(position=position, velocity=velocity)
            self._particles.append(particle)

        self._iteration = 0
        logger.debug("PSO initialized: %d particles in %dD", self._num_particles, dimensions)

    def iterate(self, fitness_fn: Callable[[list[float]], float]) -> Particle:
        """Run one iteration of PSO.

        Returns the current global best particle.
        """
        for particle in self._particles:
            # Evaluate fitness
            score = fitness_fn(particle.position)

            # Update personal best
            if score > particle.best_score:
                particle.best_score = score
                particle.best_position = list(particle.position)

            # Update global best
            if score > self._global_best_score:
                self._global_best_score = score
                self._global_best_position = list(particle.position)

        # Update velocities and positions
        for particle in self._particles:
            if particle.best_position is None or self._global_best_position is None:
                continue

            for d in range(len(particle.position)):
                r1 = random.random()
                r2 = random.random()

                cognitive = (
                    self._cognitive_weight * r1 * (particle.best_position[d] - particle.position[d])
                )
                social = (
                    self._social_weight
                    * r2
                    * (self._global_best_position[d] - particle.position[d])
                )

                particle.velocity[d] = self._inertia * particle.velocity[d] + cognitive + social
                particle.position[d] += particle.velocity[d]

                # Clamp to bounds
                lo, hi = self._bounds
                particle.position[d] = max(lo, min(hi, particle.position[d]))

        self._iteration += 1
        return self.get_best_particle()

    def optimize(
        self,
        fitness_fn: Callable[[list[float]], float],
        iterations: int = 100,
    ) -> Particle:
        """Run the full PSO optimization for a given number of iterations."""
        for _ in range(iterations):
            self.iterate(fitness_fn)
        logger.debug(
            "PSO complete: best=%.4f at iteration %d", self._global_best_score, self._iteration
        )
        return self.get_best_particle()

    def get_best_particle(self) -> Particle:
        """Return the particle with the global best score."""
        for p in self._particles:
            if p.best_position == self._global_best_position:
                return p
        return self._particles[0] if self._particles else Particle()

    @property
    def best_score(self) -> float:
        return self._global_best_score

    @property
    def best_position(self) -> list[float] | None:
        return self._global_best_position

    def snapshot(self) -> dict[str, Any]:
        return {
            "particles": len(self._particles),
            "iteration": self._iteration,
            "best_score": self._global_best_score,
            "best_position": self._global_best_position,
        }


# ---------------------------------------------------------------------------
# Bee Algorithm
# ---------------------------------------------------------------------------


class BeeAlgorithm:
    """Bee Algorithm for task allocation / resource assignment.

    Scout bees explore for food sources; employed bees exploit
    known good sources; onlooker bees choose sources based on
    quality. Abandoned sources are replaced by new scouts.
    """

    def __init__(
        self,
        *,
        num_scouts: int = 5,
        num_employed: int = 10,
        num_onlookers: int = 5,
        abandonment_limit: int = 10,
    ) -> None:
        self._num_scouts = num_scouts
        self._num_employed = num_employed
        self._num_onlookers = num_onlookers
        self._abandonment_limit = abandonment_limit

        self._food_sources: dict[str, FoodSource] = {}
        self._best_source: FoodSource | None = None

    def register_source(self, location: str, quality: float) -> FoodSource:
        """Register a potential food source (task/resource)."""
        source = FoodSource(
            location=location,
            quality=quality,
            trials_remaining=self._abandonment_limit,
        )
        self._food_sources[location] = source
        if self._best_source is None or quality > self._best_source.quality:
            self._best_source = source
        return source

    def scout(self, location: str, quality: float) -> FoodSource:
        """Scout bees explore and find new food sources."""
        existing = self._food_sources.get(location)
        if existing is None:
            return self.register_source(location, quality)

        # Update quality if improved
        if quality > existing.quality:
            existing.quality = quality
            existing.trials_remaining = self._abandonment_limit
        return existing

    def exploit(self, location: str, bonus: float = 0.1) -> None:
        """Employed bees exploit a known good source, improving its quality."""
        source = self._food_sources.get(location)
        if source:
            source.quality = min(1.0, source.quality + bonus)
            source.trials_remaining = self._abandonment_limit
            if source.quality > (self._best_source.quality if self._best_source else 0):
                self._best_source = source

    def select_onlooker(self) -> FoodSource | None:
        """Onlooker bees select a food source based on quality-proportional probability."""
        if not self._food_sources:
            return None

        total = sum(s.quality for s in self._food_sources.values())
        if total == 0:
            return random.choice(list(self._food_sources.values()))

        r = random.random() * total
        cumulative = 0.0
        for source in self._food_sources.values():
            cumulative += source.quality
            if r <= cumulative:
                return source

        return list(self._food_sources.values())[-1]

    def abandon_exhausted(self) -> list[str]:
        """Abandon food sources with too many failed trials."""
        abandoned: list[str] = []
        for loc, source in list(self._food_sources.items()):
            source.trials_remaining -= 1
            if source.trials_remaining <= 0:
                del self._food_sources[loc]
                abandoned.append(loc)
                if self._best_source is not None and self._best_source.location == loc:
                    self._best_source = None
                logger.debug("Abandoned exhausted source: %s", loc)
        return abandoned

    def get_best_source(self) -> FoodSource | None:
        """Get the highest-quality food source."""
        return self._best_source

    def get_allocation(self) -> dict[str, float]:
        """Return task allocation: location -> quality (probability)."""
        total = max(sum(s.quality for s in self._food_sources.values()), 0.001)
        return {loc: s.quality / total for loc, s in self._food_sources.items()}

    def snapshot(self) -> dict[str, Any]:
        return {
            "food_sources": len(self._food_sources),
            "best_quality": self._best_source.quality if self._best_source else 0.0,
            "best_location": self._best_source.location if self._best_source else None,
            "allocation": self.get_allocation(),
        }


# ---------------------------------------------------------------------------
# Flocking / Boids
# ---------------------------------------------------------------------------


class FlockingSystem:
    """Flocking simulation using Reynolds' boids algorithm.

    Agents follow three rules:
    1. Separation: steer to avoid crowding local flockmates
    2. Alignment: steer toward average heading of local flockmates
    3. Cohesion: steer toward average position of local flockmates
    """

    def __init__(
        self,
        *,
        separation_weight: float = 1.5,
        alignment_weight: float = 1.0,
        cohesion_weight: float = 1.0,
        max_speed: float = 2.0,
        perception_radius: float = 5.0,
        width: float = 100.0,
        height: float = 100.0,
    ) -> None:
        self._separation_weight = separation_weight
        self._alignment_weight = alignment_weight
        self._cohesion_weight = cohesion_weight
        self._max_speed = max_speed
        self._perception_radius = perception_radius
        self._width = width
        self._height = height

        self._boids: dict[str, Boid] = {}
        self._iteration: int = 0

    def add_boid(
        self,
        boid_id: str | None = None,
        position: tuple[float, float] | None = None,
        velocity: tuple[float, float] | None = None,
    ) -> str:
        """Add a boid to the flock."""
        bid = boid_id or _new_id()
        pos = position or (random.uniform(0, self._width), random.uniform(0, self._height))
        vel = velocity or (random.uniform(-1, 1), random.uniform(-1, 1))
        self._boids[bid] = Boid(
            boid_id=bid,
            position=pos,
            velocity=vel,
            max_speed=self._max_speed,
            perception_radius=self._perception_radius,
        )
        return bid

    def remove_boid(self, boid_id: str) -> bool:
        return self._boids.pop(boid_id, None) is not None

    def step(self, dt: float = 0.1) -> None:
        """Advance the flock by one time step."""
        new_positions: dict[str, tuple[float, float]] = {}
        new_velocities: dict[str, tuple[float, float]] = {}

        boids = list(self._boids.values())
        for boid in boids:
            neighbors = self._get_neighbors(boid, boids)

            separation = self._compute_separation(boid, neighbors)
            alignment = self._compute_alignment(boid, neighbors)
            cohesion = self._compute_cohesion(boid, neighbors)

            # Combine steering forces
            dvx = (
                separation[0] * self._separation_weight
                + alignment[0] * self._alignment_weight
                + cohesion[0] * self._cohesion_weight
            )
            dvy = (
                separation[1] * self._separation_weight
                + alignment[1] * self._alignment_weight
                + cohesion[1] * self._cohesion_weight
            )

            # Update velocity
            vx = boid.velocity[0] + dvx * dt
            vy = boid.velocity[1] + dvy * dt

            # Limit speed
            speed = math.sqrt(vx * vx + vy * vy)
            if speed > self._max_speed:
                vx = vx / speed * self._max_speed
                vy = vy / speed * self._max_speed

            # Update position with wrapping
            px = (boid.position[0] + vx * dt) % self._width
            py = (boid.position[1] + vy * dt) % self._height

            new_velocities[boid.boid_id] = (vx, vy)
            new_positions[boid.boid_id] = (px, py)

        # Apply all updates
        for boid in self._boids.values():
            boid.position = new_positions[boid.boid_id]
            boid.velocity = new_velocities[boid.boid_id]

        self._iteration += 1

    def _get_neighbors(self, boid: Boid, all_boids: list[Boid]) -> list[Boid]:
        """Find neighbors within perception radius."""
        neighbors: list[Boid] = []
        for other in all_boids:
            if other.boid_id == boid.boid_id:
                continue
            dx = boid.position[0] - other.position[0]
            dy = boid.position[1] - other.position[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < self._perception_radius:
                neighbors.append(other)
        return neighbors

    def _compute_separation(self, boid: Boid, neighbors: list[Boid]) -> tuple[float, float]:
        """Steer away from nearby boids."""
        if not neighbors:
            return (0.0, 0.0)

        sx, sy = 0.0, 0.0
        for other in neighbors:
            dx = boid.position[0] - other.position[0]
            dy = boid.position[1] - other.position[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 0.01:
                dist = 0.01
            sx += dx / dist
            sy += dy / dist

        n = len(neighbors)
        return (sx / n, sy / n)

    def _compute_alignment(self, boid: Boid, neighbors: list[Boid]) -> tuple[float, float]:
        """Steer toward average heading of neighbors."""
        if not neighbors:
            return (0.0, 0.0)

        avg_vx = sum(o.velocity[0] for o in neighbors) / len(neighbors)
        avg_vy = sum(o.velocity[1] for o in neighbors) / len(neighbors)

        return (avg_vx - boid.velocity[0], avg_vy - boid.velocity[1])

    def _compute_cohesion(self, boid: Boid, neighbors: list[Boid]) -> tuple[float, float]:
        """Steer toward average position of neighbors."""
        if not neighbors:
            return (0.0, 0.0)

        avg_px = sum(o.position[0] for o in neighbors) / len(neighbors)
        avg_py = sum(o.position[1] for o in neighbors) / len(neighbors)

        return (avg_px - boid.position[0], avg_py - boid.position[1])

    def get_positions(self) -> dict[str, tuple[float, float]]:
        """Get current positions of all boids."""
        return {bid: b.position for bid, b in self._boids.items()}

    def get_centroid(self) -> tuple[float, float]:
        """Get the centroid of the flock."""
        if not self._boids:
            return (0.0, 0.0)
        avg_x = sum(b.position[0] for b in self._boids.values()) / len(self._boids)
        avg_y = sum(b.position[1] for b in self._boids.values()) / len(self._boids)
        return (avg_x, avg_y)

    @property
    def population(self) -> int:
        return len(self._boids)

    def snapshot(self) -> dict[str, Any]:
        return {
            "population": len(self._boids),
            "iteration": self._iteration,
            "centroid": self.get_centroid(),
        }
