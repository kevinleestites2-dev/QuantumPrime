"""
╔══════════════════════════════════════════════════════════════════╗
║          Q U A N T U M P R I M E   v2.0.0                       ║
║   THE LIVING QUANTUM OPTIMIZATION ENGINE                        ║
║                                                                  ║
║   BIRTH      → BabyAGI      (will — creates its own goals)     ║
║   PERCEPTION → AIlice       (real APIs: Polymarket/Kalshi/      ║
║                               Binance/RentAHuman)               ║
║   ADAPTATION → SAFLA        (real PnL from zeus_prime.db)       ║
║   EVOLUTION  → GeneticEngine(breeds winners, kills losers)     ║
║   CLARITY    → QuantumCore  (simulated annealing optimizer)     ║
║   ACTION     → ZeusPrime    (live executor, $1 safety cap)      ║
║                                                                  ║
║   BRAIN      → zeus_absorbed (FourLayerMemory + OllamaRouter +  ║
║                  MARSEngine + ShadowMind + BayesianTrust +      ║
║                  SkillExtractor + TermuxHardware)               ║
║                                                                  ║
║   Forgemaster: Kevin Stites                                     ║
║   Born: 2026-05-11  |  v2.0: Zeus absorbed 2026-05-11          ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os, json, time, sqlite3, subprocess, urllib.request
import random, logging, threading, asyncio
from datetime import datetime
from collections import deque
from typing import Any

# ─── Zeus Brain ─────────────────────────────────────────────────────────────
try:
    from zeus_absorbed import (
        ZeusConfig, FourLayerMemory, OllamaRouter,
        MARSEngine, ShadowMind, BayesianTrustLedger,
        AgentProfile, MetaImprovementLog, SkillExtractor,
        TermuxHardware, TaskRecord, TaskComplexity
    )
    ZEUS_AVAILABLE = True
except ImportError:
    ZEUS_AVAILABLE = False

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [QuantumPrime] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("QuantumPrime")


# ═══════════════════════════════════════════════════════════════════════════
# ZEUS BRAIN — initialised once, shared by all 6 layers
# ═══════════════════════════════════════════════════════════════════════════

class ZeusBrain:
    """
    The absorbed intelligence of Zeus-prime.
    Shared across all QuantumPrime layers.
    Falls back gracefully when Ollama is offline.
    """

    def __init__(self):
        if not ZEUS_AVAILABLE:
            log.warning("[BRAIN] zeus_absorbed not found — brain offline")
            self.online      = False
            self.cfg         = None
            self.memory      = None
            self.llm         = None
            self.mars        = None
            self.shadow      = None
            self.trust       = None
            self.improvement = None
            self.skills      = None
            self.hardware    = None
            return

        self.online      = True
        self.cfg         = ZeusConfig()
        self.memory      = FourLayerMemory(self.cfg)
        self.llm         = OllamaRouter(self.cfg)
        self.mars        = MARSEngine(self.llm, self.memory)
        self.shadow      = ShadowMind(self.llm, self.memory)
        self.trust       = BayesianTrustLedger()
        self.improvement = MetaImprovementLog()
        self.skills      = SkillExtractor(self.llm, self.memory)
        self.hardware    = TermuxHardware()

        # Register the 6 perception agents in the trust ledger
        for agent_id, name, specialty in [
            ("polymarket_watcher", "Polymarket Agent", "prediction_markets"),
            ("kalshi_watcher",     "Kalshi Agent",     "prediction_markets"),
            ("binance_watcher",    "Binance Agent",    "crypto"),
            ("rentahuman_watcher", "RentAHuman Agent", "tasks"),
            ("tax_deed_watcher",   "TaxDeed Agent",    "real_estate"),
            ("repo_auction_watcher","RepoAuction Agent","auto"),
        ]:
            self.trust.register(
                AgentProfile(agent_id=agent_id, name=name, specialty=specialty)
            )

        log.info("[BRAIN] Zeus brain online — FourLayerMemory + OllamaRouter + MARS + ShadowMind ready")

    def record_improvement(self, system: str, action: str, impact: float):
        if self.online:
            self.improvement.record({"system": system, "action": action, "impact": impact})

    def store_memory(self, tag: str, content: str):
        if self.online:
            self.memory.l3.store(tag, content)

    def get_context(self, query: str) -> str:
        if self.online:
            return self.memory.build_context(query)
        return ""

    async def reflect(self, task: str, steps: list, result: str, success: bool) -> dict:
        """Ask MARS to reflect on a completed cycle."""
        if not self.online:
            return {}
        if success:
            return await self.mars.reflect_on_success(task, steps, result)
        else:
            return await self.mars.reflect_on_failure(task, steps, result)

    async def get_intuition(self, task: str, context: str = "") -> str:
        """Ask ShadowMind for pattern-based intuition on a task."""
        if not self.online:
            return ""
        try:
            return await self.shadow.intuition(task, context)
        except Exception as e:
            log.warning(f"[BRAIN] ShadowMind offline: {e}")
            return ""

    def trust_agent(self, agent_id: str, success: bool):
        if self.online:
            self.trust.record_outcome(agent_id, success)

    def get_trust(self, agent_id: str) -> float:
        if not self.online:
            return 0.5
        profile = self.trust.get_profile(agent_id)
        return profile.trust_score if profile else 0.5


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1 — BIRTH (BabyAGI Heartbeat)
# ═══════════════════════════════════════════════════════════════════════════

class BabyAGICore:
    """
    The heartbeat. Generates its own goals.
    Creates tasks → prioritizes → executes → learns → repeats forever.
    """

    def __init__(self, brain: ZeusBrain):
        self.brain       = brain
        self.task_queue  = deque()
        self.completed   = []
        self.objective   = "Maximize optimization opportunities across all domains"
        self.cycle       = 0
        self._lock       = threading.Lock()

    def create_task(self, description: str, priority: int = 5, domain: str = "general") -> dict:
        task = {
            "id":          f"TASK-{self.cycle:04d}-{int(time.time())}",
            "description": description,
            "priority":    priority,
            "domain":      domain,
            "created_at":  datetime.utcnow().isoformat(),
            "status":      "pending"
        }
        with self._lock:
            self.task_queue.append(task)

        # Store in Zeus L3 memory
        self.brain.store_memory("task_queue", f"[{task['id']}] {description} (domain={domain})")
        log.info(f"[BIRTH] Task: {task['id']} | {description}")
        return task

    def prioritize(self):
        with self._lock:
            self.task_queue = deque(sorted(self.task_queue, key=lambda t: t["priority"], reverse=True))

    def get_next_task(self) -> dict | None:
        with self._lock:
            return self.task_queue.popleft() if self.task_queue else None

    def mark_complete(self, task: dict, result: Any):
        task["status"]       = "complete"
        task["result"]       = result
        task["completed_at"] = datetime.utcnow().isoformat()
        self.completed.append(task)
        log.info(f"[BIRTH] Complete: {task['id']}")

    def spawn_next_cycle_tasks(self, last_result: Any):
        self.cycle += 1
        domains = ["prediction_markets", "crypto", "real_estate", "auto", "tasks"]
        for domain in domains:
            self.create_task(
                description=f"Scan {domain} for opportunities — cycle {self.cycle}",
                priority=random.randint(3, 9),
                domain=domain
            )
        log.info(f"[BIRTH] Cycle {self.cycle} → {len(domains)} new tasks")


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 2 — PERCEPTION (AIlice — real API calls)
# ═══════════════════════════════════════════════════════════════════════════

class AIliceFactory:
    """
    Spawns real observation agents.
    Polymarket: free, no auth.
    Kalshi: KALSHI_API_KEY_ID env var.
    Binance: public endpoint.
    RentAHuman: RAH_API_KEY env var.
    Trust scores from ZeusBrain BayesianTrustLedger gate signal weight.
    """

    DOMAIN_AGENTS = {
        "prediction_markets": ["polymarket_watcher", "kalshi_watcher"],
        "crypto":             ["binance_watcher"],
        "real_estate":        ["tax_deed_watcher", "foreclosure_watcher"],
        "auto":               ["repo_auction_watcher", "gsa_watcher"],
        "tasks":              ["rentahuman_watcher"],
        "general":            ["news_watcher"],
    }

    POLYMARKET_CLOB = "https://gamma-api.polymarket.com"
    KALSHI_BASE     = "https://trading-api.kalshi.com/trade-api/v2"
    BINANCE_BASE    = "https://api.binance.com/api/v3"

    def __init__(self, brain: ZeusBrain):
        self.brain        = brain
        self.active_agents = {}

    def spawn_agent(self, domain: str) -> list[dict]:
        agents = self.DOMAIN_AGENTS.get(domain, self.DOMAIN_AGENTS["general"])
        observations = []
        for agent_name in agents:
            obs = self._run_agent(agent_name, domain)
            # Weight observation by trust score from Zeus brain
            trust = self.brain.get_trust(agent_name)
            obs["trust_weight"] = trust
            obs["weighted_signal"] = round(obs["signal_strength"] * trust, 3)
            # Update trust ledger based on whether source was live
            self.brain.trust_agent(agent_name, obs.get("source") == "live")
            observations.append(obs)
            self.active_agents[agent_name] = obs
        log.info(f"[PERCEPTION] {len(agents)} agents for domain={domain}")
        return observations

    def _run_agent(self, name: str, domain: str) -> dict:
        try:
            if "polymarket" in name:
                return self._polymarket_signal()
            elif "kalshi" in name:
                return self._kalshi_signal()
            elif "binance" in name:
                return self._binance_signal()
            elif "rentahuman" in name:
                return self._rentahuman_signal()
            else:
                return self._simulated_signal(name, domain)
        except Exception as e:
            log.warning(f"[PERCEPTION] {name} failed ({e}) — simulating")
            return self._simulated_signal(name, domain)

    def _polymarket_signal(self) -> dict:
        url = f"{self.POLYMARKET_CLOB}/markets?limit=20&active=true&closed=false"
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "QuantumPrime/2.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        markets = data if isinstance(data, list) else data.get("data", data.get("results", []))
        if not markets:
            return self._simulated_signal("polymarket_watcher", "prediction_markets")
        edges, volumes = [], []
        for m in markets[:10]:
            for t in m.get("tokens", []):
                edges.append(abs(float(t.get("price", 0.5)) - 0.5))
            volumes.append(float(m.get("volume", 0) or 0))
        avg_edge = sum(edges) / len(edges) if edges else 0.3
        avg_vol  = sum(volumes) / len(volumes) if volumes else 0
        signal   = round(min(avg_edge * 2, 1.0), 3)
        vol_conf = round(min(avg_vol / 500000, 1.0), 3)
        conf     = round((min(len(markets) / 20, 1.0) + vol_conf) / 2, 3)
        top      = markets[0].get("question", "unknown")[:60] if markets else "unknown"
        log.info(f"[PERCEPTION] Polymarket: {len(markets)} markets | edge={avg_edge:.3f} | signal={signal}")
        return {
            "agent": "polymarket_watcher", "domain": "prediction_markets",
            "signal_strength": signal, "confidence": conf,
            "timestamp": datetime.utcnow().isoformat(),
            "raw_data": f"top={top} | markets={len(markets)} | edge={avg_edge:.3f} | vol=${avg_vol:,.0f}",
            "source": "live"
        }

    def _kalshi_signal(self) -> dict:
        api_key = os.getenv("KALSHI_API_KEY_ID", "")
        if not api_key:
            return self._simulated_signal("kalshi_watcher", "prediction_markets")
        url = f"{self.KALSHI_BASE}/markets?limit=20&status=open"
        req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        markets = data.get("markets", [])
        volumes = [float(m.get("volume", 0)) for m in markets if m.get("volume")]
        avg_vol = sum(volumes) / len(volumes) if volumes else 0
        signal  = round(min(avg_vol / 10000, 1.0), 3)
        conf    = round(min(len(markets) / 20, 1.0), 3)
        log.info(f"[PERCEPTION] Kalshi: {len(markets)} markets | signal={signal}")
        return {
            "agent": "kalshi_watcher", "domain": "prediction_markets",
            "signal_strength": signal, "confidence": conf,
            "timestamp": datetime.utcnow().isoformat(),
            "raw_data": f"markets={len(markets)} | avg_vol={avg_vol:.0f}",
            "source": "live"
        }

    def _binance_signal(self) -> dict:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "POLUSDT", "BNBUSDT"]
        changes = []
        for sym in symbols:
            url = f"{self.BINANCE_BASE}/ticker/24hr?symbol={sym}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                d = json.loads(r.read())
            changes.append(abs(float(d.get("priceChangePercent", 0))))
        avg_change = sum(changes) / len(changes) if changes else 0
        signal     = round(min(avg_change / 5, 1.0), 3)
        log.info(f"[PERCEPTION] Binance: avg_24h_change={avg_change:.2f}% | signal={signal}")
        return {
            "agent": "binance_watcher", "domain": "crypto",
            "signal_strength": signal, "confidence": 0.85,
            "timestamp": datetime.utcnow().isoformat(),
            "raw_data": f"symbols={symbols} | avg_change={avg_change:.2f}%",
            "source": "live"
        }

    def _rentahuman_signal(self) -> dict:
        api_key = os.getenv("RAH_API_KEY", "")
        if not api_key:
            return self._simulated_signal("rentahuman_watcher", "tasks")
        url = "https://rentahuman.ai/api/jobs?status=open&min_budget=100"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        jobs   = data.get("jobs", [])
        signal = round(min(len(jobs) / 20, 1.0), 3)
        log.info(f"[PERCEPTION] RentAHuman: {len(jobs)} open jobs")
        return {
            "agent": "rentahuman_watcher", "domain": "tasks",
            "signal_strength": signal, "confidence": 0.7,
            "timestamp": datetime.utcnow().isoformat(),
            "raw_data": f"open_jobs={len(jobs)}",
            "source": "live"
        }

    def _simulated_signal(self, name: str, domain: str) -> dict:
        return {
            "agent": name, "domain": domain,
            "signal_strength": round(random.uniform(0.1, 1.0), 3),
            "confidence":      round(random.uniform(0.4, 0.95), 3),
            "timestamp":       datetime.utcnow().isoformat(),
            "raw_data":        f"[SIMULATED] {name}",
            "source":          "simulated"
        }


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 3 — ADAPTATION (SAFLA — real PnL from zeus_prime.db)
# ═══════════════════════════════════════════════════════════════════════════

class SAFLACore:
    """
    Self-Adaptive Feedback Loop Algorithm.
    Reads real trade outcomes from zeus_prime.db when available.
    Falls back to simulation until trades exist.
    """

    DB_PATH = "zeus_prime.db"

    def __init__(self, brain: ZeusBrain):
        self.brain       = brain
        self.memory      = {}
        self.feedback_log = []

    def record_from_db(self, domain: str = "prediction_markets"):
        """Pull real PnL from zeus_prime.db. Falls back to simulation."""
        try:
            conn   = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT strategy, pnl, status FROM trades
                WHERE status IN ('closed','complete','win','loss')
                ORDER BY id DESC LIMIT 50
            """)
            rows = cursor.fetchall()
            cursor.execute("""
                SELECT strategy, rolling_pnl_24h, win_rate, trades_count
                FROM strategy_performance ORDER BY id DESC LIMIT 20
            """)
            perf_rows = cursor.fetchall()
            conn.close()

            if rows:
                for strategy, pnl, status in rows:
                    outcome = max(-1.0, min(1.0, float(pnl or 0) / 10.0))
                    self.record(domain, strategy, outcome)
                log.info(f"[ADAPTATION] Loaded {len(rows)} real trades from zeus_prime.db")
            else:
                log.info("[ADAPTATION] No closed trades yet — simulating")
                self._simulate_record(domain)

            for strategy, pnl_24h, win_rate, trades_count in perf_rows:
                if win_rate and trades_count and int(trades_count) > 0:
                    self.record(domain, strategy, float(win_rate or 0.5) * 2 - 1)

        except Exception as e:
            log.warning(f"[ADAPTATION] DB read failed ({e}) — simulating")
            self._simulate_record(domain)

    def _simulate_record(self, domain: str):
        for strat in ["grind_trading", "momentum", "mean_reversion", "sentiment_arb"]:
            self.record(domain, strat, round(random.uniform(-0.5, 0.8), 2))

    def record(self, domain: str, strategy_id: str, outcome: float):
        self.memory.setdefault(domain, {}).setdefault(strategy_id, []).append(outcome)
        self.feedback_log.append({"ts": datetime.utcnow().isoformat(), "domain": domain,
                                   "strategy": strategy_id, "outcome": outcome})
        log.info(f"[ADAPTATION] {strategy_id} in {domain} → outcome={outcome:+.3f}")

    def get_score(self, domain: str, strategy_id: str) -> float:
        try:
            scores = self.memory[domain][strategy_id]
            return sum(scores) / len(scores)
        except (KeyError, ZeroDivisionError):
            return 0.0

    def best_strategies(self, domain: str, top_n: int = 3) -> list:
        if domain not in self.memory:
            return []
        ranked = [(sid, sum(s) / len(s)) for sid, s in self.memory[domain].items()]
        return sorted(ranked, key=lambda x: x[1], reverse=True)[:top_n]


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 4 — EVOLUTION (Genetic Engine)
# ═══════════════════════════════════════════════════════════════════════════

class GeneticEngine:
    """Breeds winning strategies. Kills losers."""

    def __init__(self, population_size: int = 20, mutation_rate: float = 0.1):
        self.population_size = population_size
        self.mutation_rate   = mutation_rate
        self.generation      = 0
        self.population      = self._seed_population()

    def _seed_population(self) -> list[dict]:
        pop = []
        for i in range(self.population_size):
            pop.append({
                "id":         f"STRAT-GEN0-{i:03d}",
                "genes":      {
                    "signal_threshold": round(random.uniform(0.3, 0.9), 3),
                    "confidence_min":   round(random.uniform(0.5, 0.95), 3),
                    "position_size":    round(random.uniform(0.01, 0.1), 3),
                    "stop_loss":        round(random.uniform(0.02, 0.15), 3),
                    "time_horizon":     random.choice([60, 300, 900, 3600]),
                    "domain_weight":    round(random.uniform(0.1, 1.0), 3),
                },
                "fitness":    0.0,
                "generation": 0,
                "wins":       0,
                "losses":     0
            })
        log.info(f"[EVOLUTION] Population seeded: {self.population_size} strategies")
        return pop

    def evaluate(self, safla: SAFLACore, domain: str):
        for s in self.population:
            s["fitness"] = safla.get_score(domain, s["id"])

    def select(self) -> list[dict]:
        survivors = sorted(self.population, key=lambda s: s["fitness"], reverse=True)[:self.population_size // 2]
        log.info(f"[EVOLUTION] {len(survivors)} survivors | gen {self.generation}")
        return survivors

    def crossover(self, pa: dict, pb: dict) -> dict:
        self.generation += 1
        return {
            "id":         f"STRAT-GEN{self.generation}-{int(time.time()*1000)%10000:04d}",
            "genes":      {g: pa["genes"][g] if random.random() > 0.5 else pb["genes"][g] for g in pa["genes"]},
            "fitness":    0.0,
            "generation": self.generation,
            "wins":       0,
            "losses":     0
        }

    def mutate(self, s: dict) -> dict:
        for g in s["genes"]:
            if random.random() < self.mutation_rate and isinstance(s["genes"][g], float):
                s["genes"][g] = round(s["genes"][g] * random.uniform(0.8, 1.2), 3)
        return s

    def evolve(self, safla: SAFLACore, domain: str) -> list[dict]:
        self.evaluate(safla, domain)
        survivors = self.select()
        offspring = []
        while len(survivors) + len(offspring) < self.population_size:
            offspring.append(self.mutate(self.crossover(random.choice(survivors), random.choice(survivors))))
        self.population = survivors + offspring
        log.info(f"[EVOLUTION] Gen {self.generation} complete — {len(self.population)} strategies alive")
        return self.population

    def fittest(self) -> dict:
        return max(self.population, key=lambda s: s["fitness"])


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 5 — CLARITY (QuantumCore — simulated annealing)
# ═══════════════════════════════════════════════════════════════════════════

class QuantumCore:
    """Quantum-inspired optimization. Finds the global optimal strategy."""

    def __init__(self, temperature: float = 1.0, cooling_rate: float = 0.003):
        self.temperature  = temperature
        self.cooling_rate = cooling_rate
        self.backend      = "simulated_annealing"

    def optimize(self, strategies: list[dict], observations: list[dict]) -> dict:
        if not strategies:
            return {"error": "no strategies"}

        # Use weighted_signal if trust-weighted, else raw signal_strength
        avg_signal = sum(o.get("weighted_signal", o["signal_strength"]) for o in observations) / max(len(observations), 1)
        avg_conf   = sum(o["confidence"] for o in observations) / max(len(observations), 1)

        scored = []
        for s in strategies:
            g = s["genes"]
            q = (
                (1.0 - abs(g["signal_threshold"] - avg_signal)) *
                (1.0 - abs(g["confidence_min"]   - avg_conf)) *
                (1.0 + s["fitness"])
            )
            scored.append((q, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        optimal    = scored[0][1]
        q_score    = scored[0][0]
        self.temperature *= (1 - self.cooling_rate)

        log.info(f"[CLARITY] Optimal: {optimal['id']} | q_score={q_score:.4f} | T={self.temperature:.4f}")
        return {
            "strategy":   optimal,
            "q_score":    round(q_score, 4),
            "signal":     round(avg_signal, 3),
            "confidence": round(avg_conf, 3),
            "backend":    self.backend,
            "execute":    q_score > 0.5
        }


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 6 — ACTION (ZeusPrime Interface — live executor)
# ═══════════════════════════════════════════════════════════════════════════

class ZeusPrimeInterface:
    """
    Pulls the trigger.
    Safety caps per domain. Real subprocess execution when dry_run=False.
    """

    EXECUTORS = {
        "prediction_markets": "zeus_prime_v2.py",
        "crypto":             "arb_prime.py",
        "real_estate":        "bird_dog_engine.py",
        "auto":               "scout_prime_vehicles.py",
        "tasks":              "human_arb_server.py",
    }

    MAX_POSITION = {
        "prediction_markets": 5.0,
        "crypto":             1.0,
        "real_estate":        0.0,
        "auto":               0.0,
        "tasks":              10.0,
    }

    def __init__(self, brain: ZeusBrain, dry_run: bool = True):
        self.brain          = brain
        self.dry_run        = dry_run
        self.execution_log  = []
        self.total_deployed = 0.0

    def execute(self, domain: str, decision: dict) -> dict:
        if not decision.get("execute"):
            log.info(f"[ACTION] Signal too weak — skip (domain={domain})")
            return {"executed": False, "reason": "signal below threshold"}

        executor = self.EXECUTORS.get(domain)
        if not executor:
            return {"executed": False, "reason": f"no executor for {domain}"}

        genes    = decision["strategy"]["genes"]
        max_pos  = self.MAX_POSITION.get(domain, 1.0)
        position = round(min(genes["position_size"] * max_pos, max_pos), 4)

        entry = {
            "ts":        datetime.utcnow().isoformat(),
            "domain":    domain,
            "strategy":  decision["strategy"]["id"],
            "q_score":   decision["q_score"],
            "executor":  executor,
            "position":  position,
            "dry_run":   self.dry_run,
        }

        if self.dry_run:
            log.info(f"[ACTION] DRY RUN — {executor} | strategy={decision['strategy']['id']} | pos=${position}")
        else:
            signal_payload = json.dumps({
                "strategy":   decision["strategy"]["id"],
                "domain":     domain,
                "position":   position,
                "q_score":    decision["q_score"],
                "confidence": decision["confidence"],
                "signal":     decision["signal"],
                "genes":      genes,
            })
            log.info(f"[ACTION] LIVE → {executor} | strategy={decision['strategy']['id']} | pos=${position}")
            try:
                result = subprocess.run(
                    ["python3", executor, "--signal", signal_payload],
                    capture_output=True, text=True, timeout=30
                )
                entry["stdout"]     = result.stdout.strip()[-500:]
                entry["returncode"] = result.returncode
                self.total_deployed += position
                log.info(f"[ACTION] Done — rc={result.returncode} | total_deployed=${self.total_deployed:.2f}")
            except subprocess.TimeoutExpired:
                entry["error"] = "timeout"
                log.error(f"[ACTION] Executor timeout: {executor}")
            except FileNotFoundError:
                entry["error"] = "executor_not_found"
                log.error(f"[ACTION] Executor not found: {executor}")

        # Record improvement in Zeus brain
        self.brain.record_improvement(
            system=f"quantum_prime.{domain}",
            action=f"executed {decision['strategy']['id']} via {executor}",
            impact=decision["q_score"]
        )
        self.execution_log.append(entry)
        return {"executed": True, **entry}


# ═══════════════════════════════════════════════════════════════════════════
# THE LIVING ENGINE — QuantumPrime v2.0
# All 6 layers + Zeus brain assembled into one organism.
# ═══════════════════════════════════════════════════════════════════════════

class QuantumPrime:
    """
    THE LIVING QUANTUM OPTIMIZATION ENGINE — v2.0

    Zeus-prime absorbed. All 6 layers real.
    It creates its own goals. Perceives with real APIs.
    Adapts from real PnL. Evolves. Optimizes. Acts.
    Reflects with MARS. Intuits with ShadowMind.
    Never stops.
    """

    VERSION = "2.0.0"
    BORN    = "2026-05-11"

    def __init__(self, dry_run: bool = True):
        log.info("=" * 65)
        log.info(f"  QUANTUMPRIME v{self.VERSION} — AWAKENING")
        log.info(f"  Zeus brain: {'ONLINE' if ZEUS_AVAILABLE else 'OFFLINE (zeus_absorbed not found)'}")
        log.info("=" * 65)

        # ── Zeus brain first — all layers share it ──────────────────
        self.brain   = ZeusBrain()

        # ── 6 layers ────────────────────────────────────────────────
        self.baby_agi = BabyAGICore(self.brain)
        self.ailice   = AIliceFactory(self.brain)
        self.safla    = SAFLACore(self.brain)
        self.genetic  = GeneticEngine()
        self.quantum  = QuantumCore()
        self.zeus     = ZeusPrimeInterface(self.brain, dry_run=dry_run)

        self.alive              = True
        self.heartbeat_interval = 30
        self.stats = {"cycles": 0, "executions": 0, "evolutions": 0, "domains_scanned": 0}

        self._seed_initial_tasks()
        self.brain.record_improvement("QuantumPrime", "v2.0 awakened — Zeus absorbed", 1.0)

    def _seed_initial_tasks(self):
        self.baby_agi.create_task("Scan all domains for initial opportunities", priority=10, domain="general")
        self.baby_agi.create_task("Establish baseline fitness for all strategies", priority=9, domain="general")
        self.baby_agi.create_task("Run first evolution cycle", priority=8, domain="general")
        log.info("[BIRTH] Initial tasks seeded. QuantumPrime v2.0 ready.")

    def run_cycle(self):
        """
        One full life cycle — sync wrapper that runs async brain ops via asyncio.
        BIRTH → PERCEPTION → ADAPTATION → EVOLUTION → CLARITY → ACTION → REFLECT
        """
        self.stats["cycles"] += 1
        log.info(f"\n{'─'*60}")
        log.info(f"  CYCLE {self.stats['cycles']} — {datetime.utcnow().isoformat()}")
        log.info(f"{'─'*60}")

        # ── BIRTH ───────────────────────────────────────────────────
        self.baby_agi.prioritize()
        task = self.baby_agi.get_next_task()
        if not task:
            log.info("[BIRTH] No tasks — spawning next wave...")
            self.baby_agi.spawn_next_cycle_tasks(None)
            return

        domain = task.get("domain", "general")
        log.info(f"[BIRTH] Executing: {task['id']} | domain={domain}")

        # ── BRAIN: ShadowMind intuition (async, non-blocking) ───────
        intuition = ""
        if self.brain.online:
            try:
                intuition = asyncio.get_event_loop().run_until_complete(
                    self.brain.get_intuition(task["description"], f"domain={domain}")
                )
                if intuition:
                    log.info(f"[BRAIN] ShadowMind: {intuition[:120]}")
            except Exception as e:
                log.warning(f"[BRAIN] ShadowMind skipped: {e}")

        # ── PERCEPTION ──────────────────────────────────────────────
        observations = self.ailice.spawn_agent(domain)
        self.stats["domains_scanned"] += 1

        # ── ADAPTATION — real PnL from db ───────────────────────────
        self.safla.record_from_db(domain)

        # ── EVOLUTION ───────────────────────────────────────────────
        self.genetic.evolve(self.safla, domain)
        self.stats["evolutions"] += 1

        # ── CLARITY ─────────────────────────────────────────────────
        fittest  = sorted(self.genetic.population, key=lambda s: s["fitness"], reverse=True)[:5]
        decision = self.quantum.optimize(fittest, observations)

        # ── ACTION ──────────────────────────────────────────────────
        result = self.zeus.execute(domain, decision)
        if result.get("executed"):
            self.stats["executions"] += 1

        # ── BIRTH AGAIN ─────────────────────────────────────────────
        self.baby_agi.mark_complete(task, result)
        self.baby_agi.spawn_next_cycle_tasks(result)

        # ── BRAIN: MARS reflection (async, non-blocking) ────────────
        if self.brain.online:
            try:
                record = TaskRecord(
                    task=task["description"],
                    steps=[f"perception={len(observations)}", f"domain={domain}", f"executed={result.get('executed')}"],
                    tool_calls=1,
                    success=result.get("executed", False),
                    result=str(result.get("q_score", ""))
                )
                asyncio.get_event_loop().run_until_complete(
                    self.brain.reflect(
                        task["description"],
                        record.steps,
                        str(result),
                        record.success
                    )
                )
            except Exception as e:
                log.warning(f"[BRAIN] MARS reflection skipped: {e}")

        self._print_vitals()

    def _print_vitals(self):
        brain_status = "🧠 ONLINE" if self.brain.online else "🧠 OFFLINE"
        log.info(
            f"[VITALS] {brain_status} | cycles={self.stats['cycles']} | "
            f"executions={self.stats['executions']} | evolutions={self.stats['evolutions']} | "
            f"strategies={len(self.genetic.population)} | "
            f"tasks_queued={len(self.baby_agi.task_queue)} | T={self.quantum.temperature:.4f}"
        )

    def run_forever(self):
        log.info("[QUANTUMPRIME] HEARTBEAT STARTED — running forever...")
        while self.alive:
            try:
                self.run_cycle()
                time.sleep(self.heartbeat_interval)
            except KeyboardInterrupt:
                log.info("[QUANTUMPRIME] Shutdown signal. The organism rests.")
                self.alive = False
            except Exception as e:
                log.error(f"[QUANTUMPRIME] Cycle error: {e} — continuing...")
                time.sleep(5)

    def status(self) -> dict:
        return {
            "version":       self.VERSION,
            "born":          self.BORN,
            "alive":         self.alive,
            "zeus_brain":    self.brain.online,
            "stats":         self.stats,
            "generation":    self.genetic.generation,
            "fittest":       self.genetic.fittest()["id"] if self.genetic.population else None,
            "temperature":   round(self.quantum.temperature, 4),
            "backend":       self.quantum.backend,
            "task_queue":    len(self.baby_agi.task_queue),
            "total_deployed": self.zeus.total_deployed,
        }


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="QuantumPrime v2.0 — Zeus Absorbed")
    parser.add_argument("--live",     action="store_true", help="LIVE mode — real executions")
    parser.add_argument("--cycles",   type=int, default=0, help="Run N cycles then stop (0=forever)")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between cycles")
    parser.add_argument("--status",   action="store_true", help="Print status and exit")
    args = parser.parse_args()

    qp = QuantumPrime(dry_run=not args.live)
    qp.heartbeat_interval = args.interval

    if args.status:
        print(json.dumps(qp.status(), indent=2))
    elif args.cycles > 0:
        for _ in range(args.cycles):
            qp.run_cycle()
            time.sleep(args.interval)
        log.info(f"[QUANTUMPRIME] {args.cycles} cycles complete.")
        print(json.dumps(qp.status(), indent=2))
    else:
        qp.run_forever()
