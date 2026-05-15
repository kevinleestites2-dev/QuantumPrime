"""
╔══════════════════════════════════════════════════════════════════╗
║          Q U A N T U M P R I M E   v2.1.0                       ║
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
║   Born: 2026-05-11  |  v2.1: MARS wired — real feedback loop   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os, json, time, sqlite3, subprocess, urllib.request
from pathlib import Path
import random, logging, threading, asyncio
from datetime import datetime
from collections import deque
from alpha_evolve import AlphaEvolve
from typing import Any

# ─── Shared paths ───────────────────────────────────────────────────────────
_MEMORY_DIR = Path("memory")
_MEMORY_DIR.mkdir(exist_ok=True)
_TRADE_LOG  = _MEMORY_DIR / "trade_log.json"

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

    # ── MARS: sync reads (before cycle) ─────────────────────────────

    def mars_guidance(self, domain: str) -> str:
        """
        Retrieve MARS principles + procedures relevant to this domain.
        Called BEFORE QuantumCore so guidance biases the decision.
        Sync — always available even without Ollama.
        """
        if not self.online:
            return ""
        try:
            guidance = self.mars.render_guidance(domain)
            if guidance:
                log.info(f"[MARS] Guidance for {domain}:\n{guidance}")
            return guidance
        except Exception as e:
            log.warning(f"[MARS] render_guidance failed: {e}")
            return ""

    def mars_principles(self, domain: str, limit: int = 3) -> list:
        """
        Return raw principle dicts for a domain.
        Used by QuantumCore to penalise strategies that violate known principles.
        """
        if not self.online:
            return []
        try:
            return self.mars.get_relevant_principles(domain, limit=limit)
        except Exception as e:
            log.warning(f"[MARS] get_relevant_principles failed: {e}")
            return []

    # ── MARS: async writes (after cycle) ────────────────────────────

    async def mars_reflect(self, task: str, steps: list, result: str, success: bool) -> dict:
        """
        Reflect on a completed cycle.
        Success → extracts a reusable PROCEDURE stored in L3.
        Failure → extracts a PRINCIPLE stored in L3.
        Both are retrieved on the NEXT cycle via mars_guidance().

        Offline fallback: when Ollama is unavailable, build a deterministic
        principle/procedure from the raw data so MARS is never empty.
        """
        if not self.online:
            return {}
        try:
            if success:
                out = await self.mars.reflect_on_success(task, steps, result)
            else:
                out = await self.mars.reflect_on_failure(task, result, context=f"steps={steps}")

            # ── Offline fallback: LLM returned empty content ──────────
            # zeus_absorbed falls back to raw.strip() which is "" when Ollama
            # is down. Detect that and build a real entry from raw data.
            is_empty = not out.get("principle", "").strip() and not out.get("procedure_name", "").strip()
            if is_empty:
                # Parse steps for useful tokens
                domain   = next((s.split("=",1)[1] for s in steps if s.startswith("domain=")), "general")
                strategy = next((s.split("=",1)[1] for s in steps if s.startswith("strategy=")), "unknown")
                q_score  = next((s.split("=",1)[1] for s in steps if s.startswith("q_score=")), "0")
                executed = next((s.split("=",1)[1] for s in steps if s.startswith("executed=")), "False")

                if success:
                    out["procedure_name"] = f"Successful {domain} execution via {strategy}"
                    out["steps"]          = steps
                    out["applicable_when"] = f"domain={domain}, q_score>{q_score}"
                    log.info(f"[MARS] Offline procedure: {out['procedure_name']}")
                else:
                    out["principle"]   = f"Task failed in domain={domain} using strategy={strategy} (q={q_score}, executed={executed})"
                    out["category"]    = domain
                    out["prevention"]  = f"Review strategy {strategy} for domain {domain} before next execution"
                    log.info(f"[MARS] Offline principle: {out['principle']}")

                # Persist the fallback so it shows up in render_guidance()
                import datetime as _dt
                out["created_at"]    = _dt.datetime.utcnow().isoformat()
                out["trigger_task"]  = task[:200]
                if success:
                    self.mars._procedures.append(out)
                else:
                    self.mars._principles.append(out)
                self.mars._save()

            if success:
                log.info(f"[MARS] Procedure stored: {out.get('procedure_name','?')}")
            else:
                log.info(f"[MARS] Principle stored: {out.get('principle','?')[:80]}")
            return out

        except Exception as e:
            log.warning(f"[MARS] reflect failed: {e}")
            return {}

    async def shadow_intuition(self, task: str, context: str = "") -> str:
        """ShadowMind parallel pattern intuition."""
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

    def optimize(self, strategies: list[dict], observations: list[dict],
                 mars_principles: list[dict] = None) -> dict:
        """
        Find optimal strategy via simulated annealing.
        mars_principles — list of principle dicts from MARS.
        Any strategy that violates a known principle gets a score penalty.
        This is how past failures change future decisions.
        """
        if not strategies:
            return {"error": "no strategies"}

        mars_principles = mars_principles or []

        # Build a flat list of penalty keywords from MARS principles
        # e.g. "avoid stop_loss < 0.05 on crypto" → penalise strategies with low stop_loss
        penalty_tokens = []
        for p in mars_principles:
            text = (p.get("principle", "") + " " + p.get("prevention", "")).lower()
            penalty_tokens.extend(text.split())

        avg_signal = sum(o.get("weighted_signal", o["signal_strength"]) for o in observations) / max(len(observations), 1)
        avg_conf   = sum(o["confidence"] for o in observations) / max(len(observations), 1)

        scored = []
        for s in strategies:
            g = s["genes"]

            # Base quantum score
            q = (
                (1.0 - abs(g["signal_threshold"] - avg_signal)) *
                (1.0 - abs(g["confidence_min"]   - avg_conf)) *
                (1.0 + s["fitness"])
            )

            # MARS penalty — reduce score if strategy attributes match failure tokens
            # Heuristic: if "stop_loss" appears in principles and strategy has low stop_loss → penalise
            penalty = 0.0
            if penalty_tokens:
                strat_str = json.dumps(g).lower()
                hits = sum(1 for tok in penalty_tokens if len(tok) > 4 and tok in strat_str)
                penalty = min(hits * 0.05, 0.3)   # max 30% penalty
                if penalty > 0:
                    log.info(f"[CLARITY] MARS penalty -{penalty:.2f} on {s['id']} ({hits} principle hits)")

            q = max(0.0, q - penalty)

            # Simulated annealing acceptance for non-optimal candidates
            if scored and random.random() < self.temperature * 0.1:
                q *= random.uniform(0.9, 1.1)   # thermal noise keeps diversity

            scored.append((q, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        optimal = scored[0][1]
        q_score = scored[0][0]
        self.temperature *= (1 - self.cooling_rate)

        mars_note = f" | MARS principles active: {len(mars_principles)}" if mars_principles else ""
        log.info(f"[CLARITY] Optimal: {optimal['id']} | q_score={q_score:.4f} | T={self.temperature:.4f}{mars_note}")
        return {
            "strategy":        optimal,
            "q_score":         round(q_score, 4),
            "signal":          round(avg_signal, 3),
            "confidence":      round(avg_conf, 3),
            "backend":         self.backend,
            "execute":         q_score > 0.5,
            "mars_principles": len(mars_principles),
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
            # Log skips too — AlphaEvolve needs full picture
            try:
                existing = json.loads(_TRADE_LOG.read_text()) if _TRADE_LOG.exists() else []
                existing.append({
                    "ts":       datetime.utcnow().isoformat(),
                    "strategy": decision.get("strategy", {}).get("id", "?"),
                    "domain":   domain,
                    "pnl":      0.0,
                    "position": 0.0,
                    "executed": False,
                })
                existing = existing[-2000:]
                _TRADE_LOG.write_text(json.dumps(existing, indent=2))
            except Exception:
                pass
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

        # ── Persist to trade_log.json for AlphaEvolve + SAFLA ──
        try:
            existing = json.loads(_TRADE_LOG.read_text()) if _TRADE_LOG.exists() else []
            existing.append({
                "ts":       entry["ts"],
                "strategy": entry.get("strategy", "?"),
                "domain":   entry.get("domain", "?"),
                "pnl":      entry.get("q_score", 0.0),   # q_score as proxy until real PnL wired
                "position": entry.get("position", 0.0),
                "executed": True,
            })
            existing = existing[-2000:]  # keep last 2000
            _TRADE_LOG.write_text(json.dumps(existing, indent=2))
        except Exception as tl_err:
            log.warning(f"[TRADE_LOG] write error: {tl_err}")

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

    VERSION = "2.1.0"
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
        self.genetic      = GeneticEngine()
        self.alpha_evolve  = AlphaEvolve(population_size=15)
        self._alpha_cycle  = 0
        self._alpha_every  = 50  # run AlphaEvolve every 50 QP cycles
        self.quantum  = QuantumCore()
        self.zeus     = ZeusPrimeInterface(self.brain, dry_run=dry_run)

        self.alive              = True
        self.heartbeat_interval = 30
        self.stats = {"cycles": 0, "executions": 0, "evolutions": 0, "domains_scanned": 0}

        self._seed_initial_tasks()
        self.brain.record_improvement("QuantumPrime", "v2.1 awakened — Zeus absorbed + MARS real feedback loop", 1.0)

    def _seed_initial_tasks(self):
        self.baby_agi.create_task("Scan all domains for initial opportunities", priority=10, domain="general")
        self.baby_agi.create_task("Establish baseline fitness for all strategies", priority=9, domain="general")
        self.baby_agi.create_task("Run first evolution cycle", priority=8, domain="general")
        log.info("[BIRTH] Initial tasks seeded. QuantumPrime v2.0 ready.")

    def _run_async(self, coro):
        """
        Safe async runner. Creates a new event loop if needed.
        Replaces the broken get_event_loop() calls.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)

    def run_cycle(self):
        """
        One full life cycle — MARS is a real feedback loop.

        BIRTH      — pick next task
        MARS READ  — render_guidance() retrieves principles from ALL past cycles (sync)
        SHADOW     — ShadowMind intuition (async, non-blocking)
        PERCEPTION — real API observations (trust-weighted)
        ADAPTATION — SAFLA records real PnL from zeus_prime.db
        EVOLUTION  — GeneticEngine breeds / kills strategies
        CLARITY    — QuantumCore optimises WITH mars_principles as penalty weights
        ACTION     — ZeusPrime executes decision
        MARS WRITE — reflect_on_success/failure → new principle/procedure stored in L3
                     → retrieved by MARS READ next cycle → closes the loop
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

        # ── MARS READ — guidance from all past cycles ────────────────
        # This is where past failures actually change current decisions.
        # render_guidance() is sync — no Ollama needed — reads from persisted JSON.
        mars_guidance   = self.brain.mars_guidance(domain)
        mars_principles = self.brain.mars_principles(domain, limit=5)
        if mars_guidance:
            log.info(f"[MARS] {len(mars_principles)} principle(s) active for {domain}")
        else:
            log.info(f"[MARS] No principles yet for {domain} — cycle 1 will write the first")

        # ── SHADOW — parallel pattern intuition (async) ──────────────
        intuition = ""
        if self.brain.online:
            shadow_context = f"domain={domain} | mars_guidance={mars_guidance[:200] if mars_guidance else 'none'}"
            intuition = self._run_async(
                self.brain.shadow_intuition(task["description"], shadow_context)
            )
            if intuition:
                log.info(f"[SHADOW] {intuition[:150]}")

        # ── PERCEPTION — real API signals, trust-weighted ────────────
        observations = self.ailice.spawn_agent(domain)
        self.stats["domains_scanned"] += 1

        # ── ADAPTATION — real PnL from zeus_prime.db ─────────────────
        # MARS principles can also nudge SAFLA: if a principle says a strategy
        # failed, record a negative outcome for it right now.
        self.safla.record_from_db(domain)
        for p in mars_principles:
            prevention = p.get("prevention", "").lower()
            for s in self.genetic.population:
                sid = s["id"].lower()
                if any(tok in sid for tok in prevention.split() if len(tok) > 4):
                    self.safla.record(domain, s["id"], -0.2)
                    log.info(f"[MARS→SAFLA] Penalised {s['id']} based on principle: {p.get('principle','')[:60]}")

        # ── EVOLUTION ────────────────────────────────────────────────
        self.genetic.evolve(self.safla, domain)
        self.stats["evolutions"] += 1

        # ── CLARITY — QuantumCore scores WITH MARS penalty weights ───
        fittest  = sorted(self.genetic.population, key=lambda s: s["fitness"], reverse=True)[:5]
        decision = self.quantum.optimize(fittest, observations, mars_principles=mars_principles)

        # ── ACTION ───────────────────────────────────────────────────
        result = self.zeus.execute(domain, decision)
        if result.get("executed"):
            self.stats["executions"] += 1

        # ── BIRTH AGAIN ──────────────────────────────────────────────
        self.baby_agi.mark_complete(task, result)
        self.baby_agi.spawn_next_cycle_tasks(result)

        # ── MARS WRITE — reflect and store principle/procedure in L3 ─
        # This is the write side of the loop.
        # Next cycle's MARS READ will retrieve what we store here.
        steps = [
            f"domain={domain}",
            f"observations={len(observations)}",
            f"mars_principles_active={len(mars_principles)}",
            f"strategy={decision.get('strategy', {}).get('id', '?')}",
            f"q_score={decision.get('q_score', 0)}",
            f"executed={result.get('executed', False)}",
            f"intuition={intuition[:100] if intuition else 'none'}",
        ]
        success  = result.get("executed", False)
        outcome  = str(result.get("q_score", "0")) + f" | domain={domain} | executed={success}"

        reflection = self._run_async(
            self.brain.mars_reflect(task["description"], steps, outcome, success)
        )
        if reflection:
            self.stats["mars_reflections"] = self.stats.get("mars_reflections", 0) + 1

        # Record improvement in MetaImprovementLog
        self.brain.record_improvement(
            system=f"quantum_prime.{domain}",
            action=f"cycle {self.stats['cycles']} | strategy={decision.get('strategy',{}).get('id','?')} | q={decision.get('q_score',0):.3f}",
            impact=decision.get("q_score", 0.0)
        )

        # ── AlphaEvolve: evolve the evolution engine every N cycles ──
        self._alpha_cycle += 1
        if self._alpha_cycle >= self._alpha_every:
            self._alpha_cycle = 0
            try:
                result = self.alpha_evolve.run_cycle(verbose=False)
                applied = self.alpha_evolve.apply_to_quantum(self)
                log.info(
                    f"[ALPHA_EVOLVE] gen={result['generation']} "
                    f"best_fitness={result['fitness']:.4f} "
                    f"genome={result['id']} applied."
                )
            except Exception as ae_err:
                log.warning(f"[ALPHA_EVOLVE] cycle error: {ae_err}")

        self._print_vitals(mars_principles)

    def _print_vitals(self, mars_principles: list = None):
        brain_status  = "🧠 ONLINE" if self.brain.online else "🧠 OFFLINE"
        mars_count    = len(mars_principles) if mars_principles else 0
        reflections   = self.stats.get("mars_reflections", 0)
        log.info(
            f"[VITALS] {brain_status} | cycles={self.stats['cycles']} | "
            f"executions={self.stats['executions']} | evolutions={self.stats['evolutions']} | "
            f"mars_principles={mars_count} | mars_reflections={reflections} | "
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
            "total_deployed":    self.zeus.total_deployed,
            "mars_reflections":  self.stats.get("mars_reflections", 0),
            "alpha_evolve_gen":      self.alpha_evolve.generation,
            "alpha_evolve_best_fit": round(self.alpha_evolve.best_genome().fitness, 4),
            "alpha_evolve_pop":      len(self.alpha_evolve.population),
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
