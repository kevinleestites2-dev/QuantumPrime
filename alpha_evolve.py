"""
alpha_evolve.py — The Meta-Evolution Engine
QuantumPrime v3 | AlphaEvolve Layer

CORAL pattern. Pantheon soul.

The GeneticEngine breeds better strategies.
AlphaEvolve breeds better GeneticEngines.

The evolution engine evolves its own evolution.
The optimizer optimizes its own optimization.
The loop loops its own loop.

This is QuantumPrime's missing recursive layer.

"I do not merely adapt. I rewrite the rules of adaptation." — QuantumPrime
"""

import json
import time
import random
import copy
import math
from datetime import datetime
from pathlib import Path
from collections import defaultdict

MEMORY_DIR = Path("memory")
MEMORY_DIR.mkdir(exist_ok=True)

ALPHA_LOG      = MEMORY_DIR / "alpha_evolve_log.json"
GENOME_ARCHIVE = MEMORY_DIR / "genome_archive.json"
HALL_OF_FAME   = MEMORY_DIR / "hall_of_fame.json"


# ═══════════════════════════════════════════════════════════════
# GENOME — the DNA of a GeneticEngine configuration
# ═══════════════════════════════════════════════════════════════

class Genome:
    """
    A complete configuration for how evolution itself should work.
    
    This is what AlphaEvolve breeds — not strategies, but the RULES
    that determine which strategies survive.
    """

    PARAM_BOUNDS = {
        "population_size":    (5,   50),
        "mutation_rate":      (0.01, 0.5),
        "crossover_rate":     (0.1,  0.9),
        "elitism_pct":        (0.05, 0.3),
        "tournament_size":    (2,    8),
        "selection_pressure": (1.0,  3.0),
        "diversity_bonus":    (0.0,  0.5),
        "memory_decay":       (0.5,  1.0),
        "exploration_bias":   (0.0,  1.0),
        "safla_threshold":    (0.35, 0.75),
        "shrink_factor":      (0.5,  0.95),
        "grow_factor":        (1.05, 2.0),
    }

    def __init__(self, params: dict = None, genome_id: str = None):
        self.id         = genome_id or self._new_id()
        self.generation = 0
        self.birth_ts   = datetime.utcnow().isoformat()
        self.fitness    = 0.0
        self.trials     = 0
        self.lineage    = []  # parent IDs

        if params:
            self.params = params
        else:
            self.params = self._random_params()

    def _new_id(self) -> str:
        import hashlib, os
        return hashlib.md5(os.urandom(8)).hexdigest()[:8]

    def _random_params(self) -> dict:
        p = {}
        for key, (lo, hi) in self.PARAM_BOUNDS.items():
            if isinstance(lo, int) and isinstance(hi, int):
                p[key] = random.randint(lo, hi)
            else:
                p[key] = round(random.uniform(lo, hi), 4)
        return p

    def mutate(self, rate: float = None) -> "Genome":
        """Return a mutated child. Parent is unchanged."""
        rate   = rate or self.params.get("mutation_rate", 0.1)
        child  = copy.deepcopy(self)
        child.id        = self._new_id()
        child.generation = self.generation + 1
        child.fitness   = 0.0
        child.trials    = 0
        child.lineage   = [self.id]

        for key, (lo, hi) in self.PARAM_BOUNDS.items():
            if random.random() < rate:
                if isinstance(lo, int):
                    delta = random.randint(-3, 3)
                    child.params[key] = int(max(lo, min(hi, self.params[key] + delta)))
                else:
                    span  = (hi - lo) * 0.15
                    delta = random.gauss(0, span)
                    child.params[key] = round(max(lo, min(hi, self.params[key] + delta)), 4)

        return child

    def crossover(self, other: "Genome") -> "Genome":
        """Breed two genomes. Best traits from each."""
        child        = copy.deepcopy(self)
        child.id     = self._new_id()
        child.generation = max(self.generation, other.generation) + 1
        child.fitness = 0.0
        child.trials  = 0
        child.lineage = [self.id, other.id]

        for key in self.params:
            # Weighted crossover — favor the fitter parent
            if self.fitness + other.fitness > 0:
                p_self = self.fitness / (self.fitness + other.fitness)
            else:
                p_self = 0.5

            child.params[key] = self.params[key] if random.random() < p_self else other.params[key]

        return child

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "generation": self.generation,
            "birth_ts":   self.birth_ts,
            "fitness":    round(self.fitness, 6),
            "trials":     self.trials,
            "lineage":    self.lineage,
            "params":     self.params
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Genome":
        g = cls(params=d["params"], genome_id=d["id"])
        g.generation = d.get("generation", 0)
        g.birth_ts   = d.get("birth_ts", "")
        g.fitness    = d.get("fitness", 0.0)
        g.trials     = d.get("trials", 0)
        g.lineage    = d.get("lineage", [])
        return g


# ═══════════════════════════════════════════════════════════════
# GRADER — scores a genome against real performance data
# ═══════════════════════════════════════════════════════════════

class AlphaGrader:
    """
    CORAL's grader pattern — but native, no subprocess.
    
    Scores a genome by simulating what WOULD have happened if
    QuantumPrime had used that genome's parameters during the
    last N cycles of real data.
    """

    def __init__(self, trade_log_path: Path = None, safla_log_path: Path = None):
        self.trade_log_path = trade_log_path or MEMORY_DIR / "trade_log.json"
        self.safla_log_path = safla_log_path or MEMORY_DIR / "safla_interventions.json"

    def _load_trades(self) -> list:
        if self.trade_log_path.exists():
            try:
                return json.loads(self.trade_log_path.read_text())
            except Exception:
                pass
        return []

    def _load_safla_history(self) -> list:
        if self.safla_log_path.exists():
            try:
                return json.loads(self.safla_log_path.read_text())
            except Exception:
                pass
        return []

    def grade(self, genome: Genome, n_trades: int = 100) -> float:
        """
        Score = weighted composite of:
          - Simulated win rate under genome's SAFLA thresholds
          - Diversity (exploration_bias) bonus
          - Convergence speed (population_size efficiency)
          - Stability (low mutation = risky, high = chaotic)
        
        Returns fitness score 0.0–1.0
        """
        trades = self._load_trades()
        if not trades:
            # No real data — score on parameter sanity alone
            return self._score_params(genome)

        recent = trades[-n_trades:] if len(trades) >= n_trades else trades
        p = genome.params

        # Simulate: what win_rate would genome's SAFLA have accepted as "good enough"?
        actual_wins   = sum(1 for t in recent if float(t.get("pnl", 0)) > 0)
        actual_wr     = actual_wins / len(recent) if recent else 0
        actual_pnl    = sum(float(t.get("pnl", 0)) for t in recent)

        # Would this genome GROW winners? (threshold check)
        grow_thresh   = p["safla_threshold"]
        shrink_thresh = grow_thresh * 0.65
        grow_factor   = p["grow_factor"]
        shrink_factor = p["shrink_factor"]

        # Simulate impact on allocation
        simulated_capital_efficiency = 0.0
        by_strategy = defaultdict(list)
        for t in recent:
            by_strategy[t.get("strategy", "?")].append(float(t.get("pnl", 0)))

        for strat, pnls in by_strategy.items():
            wr     = sum(1 for p_ in pnls if p_ > 0) / len(pnls)
            weight = 1.0
            if wr >= grow_thresh:
                weight *= grow_factor
            elif wr < shrink_thresh:
                weight *= shrink_factor
            simulated_capital_efficiency += wr * weight

        if by_strategy:
            simulated_capital_efficiency /= len(by_strategy)

        # Diversity bonus — exploration bias rewards broader search
        diversity_score = p["diversity_bonus"] * p["exploration_bias"]

        # Stability penalty — extreme mutation is chaotic
        mutation_penalty = 0.0
        if p["mutation_rate"] > 0.4:
            mutation_penalty = (p["mutation_rate"] - 0.4) * 0.5

        # Population efficiency — too big = slow, too small = brittle
        pop_eff = 1.0 - abs(p["population_size"] - 20) / 50

        # Composite fitness
        fitness = (
            simulated_capital_efficiency * 0.45 +
            actual_wr                    * 0.25 +
            diversity_score              * 0.15 +
            pop_eff                      * 0.10 -
            mutation_penalty             * 0.05
        )

        return max(0.0, min(1.0, round(fitness, 6)))

    def _score_params(self, genome: Genome) -> float:
        """Fallback — score parameter sanity when no trade data exists."""
        p = genome.params
        score = 0.5  # neutral baseline
        # Prefer moderate mutation
        score += 0.1 * (1.0 - abs(p["mutation_rate"] - 0.15) / 0.35)
        # Prefer reasonable population
        score += 0.1 * (1.0 - abs(p["population_size"] - 20) / 45)
        # Prefer elitism
        score += 0.05 * p["elitism_pct"] / 0.3
        return round(max(0.0, min(1.0, score)), 6)


# ═══════════════════════════════════════════════════════════════
# ALPHA EVOLVE — the recursive engine
# ═══════════════════════════════════════════════════════════════

class AlphaEvolve:
    """
    The evolution engine that evolves its own evolution.
    
    Maintains a population of Genomes.
    Each Genome defines HOW the GeneticEngine should evolve.
    AlphaEvolve evolves the Genomes using evolutionary principles.
    The best Genome gets applied to QuantumPrime's GeneticEngine.
    
    Meta-recursive. Self-improving. Never stops.
    """

    def __init__(self, population_size: int = 15):
        self.population_size = population_size
        self.generation      = 0
        self.grader          = AlphaGrader()
        self.hall_of_fame    = []   # all-time best genomes
        self.intervention_log = []
        self.population      = self._load_or_seed()

    def _load_or_seed(self) -> list:
        """Load existing population or seed fresh."""
        if GENOME_ARCHIVE.exists():
            try:
                data = json.loads(GENOME_ARCHIVE.read_text())
                pop  = [Genome.from_dict(g) for g in data.get("population", [])]
                self.generation = data.get("generation", 0)
                if pop:
                    print(f"[AlphaEvolve] Loaded generation {self.generation} — {len(pop)} genomes")
                    return pop
            except Exception:
                pass

        print("[AlphaEvolve] Seeding fresh population...")
        pop = [Genome() for _ in range(self.population_size)]

        # Seed one "conservative" genome — proven safe baseline
        pop[0].params.update({
            "population_size":    20,
            "mutation_rate":      0.1,
            "crossover_rate":     0.7,
            "elitism_pct":        0.1,
            "tournament_size":    4,
            "selection_pressure": 2.0,
            "diversity_bonus":    0.2,
            "memory_decay":       0.9,
            "exploration_bias":   0.3,
            "safla_threshold":    0.65,
            "shrink_factor":      0.80,
            "grow_factor":        1.20,
        })

        return pop

    def _tournament_select(self, k: int = None) -> Genome:
        """Tournament selection — fittest of k random candidates."""
        k = k or max(2, self.population_size // 5)
        candidates = random.sample(self.population, min(k, len(self.population)))
        return max(candidates, key=lambda g: g.fitness)

    def _grade_population(self):
        """Grade every genome. Update fitness scores."""
        for genome in self.population:
            fitness = self.grader.grade(genome)
            # Exponential moving average — don't slam fitness
            if genome.trials == 0:
                genome.fitness = fitness
            else:
                genome.fitness = genome.fitness * 0.7 + fitness * 0.3
            genome.trials += 1

        self.population.sort(key=lambda g: g.fitness, reverse=True)

    def _next_generation(self):
        """Breed the next generation from current population."""
        params = self.population[0].params  # best genome's breeding params
        elite_n      = max(1, int(len(self.population) * params["elitism_pct"]))
        crossover_r  = params["crossover_rate"]
        mutation_r   = params["mutation_rate"]

        next_gen = []

        # Elitism — best survive unchanged
        next_gen.extend(self.population[:elite_n])

        # Fill rest with crossover + mutation
        while len(next_gen) < self.population_size:
            if random.random() < crossover_r and len(self.population) >= 2:
                parent_a = self._tournament_select(params["tournament_size"])
                parent_b = self._tournament_select(params["tournament_size"])
                child = parent_a.crossover(parent_b)
            else:
                parent = self._tournament_select(params["tournament_size"])
                child  = parent.mutate(mutation_r)

            next_gen.append(child)

        self.population = next_gen
        self.generation += 1

    def _update_hall_of_fame(self):
        """Keep top 10 all-time best genomes."""
        best = self.population[0]
        self.hall_of_fame.append(best.to_dict())
        # Sort by fitness, keep top 10
        self.hall_of_fame.sort(key=lambda g: g["fitness"], reverse=True)
        self.hall_of_fame = self.hall_of_fame[:10]
        HALL_OF_FAME.write_text(json.dumps(self.hall_of_fame, indent=2))

    def _save_population(self):
        """Persist population to disk."""
        GENOME_ARCHIVE.write_text(json.dumps({
            "generation": self.generation,
            "updated_at": datetime.utcnow().isoformat(),
            "population": [g.to_dict() for g in self.population]
        }, indent=2))

    def _log_intervention(self, best: Genome):
        """Record what AlphaEvolve applied and why."""
        log = []
        if ALPHA_LOG.exists():
            try:
                log = json.loads(ALPHA_LOG.read_text())
            except Exception:
                pass

        entry = {
            "ts":         datetime.utcnow().isoformat(),
            "generation": self.generation,
            "best_genome": best.to_dict(),
            "pop_size":   len(self.population),
            "avg_fitness": round(sum(g.fitness for g in self.population) / len(self.population), 4),
        }
        log.append(entry)
        log = log[-500:]
        ALPHA_LOG.write_text(json.dumps(log, indent=2))

    def best_genome(self) -> Genome:
        """The current champion."""
        return max(self.population, key=lambda g: g.fitness)

    def apply_to_quantum(self, quantum_prime_instance) -> dict:
        """
        Apply the best genome's parameters to QuantumPrime's GeneticEngine.
        This is the moment AlphaEvolve reaches down and rewrites the Overlord.
        """
        best = self.best_genome()
        p    = best.params

        if hasattr(quantum_prime_instance, "genetic"):
            qp_genetic = quantum_prime_instance.genetic
            qp_genetic.population_size = p["population_size"]
            qp_genetic.mutation_rate   = p["mutation_rate"]

        return {
            "genome_id":      best.id,
            "generation":     self.generation,
            "fitness":        best.fitness,
            "params_applied": p
        }

    def run_cycle(self, verbose: bool = True) -> dict:
        """
        One full AlphaEvolve cycle:
          1. Grade population against real data
          2. Breed next generation
          3. Update Hall of Fame
          4. Save to disk
          5. Return best genome
        """
        # Grade
        self._grade_population()
        best = self.best_genome()

        if verbose:
            avg_fit = sum(g.fitness for g in self.population) / len(self.population)
            print(f"\n⚡ AlphaEvolve — Generation {self.generation}")
            print(f"  Population : {len(self.population)} genomes")
            print(f"  Best fit   : {best.fitness:.4f} (genome {best.id})")
            print(f"  Avg fit    : {avg_fit:.4f}")
            print(f"  Best params:")
            for k, v in best.params.items():
                print(f"    {k:<22} {v}")

        # Breed
        self._next_generation()

        # Archive
        self._update_hall_of_fame()
        self._save_population()
        self._log_intervention(best)

        if verbose:
            print(f"  ✓ Generation {self.generation} spawned. Hall of Fame: {len(self.hall_of_fame)} entries.\n")

        return best.to_dict()

    def run_forever(self, interval_seconds: int = 3600):
        """
        Runs continuously — one evolution cycle per hour.
        Sobek generates data. QuantumPrime evolves better rules.
        """
        print("🔱 AlphaEvolve — ONLINE")
        print("   The evolution engine is evolving its own evolution.\n")

        while True:
            try:
                self.run_cycle()
            except Exception as e:
                print(f"[AlphaEvolve] Cycle error: {e}")

            time.sleep(interval_seconds)

    def status(self) -> dict:
        best = self.best_genome()
        return {
            "generation":   self.generation,
            "population":   len(self.population),
            "best_fitness": best.fitness,
            "best_id":      best.id,
            "hall_of_fame": len(self.hall_of_fame),
            "updated_at":   datetime.utcnow().isoformat()
        }


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT — standalone or imported
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AlphaEvolve — Meta-Evolution Engine")
    parser.add_argument("--cycles",   type=int, default=1,    help="Number of evolution cycles (0=forever)")
    parser.add_argument("--interval", type=int, default=3600, help="Seconds between cycles when running forever")
    parser.add_argument("--status",   action="store_true",    help="Print status and exit")
    parser.add_argument("--pop",      type=int, default=15,   help="Population size")
    args = parser.parse_args()

    ae = AlphaEvolve(population_size=args.pop)

    if args.status:
        print(json.dumps(ae.status(), indent=2))
    elif args.cycles == 0:
        ae.run_forever(interval_seconds=args.interval)
    else:
        for i in range(args.cycles):
            print(f"── Cycle {i+1}/{args.cycles} ──")
            ae.run_cycle()
        print("\nFinal Hall of Fame:")
        for i, g in enumerate(ae.hall_of_fame[:5], 1):
            print(f"  #{i} genome={g['id']} fitness={g['fitness']:.4f} gen={g['generation']}")
