"""
Zeus-Prime Absorption Layer v1.0
16 systems extracted from the King (2677 lines)
"""
import sys, os, uuid
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json, time, sqlite3, hashlib, logging, re, threading, subprocess, shutil, ast
import datetime
from datetime import datetime as _dt
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from enum import Enum, auto

try:
    import httpx; HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
try:
    import yaml; HAS_YAML = True
except ImportError:
    HAS_YAML = False

IS_TERMUX = os.path.isdir("/data/data/com.termux")
HOME = Path.home()
ZEUS_DIR = HOME / ".zeus_prime"
DB_PATH = ZEUS_DIR / "memory.db"
SKILLS_DIR = ZEUS_DIR / "skills"
FORGE_DIR = ZEUS_DIR / "forge"
AGENTS_DIR = ZEUS_DIR / "agents"
SNAPSHOT_DIR = ZEUS_DIR / "snapshots"
LOG_PATH = ZEUS_DIR / "zeus.log"
CONFIG_PATH = ZEUS_DIR / "config.json"
TRUST_LEDGER_PATH = ZEUS_DIR / "trust_ledger.json"
MARS_LOG_PATH = ZEUS_DIR / "mars_reflections.json"
META_IMPROVEMENT_PATH = ZEUS_DIR / "meta_improvements.json"
for _d in (ZEUS_DIR, SKILLS_DIR, FORGE_DIR, AGENTS_DIR, SNAPSHOT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("ZeusAbsorbed")

# ════════════════════════════════════════════════════════════
# ZeusConfig
# ════════════════════════════════════════════════════════════

class ZeusConfig:
    """Global configuration with sensible defaults for Termux + Ollama."""

    ollama_host: str = "http://localhost:11434"

    # Model routing table
    model_fast: str = "phi4-mini"
    model_code: str = "qwen2.5-coder:7b"
    model_reason: str = "llama3.1"
    model_vision: str = "llava"
    model_embed: str = "nomic-embed-text"
    model_trivial: str = "stable-zephyr:3b"

    # Cloud fallback (optional)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    cloud_model: str = "gpt-4o-mini"

    # Memory
    l1_max_tokens: int = 800
    l2_max_tokens: int = 500
    l3_fts_limit: int = 20

    # NEXUS
    max_agents: int = 8
    trust_threshold: float = 0.6

    # Forge
    forge_timeout: int = 30

    # Voice
    whisper_model_size: str = "base"
    tts_voice: str = "en-US-GuyNeural"
    wake_words: List[str] = field(default_factory=lambda: ["zeus", "hey zeus"])

    # Simulation
    sim_shell: str = "/bin/bash"

    @classmethod
    def load(cls) -> "ZeusConfig":
        if CONFIG_PATH.exists():
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            known = {f.name for f in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in raw.items() if k in known}
            return cls(**filtered)
        return cls()

    def save(self) -> None:
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), indent=2, default=str),
            encoding="utf-8",
        )


# ###########################################################################
#  SECTION 2 -- MULTI-MODEL ROUTER  (Feature 7)
# ###########################################################################



# ════════════════════════════════════════════════════════════
# TaskComplexity
# ════════════════════════════════════════════════════════════

class TaskComplexity(Enum):
    TRIVIAL = auto()
    FAST = auto()
    CODE = auto()
    REASON = auto()
    VISION = auto()
    EMBED = auto()




# ════════════════════════════════════════════════════════════
# OllamaRouter
# ════════════════════════════════════════════════════════════

class OllamaRouter:
    """Routes prompts to the optimal local Ollama model."""

    CODE_KEYWORDS = re.compile(
        r"\b(code|function|class|debug|refactor|implement|script|program|"
        r"python|javascript|rust|go|sql|html|css|api|endpoint|bug|error|"
        r"compile|test|unittest|pytest|fix|patch|diff|merge)\b",
        re.IGNORECASE,
    )
    REASON_KEYWORDS = re.compile(
        r"\b(explain|analyze|compare|evaluate|plan|design|architect|"
        r"strategy|reason|proof|derive|theorem|complex|tradeoff|"
        r"pros and cons|step.by.step|think|why|how does)\b",
        re.IGNORECASE,
    )
    VISION_KEYWORDS = re.compile(
        r"\b(image|photo|picture|screenshot|camera|see|look|visual|"
        r"describe this|what is this|ocr|scan)\b",
        re.IGNORECASE,
    )
    TRIVIAL_PATTERNS = re.compile(
        r"^(hi|hello|hey|thanks|ok|yes|no|sure|bye|good|great|"
        r"what time|date|weather)\b",
        re.IGNORECASE,
    )

    def __init__(self, cfg: ZeusConfig):
        self.cfg = cfg
        self._available_models: Set[str] = set()
        self._last_check = 0.0

    async def _refresh_models(self) -> None:
        now = time.time()
        if now - self._last_check < 60:
            return
        self._last_check = now
        try:
            if HAS_HTTPX:
                async with httpx.AsyncClient(timeout=5) as c:
                    r = await c.get(f"{self.cfg.ollama_host}/api/tags")
                    if r.status_code == 200:
                        data = r.json()
                        self._available_models = {
                            m["name"] for m in data.get("models", [])
                        }
            else:
                proc = await asyncio.create_subprocess_exec(
                    "curl", "-s", f"{self.cfg.ollama_host}/api/tags",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await proc.communicate()
                if stdout:
                    data = json.loads(stdout)
                    self._available_models = {
                        m["name"] for m in data.get("models", [])
                    }
        except Exception:
            pass

    def classify(self, prompt: str, has_image: bool = False) -> TaskComplexity:
        if has_image:
            return TaskComplexity.VISION
        if self.VISION_KEYWORDS.search(prompt):
            return TaskComplexity.VISION
        if self.TRIVIAL_PATTERNS.match(prompt.strip()):
            return TaskComplexity.TRIVIAL
        if self.CODE_KEYWORDS.search(prompt):
            return TaskComplexity.CODE
        if self.REASON_KEYWORDS.search(prompt):
            return TaskComplexity.REASON
        if len(prompt.split()) < 10:
            return TaskComplexity.FAST
        return TaskComplexity.REASON

    def select_model(self, complexity: TaskComplexity) -> str:
        mapping = {
            TaskComplexity.TRIVIAL: self.cfg.model_trivial,
            TaskComplexity.FAST: self.cfg.model_fast,
            TaskComplexity.CODE: self.cfg.model_code,
            TaskComplexity.REASON: self.cfg.model_reason,
            TaskComplexity.VISION: self.cfg.model_vision,
            TaskComplexity.EMBED: self.cfg.model_embed,
        }
        chosen = mapping.get(complexity, self.cfg.model_fast)
        if self._available_models and chosen not in self._available_models:
            for fallback in [self.cfg.model_fast, self.cfg.model_reason]:
                if fallback in self._available_models:
                    log.warning("Model %s unavailable, falling back to %s", chosen, fallback)
                    return fallback
            if self._available_models:
                return next(iter(self._available_models))
        return chosen

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        images: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        await self._refresh_models()
        if model is None:
            complexity = self.classify(prompt, has_image=bool(images))
            model = self.select_model(complexity)

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["system"] = system
        if images:
            payload["images"] = images

        try:
            if HAS_HTTPX:
                async with httpx.AsyncClient(timeout=120) as c:
                    r = await c.post(
                        f"{self.cfg.ollama_host}/api/generate",
                        json=payload,
                    )
                    r.raise_for_status()
                    return r.json().get("response", "")
            else:
                proc = await asyncio.create_subprocess_exec(
                    "curl", "-s", "-X", "POST",
                    f"{self.cfg.ollama_host}/api/generate",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await proc.communicate()
                if stdout:
                    return json.loads(stdout).get("response", "")
                return "[Ollama unavailable]"
        except Exception as exc:
            log.error("Ollama generate failed: %s", exc)
            return await self._cloud_fallback(prompt, system)

    async def embed(self, text: str) -> List[float]:
        payload = {"model": self.cfg.model_embed, "prompt": text}
        try:
            if HAS_HTTPX:
                async with httpx.AsyncClient(timeout=30) as c:
                    r = await c.post(
                        f"{self.cfg.ollama_host}/api/embeddings",
                        json=payload,
                    )
                    r.raise_for_status()
                    return r.json().get("embedding", [])
            else:
                proc = await asyncio.create_subprocess_exec(
                    "curl", "-s", "-X", "POST",
                    f"{self.cfg.ollama_host}/api/embeddings",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await proc.communicate()
                if stdout:
                    return json.loads(stdout).get("embedding", [])
                return []
        except Exception as exc:
            log.error("Embedding failed: %s", exc)
            return []

    async def _cloud_fallback(self, prompt: str, system: str = "") -> str:
        if not self.cfg.openai_api_key:
            return "[No model available -- Ollama offline and no cloud API key set]"
        if not HAS_HTTPX:
            return "[Cloud fallback requires httpx]"
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.cfg.openai_api_key}"},
                    json={"model": self.cfg.cloud_model, "messages": messages},
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            log.error("Cloud fallback failed: %s", exc)
            return f"[Error: {exc}]"


# ###########################################################################
#  SECTION 3 -- FOUR-LAYER MEMORY  (Feature 3)
# ###########################################################################



# ════════════════════════════════════════════════════════════
# MemoryL1Core
# ════════════════════════════════════════════════════════════

class MemoryL1Core:
    """L1 Core Memory -- project context, frozen at session start (~800 tokens)."""

    def __init__(self, max_tokens: int = 800):
        self.max_tokens = max_tokens
        self._data: Dict[str, str] = {}
        self._frozen = False

    def set(self, key: str, value: str) -> None:
        if self._frozen:
            return
        self._data[key] = value

    def freeze(self) -> None:
        self._frozen = True
        log.info("L1 Core Memory frozen with %d entries", len(self._data))

    def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    def render(self) -> str:
        lines = [f"[{k}]: {v}" for k, v in self._data.items()]
        text = "\n".join(lines)
        words = text.split()
        if len(words) > self.max_tokens:
            text = " ".join(words[: self.max_tokens]) + "..."
        return text

    def to_dict(self) -> Dict[str, str]:
        return dict(self._data)




# ════════════════════════════════════════════════════════════
# MemoryL2UserProfile
# ════════════════════════════════════════════════════════════

class MemoryL2UserProfile:
    """L2 User Profile -- preferences, style, stack (~500 tokens)."""

    def __init__(self, max_tokens: int = 500):
        self.max_tokens = max_tokens
        self._profile: Dict[str, Any] = {
            "preferences": {},
            "style": "",
            "stack": [],
            "corrections": [],
        }
        self._profile_path = ZEUS_DIR / "user_profile.json"
        self._load()

    def _load(self) -> None:
        if self._profile_path.exists():
            try:
                self._profile = json.loads(
                    self._profile_path.read_text(encoding="utf-8")
                )
            except Exception:
                pass

    def _save(self) -> None:
        self._profile_path.write_text(
            json.dumps(self._profile, indent=2, default=str),
            encoding="utf-8",
        )

    def update_preference(self, key: str, value: Any) -> None:
        self._profile["preferences"][key] = value
        self._save()

    def set_style(self, style: str) -> None:
        self._profile["style"] = style
        self._save()

    def add_stack(self, tech: str) -> None:
        if tech not in self._profile["stack"]:
            self._profile["stack"].append(tech)
            self._save()

    def add_correction(self, correction: str) -> None:
        self._profile["corrections"].append(correction)
        if len(self._profile["corrections"]) > 50:
            self._profile["corrections"] = self._profile["corrections"][-50:]
        self._save()

    def render(self) -> str:
        parts = []
        if self._profile["preferences"]:
            parts.append("Preferences: " + json.dumps(self._profile["preferences"]))
        if self._profile["style"]:
            parts.append(f"Style: {self._profile['style']}")
        if self._profile["stack"]:
            parts.append("Stack: " + ", ".join(self._profile["stack"]))
        if self._profile["corrections"]:
            recent = self._profile["corrections"][-5:]
            parts.append("Recent corrections: " + "; ".join(recent))
        text = "\n".join(parts)
        words = text.split()
        if len(words) > self.max_tokens:
            text = " ".join(words[: self.max_tokens]) + "..."
        return text




# ════════════════════════════════════════════════════════════
# MemoryL3LongTerm
# ════════════════════════════════════════════════════════════

class MemoryL3LongTerm:
    """L3 Long-term Memory -- SQLite FTS5 searchable history."""

    def __init__(self, db_path: Path = DB_PATH, fts_limit: int = 20):
        self.db_path = db_path
        self.fts_limit = fts_limit
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                embedding TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                id, category, content,
                content='memories',
                content_rowid='rowid'
            );
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(id, category, content)
                VALUES (new.id, new.category, new.content);
            END;
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, id, category, content)
                VALUES ('delete', old.id, old.category, old.content);
            END;
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, id, category, content)
                VALUES ('delete', old.id, old.category, old.content);
                INSERT INTO memories_fts(id, category, content)
                VALUES (new.id, new.category, new.content);
            END;

            CREATE TABLE IF NOT EXISTS task_history (
                id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                result TEXT,
                tool_calls INTEGER DEFAULT 0,
                self_corrections INTEGER DEFAULT 0,
                user_corrections INTEGER DEFAULT 0,
                duration_s REAL DEFAULT 0,
                skill_extracted INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reflections (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                trigger_task_id TEXT,
                insight TEXT NOT NULL,
                principles TEXT DEFAULT '[]',
                procedures TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def store(
        self,
        category: str,
        content: str,
        metadata: Optional[Dict] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        mem_id = f"mem-{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT INTO memories (id, category, content, metadata, embedding, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                mem_id,
                category,
                content,
                json.dumps(metadata or {}),
                json.dumps(embedding or []),
                now,
            ),
        )
        self.conn.commit()
        return mem_id

    def search(self, query: str, limit: Optional[int] = None) -> List[Dict]:
        limit = limit or self.fts_limit
        safe_query = re.sub(r"[^\w\s]", "", query)
        tokens = safe_query.split()
        if not tokens:
            return []
        fts_query = " OR ".join(tokens)
        rows = self.conn.execute(
            "SELECT m.id, m.category, m.content, m.metadata, m.created_at "
            "FROM memories_fts f JOIN memories m ON f.id = m.id "
            "WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?",
            (fts_query, limit),
        ).fetchall()
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "category": row[1],
                "content": row[2],
                "metadata": json.loads(row[3]),
                "created_at": row[4],
            })
            self.conn.execute(
                "UPDATE memories SET access_count = access_count + 1 WHERE id = ?",
                (row[0],),
            )
        self.conn.commit()
        return results

    def store_task(self, task_record: Dict) -> str:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT INTO task_history "
            "(id, task, result, tool_calls, self_corrections, user_corrections, "
            "duration_s, skill_extracted, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task_id,
                task_record.get("task", ""),
                task_record.get("result", ""),
                task_record.get("tool_calls", 0),
                task_record.get("self_corrections", 0),
                task_record.get("user_corrections", 0),
                task_record.get("duration_s", 0),
                task_record.get("skill_extracted", 0),
                now,
            ),
        )
        self.conn.commit()
        return task_id

    def store_reflection(self, reflection: Dict) -> str:
        ref_id = f"ref-{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT INTO reflections "
            "(id, type, trigger_task_id, insight, principles, procedures, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ref_id,
                reflection.get("type", "principle"),
                reflection.get("trigger_task_id", ""),
                reflection.get("insight", ""),
                json.dumps(reflection.get("principles", [])),
                json.dumps(reflection.get("procedures", [])),
                now,
            ),
        )
        self.conn.commit()
        return ref_id

    def get_recent_tasks(self, limit: int = 10) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM task_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        cols = [
            "id", "task", "result", "tool_calls", "self_corrections",
            "user_corrections", "duration_s", "skill_extracted", "created_at",
        ]
        return [dict(zip(cols, row)) for row in rows]

    def get_reflections(self, ref_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        if ref_type:
            rows = self.conn.execute(
                "SELECT * FROM reflections WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                (ref_type, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM reflections ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        cols = [
            "id", "type", "trigger_task_id", "insight",
            "principles", "procedures", "created_at",
        ]
        results = []
        for row in rows:
            d = dict(zip(cols, row))
            d["principles"] = json.loads(d["principles"])
            d["procedures"] = json.loads(d["procedures"])
            results.append(d)
        return results

    def stats(self) -> Dict[str, int]:
        mem_count = self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        task_count = self.conn.execute("SELECT COUNT(*) FROM task_history").fetchone()[0]
        ref_count = self.conn.execute("SELECT COUNT(*) FROM reflections").fetchone()[0]
        return {"memories": mem_count, "tasks": task_count, "reflections": ref_count}




# ════════════════════════════════════════════════════════════
# MemoryL4SkillsLibrary
# ════════════════════════════════════════════════════════════

class MemoryL4SkillsLibrary:
    """L4 Skills Library -- reusable procedures, names only until needed (near-zero token cost)."""

    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir
        self._index: Dict[str, Dict[str, str]] = {}
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._index.clear()
        for fp in self.skills_dir.glob("*.md"):
            name = fp.stem
            first_line = ""
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip().lstrip("# ")
            except Exception:
                pass
            self._index[name] = {
                "path": str(fp),
                "title": first_line or name,
            }

    def list_names(self) -> List[str]:
        return list(self._index.keys())

    def render_index(self) -> str:
        if not self._index:
            return "(no skills)"
        return "\n".join(
            f"- {name}: {info['title']}" for name, info in self._index.items()
        )

    def load_skill(self, name: str) -> Optional[str]:
        info = self._index.get(name)
        if not info:
            return None
        try:
            return Path(info["path"]).read_text(encoding="utf-8")
        except Exception:
            return None

    def save_skill(self, name: str, content: str) -> Path:
        fp = self.skills_dir / f"{name}.md"
        fp.write_text(content, encoding="utf-8")
        self._rebuild_index()
        log.info("Skill saved: %s", name)
        return fp

    def delete_skill(self, name: str) -> bool:
        info = self._index.get(name)
        if not info:
            return False
        try:
            Path(info["path"]).unlink()
            self._rebuild_index()
            return True
        except Exception:
            return False




# ════════════════════════════════════════════════════════════
# FourLayerMemory
# ════════════════════════════════════════════════════════════

class FourLayerMemory:
    """Unified memory facade across all four layers."""

    def __init__(self, cfg: ZeusConfig):
        self.l1 = MemoryL1Core(max_tokens=cfg.l1_max_tokens)
        self.l2 = MemoryL2UserProfile(max_tokens=cfg.l2_max_tokens)
        self.l3 = MemoryL3LongTerm(fts_limit=cfg.l3_fts_limit)
        self.l4 = MemoryL4SkillsLibrary()

    def build_context(self, query: str = "") -> str:
        parts = ["=== L1 Core ===", self.l1.render()]
        parts += ["", "=== L2 User Profile ===", self.l2.render()]
        if query:
            results = self.l3.search(query, limit=5)
            if results:
                parts += ["", "=== L3 Relevant Memories ==="]
                for r in results:
                    parts.append(f"[{r['category']}] {r['content'][:200]}")
        parts += ["", "=== L4 Available Skills ===", self.l4.render_index()]
        return "\n".join(parts)

    def stats(self) -> Dict:
        return {
            "l1_entries": len(self.l1._data),
            "l1_frozen": self.l1._frozen,
            "l3": self.l3.stats(),
            "l4_skills": len(self.l4.list_names()),
        }


# ###########################################################################
#  SECTION 4 -- MARS META-COGNITIVE REFLECTION  (Feature 1)
# ###########################################################################



# ════════════════════════════════════════════════════════════
# MARSEngine
# ════════════════════════════════════════════════════════════

class MARSEngine:
    """
    Meta-Agent Reflection System (MARS).
    - Principle-based reflection: abstracts rules from mistakes
    - Procedural reflection: derives step-by-step strategies from successes
    - Improves without continuous online feedback
    """

    def __init__(self, llm: OllamaRouter, memory: FourLayerMemory):
        self.llm = llm
        self.memory = memory
        self._principles: List[Dict] = []
        self._procedures: List[Dict] = []
        self._load()

    def _load(self) -> None:
        if MARS_LOG_PATH.exists():
            try:
                data = json.loads(MARS_LOG_PATH.read_text(encoding="utf-8"))
                self._principles = data.get("principles", [])
                self._procedures = data.get("procedures", [])
            except Exception:
                pass

    def _save(self) -> None:
        MARS_LOG_PATH.write_text(
            json.dumps(
                {"principles": self._principles, "procedures": self._procedures},
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    async def reflect_on_failure(self, task: str, error: str, context: str = "") -> Dict:
        prompt = (
            "You are a meta-cognitive reflection engine. A task failed.\n\n"
            f"Task: {task}\n"
            f"Error: {error}\n"
            f"Context: {context}\n\n"
            "Extract a general PRINCIPLE (not task-specific) that prevents "
            "this class of error in the future. Return JSON:\n"
            '{"principle": "...", "category": "...", "prevention": "..."}'
        )
        raw = await self.llm.generate(prompt, model=self.llm.cfg.model_reason)
        try:
            principle = json.loads(self._extract_json(raw))
        except Exception:
            principle = {"principle": raw.strip(), "category": "general", "prevention": ""}

        principle["created_at"] = datetime.datetime.utcnow().isoformat()
        principle["trigger_task"] = task[:200]
        self._principles.append(principle)
        self._save()

        self.memory.l3.store_reflection({
            "type": "principle",
            "trigger_task_id": task[:100],
            "insight": principle.get("principle", ""),
            "principles": [principle],
        })
        log.info("MARS principle extracted: %s", principle.get("principle", "")[:80])
        return principle

    async def reflect_on_success(self, task: str, steps: List[str], result: str) -> Dict:
        prompt = (
            "You are a meta-cognitive reflection engine. A task succeeded.\n\n"
            f"Task: {task}\n"
            f"Steps taken: {json.dumps(steps)}\n"
            f"Result: {result[:500]}\n\n"
            "Extract a reusable PROCEDURE (step-by-step strategy) that can be "
            "applied to similar tasks. Return JSON:\n"
            '{"procedure_name": "...", "steps": ["..."], "applicable_when": "..."}'
        )
        raw = await self.llm.generate(prompt, model=self.llm.cfg.model_reason)
        try:
            procedure = json.loads(self._extract_json(raw))
        except Exception:
            procedure = {
                "procedure_name": "derived_procedure",
                "steps": steps,
                "applicable_when": "similar tasks",
            }

        procedure["created_at"] = datetime.datetime.utcnow().isoformat()
        procedure["trigger_task"] = task[:200]
        self._procedures.append(procedure)
        self._save()

        self.memory.l3.store_reflection({
            "type": "procedure",
            "trigger_task_id": task[:100],
            "insight": procedure.get("procedure_name", ""),
            "procedures": [procedure],
        })
        log.info("MARS procedure extracted: %s", procedure.get("procedure_name", ""))
        return procedure

    def get_relevant_principles(self, task: str, limit: int = 3) -> List[Dict]:
        task_lower = task.lower()
        scored = []
        for p in self._principles:
            cat = p.get("category", "").lower()
            principle_text = p.get("principle", "").lower()
            score = sum(1 for w in task_lower.split() if w in principle_text or w in cat)
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def get_relevant_procedures(self, task: str, limit: int = 3) -> List[Dict]:
        task_lower = task.lower()
        scored = []
        for p in self._procedures:
            applicable = p.get("applicable_when", "").lower()
            name = p.get("procedure_name", "").lower()
            score = sum(1 for w in task_lower.split() if w in applicable or w in name)
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def render_guidance(self, task: str) -> str:
        principles = self.get_relevant_principles(task)
        procedures = self.get_relevant_procedures(task)
        parts = []
        if principles:
            parts.append("MARS Principles:")
            for p in principles:
                parts.append(f"  - {p.get('principle', '')}")
                if p.get("prevention"):
                    parts.append(f"    Prevention: {p['prevention']}")
        if procedures:
            parts.append("MARS Procedures:")
            for p in procedures:
                parts.append(f"  - {p.get('procedure_name', '')}")
                for i, s in enumerate(p.get("steps", []), 1):
                    parts.append(f"    {i}. {s}")
        return "\n".join(parts) if parts else ""

    @staticmethod
    def _extract_json(text: str) -> str:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return match.group(0) if match else "{}"


# ###########################################################################
#  SECTION 5 -- CLOSED SKILL EXTRACTION LOOP  (Feature 4)
# ###########################################################################

@dataclass


# ════════════════════════════════════════════════════════════
# TaskRecord
# ════════════════════════════════════════════════════════════

class TaskRecord:
    task: str = ""
    steps: List[str] = field(default_factory=list)
    tool_calls: int = 0
    self_corrections: int = 0
    user_corrections: int = 0
    found_better_path: bool = False
    result: str = ""
    duration_s: float = 0.0
    success: bool = False
    skill_extracted: bool = False




# ════════════════════════════════════════════════════════════
# SkillExtractor
# ════════════════════════════════════════════════════════════

class SkillExtractor:
    """Closed-loop skill extraction -- evaluates every completed task."""

    EXTRACT_CONDITIONS = [
        lambda r: r.tool_calls > 5,
        lambda r: r.self_corrections > 0,
        lambda r: r.user_corrections > 0,
        lambda r: r.found_better_path,
    ]

    def __init__(self, llm: OllamaRouter, memory: FourLayerMemory):
        self.llm = llm
        self.memory = memory

    def should_extract(self, record: TaskRecord) -> bool:
        return any(cond(record) for cond in self.EXTRACT_CONDITIONS)

    async def extract(self, record: TaskRecord) -> Optional[str]:
        if not self.should_extract(record):
            return None

        triggers = []
        if record.tool_calls > 5:
            triggers.append(f"complex task ({record.tool_calls} tool calls)")
        if record.self_corrections > 0:
            triggers.append(f"self-corrected {record.self_corrections} time(s)")
        if record.user_corrections > 0:
            triggers.append(f"user corrected {record.user_corrections} time(s)")
        if record.found_better_path:
            triggers.append("found a more efficient path")

        prompt = (
            "You are a skill extraction engine. Convert this completed task into "
            "a reusable skill document in agentskills.io markdown format.\n\n"
            f"Task: {record.task}\n"
            f"Steps: {json.dumps(record.steps)}\n"
            f"Result: {record.result[:500]}\n"
            f"Extraction triggers: {', '.join(triggers)}\n\n"
            "Write a skill document with:\n"
            "- Title (# Skill Name)\n"
            "- Description\n"
            "- Prerequisites\n"
            "- Steps (numbered)\n"
            "- Expected outcome\n"
            "- Notes/caveats\n\n"
            "Keep it portable (works with OpenClaw, Claude Code, etc)."
        )
        skill_md = await self.llm.generate(prompt, model=self.llm.cfg.model_code)

        name_match = re.search(r"^#\s+(.+)$", skill_md, re.MULTILINE)
        skill_name = "auto_skill"
        if name_match:
            skill_name = re.sub(r"[^\w\-]", "_", name_match.group(1).strip().lower())
            skill_name = skill_name[:60]

        self.memory.l4.save_skill(skill_name, skill_md)
        record.skill_extracted = True

        self.memory.l3.store(
            category="skill_extraction",
            content=f"Extracted skill '{skill_name}' from task: {record.task[:200]}",
            metadata={"skill_name": skill_name, "triggers": triggers},
        )
        log.info("Skill extracted: %s (triggers: %s)", skill_name, triggers)
        return skill_name


# ###########################################################################
#  SECTION 6 -- ANDROID HARDWARE INTEGRATION  (Feature 6)
# ###########################################################################



# ════════════════════════════════════════════════════════════
# TermuxHardware
# ════════════════════════════════════════════════════════════

class TermuxHardware:
    """Android hardware integration via Termux APIs."""

    @staticmethod
    async def _run_termux_cmd(cmd: List[str], timeout: int = 10) -> Optional[str]:
        if not IS_TERMUX:
            return None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            if proc.returncode == 0:
                return stdout.decode("utf-8", errors="replace").strip()
            log.warning("Termux cmd %s failed: %s", cmd, stderr.decode())
            return None
        except asyncio.TimeoutError:
            log.warning("Termux cmd %s timed out", cmd)
            return None
        except FileNotFoundError:
            return None

    async def take_photo(self, camera_id: int = 0) -> Optional[str]:
        photo_path = str(ZEUS_DIR / f"photo_{int(time.time())}.jpg")
        result = await self._run_termux_cmd(
            ["termux-camera-photo", "-c", str(camera_id), photo_path],
            timeout=15,
        )
        if result is not None and Path(photo_path).exists():
            return photo_path
        return None

    async def take_screenshot(self) -> Optional[str]:
        ss_path = str(ZEUS_DIR / f"screenshot_{int(time.time())}.png")
        result = await self._run_termux_cmd(
            ["termux-screenshot", ss_path],
            timeout=10,
        )
        if result is not None and Path(ss_path).exists():
            return ss_path
        return None

    async def get_location(self) -> Optional[Dict]:
        raw = await self._run_termux_cmd(
            ["termux-location", "-p", "gps", "-r", "once"],
            timeout=30,
        )
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    async def get_battery(self) -> Optional[Dict]:
        raw = await self._run_termux_cmd(["termux-battery-status"])
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    async def get_sensors(self) -> Optional[Dict]:
        raw = await self._run_termux_cmd(
            ["termux-sensor", "-s", "all", "-n", "1"],
            timeout=10,
        )
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    async def send_notification(
        self, title: str, content: str, priority: str = "default"
    ) -> bool:
        result = await self._run_termux_cmd([
            "termux-notification",
            "--title", title,
            "--content", content,
            "--priority", priority,
        ])
        return result is not None

    async def get_clipboard(self) -> Optional[str]:
        return await self._run_termux_cmd(["termux-clipboard-get"])

    async def set_clipboard(self, text: str) -> bool:
        result = await self._run_termux_cmd(["termux-clipboard-set", text])
        return result is not None

    async def vibrate(self, duration_ms: int = 200) -> bool:
        result = await self._run_termux_cmd(
            ["termux-vibrate", "-d", str(duration_ms)]
        )
        return result is not None

    async def tts_speak(self, text: str) -> bool:
        result = await self._run_termux_cmd(
            ["termux-tts-speak", text],
            timeout=30,
        )
        return result is not None

    async def get_device_info(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {"is_termux": IS_TERMUX}
        battery = await self.get_battery()
        if battery:
            info["battery"] = battery
        info["platform"] = platform.platform()
        info["python"] = platform.python_version()
        return info

    async def analyze_image(self, image_path: str, llm: OllamaRouter) -> str:
        if not Path(image_path).exists():
            return "[Image not found]"
        import base64
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return await llm.generate(
            "Describe this image in detail.",
            model=llm.cfg.model_vision,
            images=[b64],
        )


# ###########################################################################
#  SECTION 7 -- SANDBOXED SKILL FORGE  (Feature 8)
# ###########################################################################



# ════════════════════════════════════════════════════════════
# AgentProfile
# ════════════════════════════════════════════════════════════

@dataclass
class AgentProfile:
    agent_id: str
    name: str
    specialty: str
    capabilities: List[str] = field(default_factory=list)
    trust_score: float = 0.5
    tasks_completed: int = 0
    tasks_failed: int = 0
    accuracy_history: List[float] = field(default_factory=list)
    created_at: str = ""
    status: str = "active"




# ════════════════════════════════════════════════════════════
# BayesianTrustLedger
# ════════════════════════════════════════════════════════════

class BayesianTrustLedger:
    """Tracks per-agent accuracy with Bayesian updates."""

    def __init__(self):
        self._ledger: Dict[str, AgentProfile] = {}
        self._load()

    def _load(self) -> None:
        if TRUST_LEDGER_PATH.exists():
            try:
                data = json.loads(TRUST_LEDGER_PATH.read_text(encoding="utf-8"))
                for agent_id, info in data.items():
                    self._ledger[agent_id] = AgentProfile(**info)
            except Exception:
                pass

    def _save(self) -> None:
        data = {aid: asdict(ap) for aid, ap in self._ledger.items()}
        TRUST_LEDGER_PATH.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )

    def register(self, profile: AgentProfile) -> None:
        self._ledger[profile.agent_id] = profile
        self._save()

    def record_outcome(self, agent_id: str, success: bool, accuracy: float = 1.0) -> None:
        profile = self._ledger.get(agent_id)
        if not profile:
            return
        if success:
            profile.tasks_completed += 1
        else:
            profile.tasks_failed += 1
        profile.accuracy_history.append(accuracy)
        if len(profile.accuracy_history) > 100:
            profile.accuracy_history = profile.accuracy_history[-100:]
        total = profile.tasks_completed + profile.tasks_failed
        alpha = profile.tasks_completed + 1
        beta = profile.tasks_failed + 1
        profile.trust_score = alpha / (alpha + beta)
        self._save()

    def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        return self._ledger.get(agent_id)

    def get_all(self) -> List[AgentProfile]:
        return list(self._ledger.values())

    def get_trusted(self, threshold: float = 0.6) -> List[AgentProfile]:
        return [p for p in self._ledger.values() if p.trust_score >= threshold]




# ════════════════════════════════════════════════════════════
# ShadowMind
# ════════════════════════════════════════════════════════════

class ShadowMind:
    """Parallel cognitive layer -- offers pattern-based intuition."""

    def __init__(self, llm: OllamaRouter, memory: FourLayerMemory):
        self.llm = llm
        self.memory = memory

    async def intuition(self, task: str, context: str = "") -> str:
        memories = self.memory.l3.search(task, limit=5)
        mem_context = "\n".join(m["content"][:150] for m in memories)

        prompt = (
            "You are the Shadow Mind -- a parallel cognitive layer that provides "
            "pattern-based intuition. Based on past patterns, provide a brief "
            "intuitive assessment of this task.\n\n"
            f"Task: {task}\n"
            f"Context: {context}\n"
            f"Relevant memories:\n{mem_context}\n\n"
            "Provide:\n"
            "1. Confidence level (0-1)\n"
            "2. Suggested approach\n"
            "3. Potential pitfalls\n"
            "4. Recommended agent specialties needed\n"
            "Keep it brief (3-4 sentences total)."
        )
        return await self.llm.generate(prompt, model=self.llm.cfg.model_fast)




# ════════════════════════════════════════════════════════════
# MetaImprovementLog
# ════════════════════════════════════════════════════════════

class MetaImprovementLog:
    """Tracks meta-level improvements for self-acceleration."""

    def __init__(self):
        self._improvements: List[Dict] = []
        self._load()

    def _load(self) -> None:
        if META_IMPROVEMENT_PATH.exists():
            try:
                self._improvements = json.loads(
                    META_IMPROVEMENT_PATH.read_text(encoding="utf-8")
                )
            except Exception:
                pass

    def _save(self) -> None:
        META_IMPROVEMENT_PATH.write_text(
            json.dumps(self._improvements, indent=2, default=str),
            encoding="utf-8",
        )

    def record(self, improvement: Dict) -> None:
        improvement["timestamp"] = datetime.datetime.utcnow().isoformat()
        self._improvements.append(improvement)
        if len(self._improvements) > 200:
            self._improvements = self._improvements[-200:]
        self._save()

    def get_recent(self, limit: int = 10) -> List[Dict]:
        return self._improvements[-limit:]

    def count(self) -> int:
        return len(self._improvements)




