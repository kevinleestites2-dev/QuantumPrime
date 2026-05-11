# QuantumPrime v2.1 — The Living Optimization Engine

> Not a trading bot. Not a task bot. A UNIVERSAL OPTIMIZATION ENGINE — alive.

## Architecture

```
BRAIN      → zeus_absorbed.py   (FourLayerMemory + OllamaRouter + MARS + ShadowMind + BayesianTrust)
BIRTH      → BabyAGICore        (generates its own goals)
PERCEPTION → AIliceFactory      (real APIs: Polymarket / Kalshi / Binance / RentAHuman)
ADAPTATION → SAFLACore          (real PnL from zeus_prime.db)
EVOLUTION  → GeneticEngine      (breeds winners, kills losers)
CLARITY    → QuantumCore        (simulated annealing optimizer + MARS penalty weights)
ACTION     → ZeusPrimeInterface (live executor with safety caps)
```

## MARS Feedback Loop

Every cycle writes a principle or procedure to L3 memory.
Every cycle reads them back before making decisions.
Past failures change future strategy scores — automatically.

```
Cycle N   → reflect_on_failure() → stores PRINCIPLE in L3
Cycle N+1 → render_guidance()    → reads PRINCIPLE → penalises matching strategies
```

## Files

| File | Purpose |
|---|---|
| `quantum_prime_v2.py` | Main engine — all 6 layers + Zeus brain + MARS loop |
| `zeus_absorbed.py` | The King — memory, LLM routing, MARS, ShadowMind |

## Run (Termux)

```bash
# Clone
git clone https://github.com/kevinleestites2-dev/QuantumPrime
cd QuantumPrime

# Dry run — 3 cycles
python3 quantum_prime_v2.py --cycles 3

# Run forever (dry)
python3 quantum_prime_v2.py

# LIVE mode (real executions)
python3 quantum_prime_v2.py --live

# Status check
python3 quantum_prime_v2.py --status
```

## Environment Variables

```bash
KALSHI_API_KEY_ID=your_key       # prediction markets
RAH_API_KEY=your_key             # RentAHuman task engine
```

Polymarket and Binance are free — no keys needed.

