"""
Memory & Knowledge Engine for J.A.R.V.I.S.

Structured, durable memory layers:
- EPISODIC: What happened (session actions, execution logs)
- SEMANTIC: What is known (technology concepts, API constraints)
- PROJECT: Facts about local codebases (stack, architecture, configs)
- TASK: Current task state & decisions
- PREFERENCE: User preferences & configuration

Supports semantic/tag retrieval, confidence scoring, conflict resolution,
and durable persistence to disk.
"""

import os
import json
import time
import re
from typing import Dict, List, Any, Optional, Callable

from intelligence.models import MemoryEntry, MemoryType


class MemoryEngine:
    """
    Authoritative memory and knowledge manager for J.A.R.V.I.S.
    """

    DEFAULT_STORAGE_FILE = "jarvis_memory.json"

    def __init__(
        self,
        storage_path: Optional[str] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", self.DEFAULT_STORAGE_FILE
        )
        self.log_callback = log_callback
        self.entries: Dict[str, MemoryEntry] = {}
        self.load_from_disk()

    def _log(self, stage: str, message: str):
        formatted = f"[{stage}] {message}"
        print(formatted)
        if self.log_callback:
            try:
                self.log_callback(stage, message)
            except Exception:
                pass

    def load_from_disk(self):
        """Loads persisted memory entries from local JSON storage."""
        if not os.path.exists(self.storage_path):
            self._seed_default_knowledge()
            self.save_to_disk()
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as fp:
                raw_data = json.load(fp)
                for item in raw_data:
                    mtype_str = item.get("type", "semantic")
                    mtype = MemoryType(mtype_str) if mtype_str in [e.value for e in MemoryType] else MemoryType.SEMANTIC
                    entry = MemoryEntry(
                        id=item.get("id"),
                        content=item.get("content", ""),
                        type=mtype,
                        source=item.get("source", "system"),
                        confidence=float(item.get("confidence", 0.95)),
                        timestamp=float(item.get("timestamp", time.time())),
                        relevance=float(item.get("relevance", 1.0)),
                        tags=list(item.get("tags", [])),
                        verified=bool(item.get("verified", True))
                    )
                    self.entries[entry.id] = entry
            self._log("MEMORY", f"Loaded {len(self.entries)} durable memory records from storage.")
        except Exception as e:
            self._log("MEMORY", f"Warning: Failed to load memory file ({e}). Seeding defaults.")
            self._seed_default_knowledge()

    def save_to_disk(self):
        """Persists all memory entries to disk."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as fp:
                data = [entry.to_dict() for entry in self.entries.values()]
                json.dump(data, fp, indent=2)
        except Exception as e:
            self._log("MEMORY", f"Error saving memory to disk: {e}")

    def _seed_default_knowledge(self):
        """Seeds foundational established facts."""
        default_facts = [
            ("J.A.R.V.I.S. is an autonomous desktop AI assistant and agent platform.", MemoryType.SEMANTIC, ["jarvis", "platform"], 1.0),
            ("Python, Flask, and Gemini 2.5 Flash power the core architecture.", MemoryType.PROJECT, ["stack", "python", "flask"], 0.98),
            ("Desktop automation uses closed-loop Observe-Perceive-Context-Decide-Validate-Execute-Verify cycles.", MemoryType.SEMANTIC, ["automation", "architecture"], 0.99),
            ("User prefers dark glassmorphic cybersecurity-themed user interfaces.", MemoryType.PREFERENCE, ["ui", "theme", "preference"], 0.95)
        ]
        for content, mtype, tags, conf in default_facts:
            self.store(content=content, mem_type=mtype, source="system_init", confidence=conf, tags=tags, verified=True)

    def store(
        self,
        content: str,
        mem_type: MemoryType = MemoryType.SEMANTIC,
        source: str = "user_input",
        confidence: float = 0.90,
        tags: Optional[List[str]] = None,
        verified: bool = True
    ) -> MemoryEntry:
        """
        Stores a new memory entry or resolves conflicts with existing matching entries.
        """
        clean_content = content.strip()
        tags_list = tags or []

        # Check for existing memory with very similar content
        for existing in self.entries.values():
            if existing.type == mem_type and (
                existing.content.lower() == clean_content.lower()
                or (len(clean_content) > 20 and clean_content.lower() in existing.content.lower())
            ):
                return self.resolve_conflict(existing, clean_content, confidence, source, verified)

        entry = MemoryEntry(
            content=clean_content,
            type=mem_type,
            source=source,
            confidence=confidence,
            tags=tags_list,
            verified=verified
        )
        self.entries[entry.id] = entry
        self.save_to_disk()
        self._log("MEMORY", f"Stored [{entry.type.value}] memory (conf={entry.confidence}): '{clean_content[:50]}...'")
        return entry

    def resolve_conflict(
        self,
        existing: MemoryEntry,
        new_content: str,
        new_confidence: float,
        new_source: str,
        verified: bool
    ) -> MemoryEntry:
        """
        Handles conflicting or updated evidence.
        Higher confidence verified evidence updates older or unverified memory.
        """
        if new_confidence >= existing.confidence or (verified and not existing.verified):
            self._log("MEMORY", f"Updating memory '{existing.id}' with higher confidence evidence ({new_confidence} >= {existing.confidence}).")
            existing.content = new_content
            existing.confidence = max(existing.confidence, new_confidence)
            existing.source = new_source
            existing.verified = verified or existing.verified
            existing.timestamp = time.time()
            self.save_to_disk()
            return existing
        else:
            self._log("MEMORY", f"Preserved existing verified memory '{existing.id}' over lower confidence update ({existing.confidence} > {new_confidence}).")
            return existing

    def retrieve(
        self,
        query: str,
        type_filter: Optional[MemoryType] = None,
        min_confidence: float = 0.4,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """
        Retrieves top relevant memory entries matching query tokens and tags.
        """
        query_words = set(re.findall(r"\b\w{3,}\b", query.lower()))
        results: List[tuple[float, MemoryEntry]] = []

        for entry in self.entries.values():
            if type_filter and entry.type != type_filter:
                continue
            if entry.confidence < min_confidence:
                continue

            # Calculate match score based on token overlap + tags + recency
            entry_words = set(re.findall(r"\b\w{3,}\b", entry.content.lower()))
            overlap = query_words.intersection(entry_words)
            tag_overlap = query_words.intersection({t.lower() for t in entry.tags})

            score = (len(overlap) * 2.0) + (len(tag_overlap) * 3.0)

            # Recency boost (within last 24h)
            age_hours = (time.time() - entry.timestamp) / 3600
            if age_hours < 24:
                score += 0.5

            score = score * entry.confidence

            if score > 0.5 or not query.strip():
                entry.relevance = min(1.0, score / max(1, len(query_words) * 2.0)) if query.strip() else 1.0
                results.append((score, entry))

        # Sort by relevance score descending
        results.sort(key=lambda x: x[0], reverse=True)
        top_entries = [r[1] for r in results[:limit]]
        self._log("MEMORY", f"Retrieved {len(top_entries)} relevant memory records for query: '{query[:30]}'")
        return top_entries

    def delete(self, entry_id: str) -> bool:
        """Deletes a memory record by ID."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            self.save_to_disk()
            self._log("MEMORY", f"Deleted memory entry: '{entry_id}'")
            return True
        return False

    def get_all(self, type_filter: Optional[MemoryType] = None) -> List[MemoryEntry]:
        """Returns all memory records sorted by timestamp descending."""
        all_entries = list(self.entries.values())
        if type_filter:
            all_entries = [e for e in all_entries if e.type == type_filter]
        all_entries.sort(key=lambda e: e.timestamp, reverse=True)
        return all_entries
