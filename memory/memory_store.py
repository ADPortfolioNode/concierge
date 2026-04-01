"""Async MemoryStore for RAG using ChromaDB/Qdrant with in-memory fallback.

This module provides an async-friendly wrapper around optional vector
databases (ChromaDB or Qdrant). If no external DB is available the
store falls back to an in-memory list and a local JSONL backup for
restart-safe testing.
"""

import os
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

# local import to avoid hard dependency for environments that don't need LLM
try:
    from tools.llm_tool import LLMTool
except Exception:  # pragma: no cover - optional
    LLMTool = None

try:
    import chromadb
except Exception:  # pragma: no cover - optional dependency
    chromadb = None

# Detect whether onnxruntime is available so we can avoid triggering
# Chromadb's ONNX embedder at runtime in environments without the native
# dependency. If onnxruntime is missing we will skip initializing Chroma
# to prevent late ImportError/DLL failures.
try:
    import onnxruntime  # type: ignore
    _ONNX_AVAILABLE = True
except Exception:
    _ONNX_AVAILABLE = False

try:
    # qdrant client (optional)
    from qdrant_client import QdrantClient
    # import the models namespace so we can construct VectorParams/Distance
    from qdrant_client import models as qdrant_models
    try:
        from qdrant_client.models import PointStruct
    except Exception:
        PointStruct = None
except Exception:  # pragma: no cover - optional
    QdrantClient = None
    qdrant_models = None
    PointStruct = None

logger = logging.getLogger(__name__)


from dataclasses import dataclass, field


@dataclass
class IntelligenceNode:
    id: str
    goal: Optional[str]
    summary: str
    key_points: List[str] = field(default_factory=list)
    recommendation: str = ""
    delta_from_previous: str = ""
    parent_ids: List[str] = field(default_factory=list)
    timestamp: str = ""
    confidence: float = 0.0
    active: bool = True                    # archived flag
    contradiction_risk: float = 0.0        # computed on insertion


class MemoryStore:
    """Async-friendly memory store backed by a directed intelligence graph.

    The graph is kept in memory with an optional external vector database
    for retrieval. Writes are serialized via a lock; reads rely on indices for
    performance. The store maintains an inverted keyword index for deterministic
    lookup and a simple embedding fallback.
    """

    def __init__(
        self,
        collection_name: str = "concierge_memory",
        llm_tool: Optional["LLMTool"] = None,
        compress_threshold: Optional[int] = None,
    ) -> None:
        self._collection_name = collection_name
        self._client = None
        self._collection = None
        self._is_qdrant = False
        self._llm = llm_tool

        self._vector_db = os.getenv("VECTOR_DB", "chroma").lower()
        chroma_host = os.getenv("CHROMA_HOST", "localhost")
        chroma_port = os.getenv("CHROMA_PORT", "8000")
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = os.getenv("QDRANT_PORT", "6333")
        # vector dimension for qdrant when embeddings are unavailable
        self._qdrant_vector_dim = int(os.getenv("QDRANT_VECTOR_DIM", "8"))

        # Initialize selected vector DB client if available. Prefer Chroma when
        # configured, otherwise attempt Qdrant. If optional libraries are
        # missing fall back to the in-memory JSONL-backed store.
        if self._vector_db == "chroma":
            if chromadb is not None and _ONNX_AVAILABLE:
                try:
                    try:
                        self._client = chromadb.Client()
                    except Exception:
                        try:
                            self._client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
                        except Exception:
                            self._client = None

                    if self._client is not None:
                        try:
                            if hasattr(self._client, "get_or_create_collection"):
                                self._collection = self._client.get_or_create_collection(name=self._collection_name)
                            else:
                                self._collection = self._client.create_collection(name=self._collection_name)
                        except Exception:
                            logger.exception("Failed to create/get chroma collection; disabling chroma")
                            self._client = None
                except Exception:
                    logger.exception("Failed to initialize chromadb client; using in-memory fallback")
                    self._client = None
            else:
                if chromadb is not None:
                    logger.warning("onnxruntime not available; skipping Chroma initialization and using in-memory fallback")

        elif self._vector_db == "qdrant":
            if QdrantClient is not None:
                try:
                    try:
                        self._client = QdrantClient(host=qdrant_host, port=int(qdrant_port))
                    except Exception:
                        try:
                            self._client = QdrantClient(url=f"http://{qdrant_host}:{qdrant_port}")
                        except Exception:
                            self._client = None

                    if self._client is not None:
                        try:
                            exists = None
                            try:
                                exists = self._client.get_collection(collection_name=self._collection_name)
                            except Exception:
                                exists = None

                            if qdrant_models is not None:
                                vectors_config = {
                                    "embedding": qdrant_models.VectorParams(
                                        size=1536, distance=qdrant_models.Distance.COSINE
                                    )
                                }
                            else:
                                vectors_config = {"embedding": {"size": 1536, "distance": "Cosine"}}

                            dev_mode = os.getenv("DEV_MODE", "false").lower() in ("1", "true", "yes")
                            if not exists:
                                if dev_mode:
                                    self._client.recreate_collection(collection_name=self._collection_name, vectors_config=vectors_config)
                                    logger.info("Qdrant collection recreated (dev): %s", self._collection_name)
                                else:
                                    try:
                                        self._client.create_collection(collection_name=self._collection_name, vectors_config=vectors_config)
                                        logger.info("Qdrant collection created: %s", self._collection_name)
                                    except Exception:
                                        self._client.recreate_collection(collection_name=self._collection_name, vectors_config=vectors_config)
                                        logger.info("Qdrant collection recreated (fallback): %s", self._collection_name)
                            else:
                                logger.info("Qdrant collection exists: %s", self._collection_name)
                                logger.info("Qdrant vector config: %s", vectors_config)

                            logger.info("Connected to Qdrant at %s:%s", qdrant_host, qdrant_port)
                        except Exception:
                            logger.exception("Qdrant collection create failed; disabling qdrant")
                            self._client = None
                        else:
                            self._is_qdrant = True
                except Exception:
                    logger.exception("Failed to initialize Qdrant client; using in-memory fallback")
                    self._client = None
            else:
                logger.warning("Qdrant client not installed; using in-memory fallback")

        self._in_memory: List[Dict[str, Any]] = []
        # intelligence graph structures
        self._graph: Dict[str, IntelligenceNode] = {}
        # simple inverted index token -> set of node ids
        self._index: Dict[str, set] = {}
        # lock to serialize graph writes
        self._graph_lock = asyncio.Lock()
        # threshold for compressing old memories; can be overridden by env
        env_thresh = os.getenv("MEMORY_COMPRESS_THRESHOLD")
        try:
            self._compress_threshold = int(env_thresh) if env_thresh is not None else (compress_threshold or 500)
        except Exception:
            self._compress_threshold = compress_threshold or 500

        # attempt to schedule migration from disk if running inside an event loop
        try:
            self.schedule_migration()
        except Exception:
            # ignore scheduling failures; caller can call `migrate_from_disk` explicitly
            logger.debug("Could not schedule migration at init")

        # Load local backup file to support restart-safe validation when external
        # vector DB upserts fail. This provides a best-effort persistence fallback
        # for tests and development.
        try:
            backup_path = os.path.join(os.getcwd(), "memory_backup.jsonl")
            if os.path.exists(backup_path):
                with open(backup_path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            obj = __import__("json").loads(line)
                            if isinstance(obj, dict) and obj.get("id"):
                                # old-format entry? treat as summary - keep for backward compatibility
                                if "node" not in obj:
                                    self._in_memory.append({"id": obj.get("id"), "summary": obj.get("summary"), "metadata": obj.get("metadata", {})})
                                else:
                                    # new style: node record
                                    node_data = obj.get("node")
                                    node = IntelligenceNode(**node_data)
                                    self._graph[node.id] = node
                                    # rebuild index tokens
                                    tokens = set(w.strip('.,').lower() for w in (node.summary + ' ' + (node.goal or '')) .split() if len(w) > 3)
                                    for tok in tokens:
                                        self._index.setdefault(tok, set()).add(node.id)
                        except Exception:
                            continue
        except Exception:
            logger.exception("Failed to load memory backup file")

        # Ensure backup loader is available for explicit reloads (used by tests)
        def _load_backup() -> None:
            try:
                path = os.path.join(os.getcwd(), "memory_backup.jsonl")
                if not os.path.exists(path):
                    return
                with open(path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            obj = __import__("json").loads(line)
                            if isinstance(obj, dict) and obj.get("id"):
                                if "node" not in obj:
                                    # legacy
                                    if not any(r.get("id") == obj.get("id") for r in self._in_memory):
                                        self._in_memory.append({"id": obj.get("id"), "summary": obj.get("summary"), "metadata": obj.get("metadata", {})})
                                else:
                                    node_data = obj.get("node")
                                    node = IntelligenceNode(**node_data)
                                    if node.id not in self._graph:
                                        self._graph[node.id] = node
                                        tokens = set(w.strip('.,').lower() for w in (node.summary + ' ' + (node.goal or '')) .split() if len(w) > 3)
                                        for tok in tokens:
                                            self._index.setdefault(tok, set()).add(node.id)
                        except Exception:
                            continue
            except Exception:
                logger.exception("Failed to reload memory backup file")

        # attach as instance utility
        try:
            self.load_local_backup = _load_backup  # type: ignore[attr-defined]
        except Exception:
            pass

    async def _update_confidence(self, node_id: str, score: float) -> None:
        """Deterministically update confidence of an existing node.

        Use a simple average to evolve confidence over time.
        """
        try:
            async with self._graph_lock:
                node = self._graph.get(node_id)
                if node:
                    node.confidence = (node.confidence + float(score) / 100.0) / 2.0
        except Exception:
            logger.exception("Failed to update node confidence")

    def get_low_confidence_nodes(self, threshold: Optional[float] = None) -> List[IntelligenceNode]:
        """Return active nodes with confidence below threshold.

        If no threshold is provided, use the configured low confidence threshold.
        """
        if threshold is None:
            from config.settings import get_settings

            threshold = get_settings().low_confidence_threshold
        return [n for n in self._graph.values() if n.active and n.confidence < threshold]

    def get_contradiction_nodes(self, threshold: Optional[float] = None) -> List[IntelligenceNode]:
        """Return active nodes with contradiction risk above threshold.

        If no threshold is provided, use configured contradiction risk threshold.
        """
        if threshold is None:
            from config.settings import get_settings

            threshold = get_settings().contradiction_risk_threshold
        return [n for n in self._graph.values() if n.active and n.contradiction_risk > threshold]

    def prune_graph(self, confidence_threshold: float = 0.1) -> None:
        """Archive nodes whose confidence has decayed below threshold.

        Archived nodes remain in graph but marked inactive and excluded from
        retrieval. Lineage is preserved in metadata for audit.
        """
        try:
            for node in list(self._graph.values()):
                if node.active and node.confidence < confidence_threshold:
                    node.active = False
                    logger.info("Archiving low-confidence node %s", node.id)
        except Exception:
            logger.exception("Graph pruning failed")

    def _pseudo_embed(self, text: str, dim: int = 8) -> List[float]:
        """Generate a deterministic pseudo-embedding for local testing.

        This is a fallback for environments without a real embedder. Not
        intended for production-quality semantic vectors.
        """
        h = abs(hash(text))
        out: List[float] = []
        for i in range(dim):
            out.append(((h >> (i * 4)) & 0xFFFF) / 65535.0)
        return out

    async def store_summary(self, task_name: str, summary: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a summary and return its id.

        Metadata will be merged with timestamp and task_name.
        """
        metadata = metadata or {}
        # ensure required metadata fields
        metadata = {
            **metadata,
            "task_name": task_name,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_type": metadata.get("agent_type", "unknown"),
            "reflection": bool(metadata.get("reflection", False)),
        }
        # Use provided task_id if available for idempotent tracking
        rec_id = metadata.get("task_id") or str(uuid.uuid4())
        # Build graph node and index tokens atomically. If a node with this
        # id already exists, we update its fields rather than replace it so that
        # historical data is preserved and we can track state changes.
        try:
            async with self._graph_lock:
                struct = metadata.get("structured") or {}
                node = self._graph.get(rec_id)
                if node:
                    # update existing node summary and metadata
                    node.summary = summary
                    node.goal = metadata.get("goal") or node.goal
                    node.key_points = struct.get("key_points", []) or node.key_points
                    node.recommendation = struct.get("recommendations", [node.recommendation])[0] if struct.get("recommendations") else node.recommendation
                    node.delta_from_previous = metadata.get("delta", node.delta_from_previous)
                    node.parent_ids = metadata.get("parent_ids", node.parent_ids)
                    node.timestamp = metadata.get("timestamp", node.timestamp)
                    # confidence may be updated separately via _update_confidence
                else:
                    node = IntelligenceNode(
                        id=rec_id,
                        goal=metadata.get("goal"),
                        summary=summary,
                        key_points=struct.get("key_points", []) or [],
                        recommendation=struct.get("recommendations", [""])[0] if struct.get("recommendations") else "",
                        delta_from_previous=metadata.get("delta", ""),
                        parent_ids=metadata.get("parent_ids", []),
                        timestamp=metadata.get("timestamp", ""),
                        confidence=float(metadata.get("confidence", 0.0)) if metadata.get("confidence") is not None else 0.0,
                    )
                    self._graph[rec_id] = node
                # update inverted index using keywords from summary and task_name
                tokens = set(w.strip('.,').lower() for w in (summary + ' ' + task_name).split() if len(w) > 3)
                for tok in tokens:
                    self._index.setdefault(tok, set()).add(rec_id)
        except Exception:
            logger.exception("Failed to update intelligence graph")
        # Always append a local backup record to support restart-safe tests
        try:
            backup_path = os.path.join(os.getcwd(), "memory_backup.jsonl")
            with open(backup_path, "a", encoding="utf-8") as fh:
                # persist node structure rather than raw summary
                backup_obj = {"id": rec_id, "node": node.__dict__}
                fh.write(__import__("json").dumps(backup_obj) + "\n")
        except Exception:
            logger.exception("Failed to write memory backup")
        # if neither chroma nor qdrant available, fallback to in-memory
        if self._client is None:
            self._in_memory.append({"id": rec_id, "summary": summary, "metadata": metadata})
            await asyncio.sleep(0)
            logger.debug("MemoryStore (in-memory) stored %s", rec_id)
            # append to local backup for restart-safety
            try:
                backup_path = os.path.join(os.getcwd(), "memory_backup.jsonl")
                with open(backup_path, "a", encoding="utf-8") as fh:
                    fh.write(__import__("json").dumps({"id": rec_id, "summary": summary, "metadata": metadata}) + "\n")
            except Exception:
                logger.exception("Failed to write memory backup")
            try:
                if len(self._in_memory) > self._compress_threshold and self._llm is not None:
                    asyncio.create_task(self.compress_old_memories())
            except Exception:
                logger.exception("Failed to schedule memory compression")
            return rec_id

        loop = asyncio.get_running_loop()

        # update graph node confidence if Critic score is present
        if metadata.get("score") is not None and rec_id in self._graph:
            await self._update_confidence(rec_id, metadata.get("score"))
        # compute contradiction risk based on key_points heuristics
        try:
            node = self._graph.get(rec_id)
            if node:
                # simple check: any summary containing 'not X' vs existing 'X'
                for other in self._graph.values():
                    if other.id == node.id or not other.active:
                        continue
                    for kp in other.key_points:
                        if kp and kp.lower() in node.summary.lower() and "not" in node.summary.lower():
                            node.contradiction_risk = 1.0
                            break
                    if node.contradiction_risk:
                        break
        except Exception:
            pass
        # helper to sanitize metadata for Chroma which restricts metadata value types
        def _sanitize_for_chroma(m: Dict[str, Any]) -> Dict[str, Any]:
            out: Dict[str, Any] = {}
            for k, v in (m or {}).items():
                key = str(k)
                # allow simple primitives unchanged
                if v is None or isinstance(v, (str, int, float, bool)):
                    out[key] = v
                    continue
                # for lists, dicts, sets, or any complex object stringify to JSON
                try:
                    # sets aren't JSON serializable; convert to list first
                    if isinstance(v, set):
                        v_conv = list(v)
                    else:
                        v_conv = v
                    out[key] = json.dumps(v_conv, default=str, ensure_ascii=False)
                except Exception:
                    try:
                        out[key] = str(v)
                    except Exception:
                        out[key] = None
            return out

        # Chroma path
        if self._vector_db == "chroma" and self._collection is not None:
            def _add_chroma():
                try:
                    safe_meta = _sanitize_for_chroma(metadata)
                    self._collection.add(documents=[summary], metadatas=[safe_meta], ids=[rec_id])
                except Exception as e:
                    # Detect common missing-native-dependency errors (onnxruntime)
                    err_text = str(e) or ''
                    if 'onnxruntime' in err_text or 'onnxruntime python package is not installed' in err_text.lower():
                        logger.error("Chroma add failed due to missing onnxruntime. Disabling Chroma and falling back to in-memory. Install onnxruntime with: pip install onnxruntime")
                        try:
                            # disable chroma for remainder of process to avoid repeated failures
                            self._client = None
                            self._collection = None
                        except Exception:
                            pass
                    else:
                        logger.exception("Chroma add failed")

            await loop.run_in_executor(None, _add_chroma)
            # If chroma was disabled by the failure handler above, fall back
            if self._client is None or self._collection is None:
                logger.warning("Chroma disabled; storing %s in in-memory fallback", rec_id)
                self._in_memory.append({"id": rec_id, "summary": summary, "metadata": metadata})
                await asyncio.sleep(0)
                return rec_id

            logger.debug("MemoryStore stored %s in chroma", rec_id)
            return rec_id

        # Qdrant path
        if self._is_qdrant and self._client is not None:
            def _upsert_qdrant():
                try:
                    # Attempt to create a PointStruct with optional vector if LLM provides embedding
                    vec = None
                    if self._llm is not None and hasattr(self._llm, "embed"):
                        try:
                            vec = self._llm.embed(summary)
                        except Exception:
                            vec = None
                    # if no real embedding available, create a deterministic pseudo-embedding
                    if vec is None:
                        try:
                            vec = self._pseudo_embed(summary, dim=self._qdrant_vector_dim)
                        except Exception:
                            vec = None
                    # Build payload with required fields
                    payload = {**metadata, "text": summary}
                    # ensure tool_usage present when available
                    if metadata.get("tool_usage") is not None:
                        payload["tool_usage"] = metadata.get("tool_usage")
                    # DEBUG: log what we're about to upsert
                    try:
                        logger.debug("Qdrant upsert prepare: rec_id=%s payload_keys=%s vec_len=%s", rec_id, list(payload.keys()), (len(vec) if (vec is not None and hasattr(vec, '__len__')) else None))
                    except Exception:
                        logger.debug("Qdrant upsert prepare: rec_id=%s (failed to compute vec length)", rec_id)
                    # ensure a qdrant-friendly id (UUID or int);
                    point_id = rec_id
                    try:
                        import uuid as _uuid_check

                        _uuid_check.UUID(point_id)
                    except Exception:
                        # deterministically map arbitrary id to a UUID
                        import uuid as _uuid

                        point_id = str(_uuid.uuid5(_uuid.NAMESPACE_OID, rec_id))

                    if vec is not None:
                        # Try multiple strategies for upserting to support different qdrant-client/server versions:
                        # 1) Prefer PointStruct objects when available
                        # 2) Fallback to dict with named 'vectors' ({'embedding': [...]}) to match collection schema
                        # 3) Fallback to dict with 'vector' for older client expectations
                        upsert_error = None
                        # Attempt PointStruct path first when available
                        if PointStruct is not None:
                            try:
                                try:
                                    p = PointStruct(id=point_id, payload=payload, vector=vec)
                                except TypeError:
                                    # Some PointStruct versions accept 'vectors' mapping; try that form
                                    try:
                                        p = PointStruct(id=point_id, payload=payload, vectors={"embedding": vec})
                                    except Exception:
                                        raise
                                logger.debug("Qdrant upsert using PointStruct id=%s", point_id)
                                self._client.upsert(collection_name=self._collection_name, points=[p])
                                upsert_error = None
                            except Exception as e:  # pragma: no cover - runtime fallback
                                upsert_error = e
                                logger.debug("PointStruct upsert failed, will try dict fallbacks: %s", e)

                        # If PointStruct not used or failed, try dict-shaped upsert
                        if upsert_error is not None or PointStruct is None:
                            try:
                                # Preferred form for named vectors
                                point = {"id": point_id, "payload": payload, "vectors": {"embedding": vec}}
                                logger.debug("Qdrant upsert: dict 'vectors' id=%s vectors_keys=%s vector_len=%s", point_id, list(point.get("vectors", {}).keys()), len(vec) if hasattr(vec, '__len__') else None)
                                self._client.upsert(collection_name=self._collection_name, points=[point])
                            except Exception as e2:
                                logger.debug("Dict 'vectors' upsert failed: %s", e2)
                                try:
                                    # Older clients may expect a single 'vector' key
                                    point = {"id": point_id, "payload": payload, "vector": vec}
                                    logger.debug("Qdrant upsert: dict 'vector' id=%s", point_id)
                                    self._client.upsert(collection_name=self._collection_name, points=[point])
                                except Exception:
                                    logger.exception("Qdrant upsert failed for rec_id=%s (vec path)", rec_id)
                                    # let caller see failure via logs but continue; last-resort will raise below if payload-only also fails
                    else:
                        # last-resort: payload-only may not be supported depending on collection schema
                        try:
                            point = {"id": point_id, "payload": payload}
                            logger.debug("Qdrant upsert: payload-only id=%s", point_id)
                            self._client.upsert(collection_name=self._collection_name, points=[point])
                        except Exception:
                            logger.exception("Qdrant payload-only upsert failed for id=%s", point_id)
                            raise
                except Exception:
                    logger.exception("Qdrant upsert failed for rec_id=%s", rec_id)

            await loop.run_in_executor(None, _upsert_qdrant)
            logger.debug("MemoryStore stored %s in qdrant", rec_id)
            return rec_id

        # If we reach here, no supported persistence path was taken; fallback to in-memory
        logger.warning("No supported vector DB path available; falling back to in-memory for %s", rec_id)
        self._in_memory.append({"id": rec_id, "summary": summary, "metadata": metadata})
        await asyncio.sleep(0)
        return rec_id

    async def query(self, context: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return top_k memory entries relevant to `context`.

        The returned list contains dicts with `id`, `summary`, and `metadata`.
        """
        if self._collection is None:
            # use keyword index fallback
            results = []
            # tokenize query into keywords
            keys = set(w.strip('.,').lower() for w in context.split() if len(w) > 3)
            candidate_ids = set()
            for k in keys:
                candidate_ids.update(self._index.get(k, set()))
            for cid in candidate_ids:
                node = self._graph.get(cid)
                if not node:
                    continue
                results.append({"id": node.id, "summary": node.summary, "metadata": node.__dict__})
            await asyncio.sleep(0)
            # deterministic sort by id, then truncate
            results.sort(key=lambda r: r.get("id", ""))
            return results[:top_k]

        loop = asyncio.get_running_loop()

        # Chroma query path
        if self._vector_db == "chroma" and self._collection is not None:
            def _query_chroma() -> List[Dict[str, Any]]:
                try:
                    hits = self._collection.query(query_texts=[context], n_results=top_k)
                    out: List[Dict[str, Any]] = []
                    docs = hits.get("documents", [])
                    metas = hits.get("metadatas", [])
                    ids = hits.get("ids", [])
                    if docs and metas and ids:
                        for doc_list, meta_list, id_list in zip(docs, metas, ids):
                            for d, m, i in zip(doc_list, meta_list, id_list):
                                out.append({"id": i, "summary": d, "metadata": m})
                    return out
                except Exception:
                    logger.exception("Chroma query failed")
                    return []

            results = await loop.run_in_executor(None, _query_chroma)
            return results

        # Qdrant query path
        if self._is_qdrant and self._client is not None:
            def _query_qdrant() -> List[Dict[str, Any]]:
                try:
                    # If we have an embed method, use it to create a query vector
                    vec = None
                    if self._llm is not None and hasattr(self._llm, "embed"):
                        try:
                            # Prefer synchronous embed() if available to avoid blocking the event loop
                            vec = self._llm.embed(context)
                        except Exception:
                            vec = None

                    out: List[Dict[str, Any]] = []
                    if vec is not None:
                        # use vector search
                        try:
                            hits = self._client.search(collection_name=self._collection_name, query_vector=vec, limit=top_k)
                            for h in hits:
                                payload = getattr(h, 'payload', None) or h.payload if hasattr(h, 'payload') else None
                                summary = payload.get('text') if isinstance(payload, dict) else None
                                out.append({"id": str(h.id), "summary": summary or "", "metadata": payload or {}})
                            return out
                        except Exception:
                            logger.exception("Qdrant vector search failed; falling back to scan")

                    # fallback: scan payloads and substring match
                    try:
                        scroll = self._client.scroll(collection_name=self._collection_name, limit=1000)
                        for item in scroll:
                            payload = getattr(item, 'payload', None) or item.payload if hasattr(item, 'payload') else {}
                            text = payload.get('text', '') if isinstance(payload, dict) else ''
                            if context.lower() in text.lower() or context.lower() in str(payload.get('task_name', '')).lower():
                                out.append({"id": str(item.id), "summary": text, "metadata": payload})
                                if len(out) >= top_k:
                                    break
                    except Exception:
                        logger.exception("Qdrant scan failed")
                    return out
                except Exception:
                    logger.exception("Qdrant query failed")
                    return []

            results = await loop.run_in_executor(None, _query_qdrant)
            return results

        # fallback (shouldn't reach here)
        # If other paths fail to return anything, fall back to any in-memory backup
        if self._in_memory:
            results = []
            for r in self._in_memory:
                summary_val = r.get("summary", "")
                summary_text = summary_val if isinstance(summary_val, str) else str(summary_val)
                task_name_text = r.get("metadata", {}).get("task_name", "")
                if context.lower() in summary_text.lower() or context.lower() in str(task_name_text).lower():
                    results.append({"id": r["id"], "summary": r["summary"], "metadata": r.get("metadata", {})})
            return results[:top_k]
        return []

    async def retrieve_relevant_intelligence(self, goal: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return relevant intelligence artifacts for a new root goal.

        The retrieval is deterministic and keyword-driven and biases results by
        node confidence and optional priority weight encoded in metadata.
        """
        try:
            tokens = [w.strip('.,').lower() for w in goal.split() if len(w) > 3]
            hits: List[Dict[str, Any]] = []
            for tok in tokens:
                sub = await self.query(tok, top_k=top_k)
                if sub:
                    hits.extend(sub)
            seen_ids = set()
            unique: List[Dict[str, Any]] = []
            for h in hits:
                hid = h.get('id')
                if hid and hid not in seen_ids:
                    seen_ids.add(hid)
                    # compute score bias
                    node = self._graph.get(hid)
                    score = 1.0
                    if node:
                        score *= node.confidence or 1.0
                        score *= max(0.1, 1.0 - node.contradiction_risk)
                    # bias by explicit priority stored in metadata
                    try:
                        prio = float(h.get("metadata", {}).get("priority", 1.0))
                    except Exception:
                        prio = 1.0
                    score *= prio
                    h["score"] = score
                    unique.append(h)
            # sort by score desc then id
            unique.sort(key=lambda r: (-r.get("score", 0.0), r.get("id", "")))
            # ensure deterministic return order
            return unique[:top_k]
        except Exception:
            logger.exception("retrieve_relevant_intelligence failed")
            return []

    async def health_check(self) -> bool:
        """Async health check for the configured vector DB client.

        Returns True when Qdrant (or the configured client) is reachable and
        responds to a collections request. Returns False on any error or when
        no external client is configured.
        """
        if self._client is None:
            return False
        loop = asyncio.get_running_loop()

        def _check() -> bool:
            try:
                # Prefer bulk collections API; fall back to single-collection query
                if hasattr(self._client, "get_collections"):
                    _ = self._client.get_collections()
                else:
                    _ = self._client.get_collection(collection_name=self._collection_name)
                return True
            except Exception:
                logger.exception("Vector DB health check failed")
                return False

        return await loop.run_in_executor(None, _check)

    async def compress_old_memories(self, force: bool = False, keep_recent: int = 50) -> Optional[str]:
        """Compress older memory entries into a single archived summary.

        If the number of stored in-memory entries exceeds the configured
        threshold (or `force` is True) this function will summarize the
        older entries with the provided LLM and replace them with a single
        compressed record marked with metadata `archived: True` and a list
        of `compressed_from` ids.
        Returns the id of the compressed record, or None if no action taken.
        """
        if self._llm is None:
            logger.debug("No LLM available; skipping compression")
            return None

        # operate on in-memory store only; for chroma attempt similar ops
        if self._collection is None:
            if not force and len(self._in_memory) <= self._compress_threshold:
                return None

            # sort by timestamp if available
            entries = list(self._in_memory)
            try:
                entries.sort(key=lambda x: x.get("metadata", {}).get("timestamp", ""))
            except Exception:
                pass

            if len(entries) <= keep_recent:
                return None

            to_compress = entries[:-keep_recent]
            remaining = entries[-keep_recent:]

            # build a single prompt for summarization
            concat_text = "\n\n".join([str(e.get("summary", "")) for e in to_compress])
            prompt = (
                "You are an assistant that compresses and summarizes multiple memory entries into a "
                "concise coherent summary suitable for long-term archival. Produce a short summary, "
                "and a bullet list of the main points."
            )

            try:
                summary = await self._llm.generate(prompt, context=concat_text)
            except Exception:
                logger.exception("LLM summarization failed")
                return None

            compressed_id = f"compressed_{int(datetime.utcnow().timestamp())}_{abs(hash(summary))}"
            compressed_meta = {
                "archived": True,
                "compressed_from": [e["id"] for e in to_compress],
                "timestamp": datetime.utcnow().isoformat(),
            }

            # replace in-memory store
            self._in_memory = [*remaining, {"id": compressed_id, "summary": summary, "metadata": compressed_meta}]
            logger.info("Compressed %d entries into %s", len(to_compress), compressed_id)
            return compressed_id

        # If using chroma, attempt to compress via LLM and update collection
        loop = asyncio.get_running_loop()

        def _chroma_ops() -> Optional[str]:
            try:
                # fetch all docs' metadatas/ids via a naive query if API allows
                # Some chroma clients don't expose list; we try get and fallback
                try:
                    all_ids = [m["id"] for m in self._collection.get_all_ids()]
                except Exception:
                    # fallback: no list API; abort
                    logger.debug("Chroma client does not support listing ids; skipping compression")
                    return None

                # try to fetch documents by ids if supported
                docs = []
                for i in all_ids:
                    try:
                        q = self._collection.get(ids=[i])
                        # get may return dict with documents/metadatas/ids
                        for docs_list in q.get("documents", []) if isinstance(q, dict) else []:
                            for d in docs_list:
                                docs.append((i, d))
                    except Exception:
                        continue

                if len(docs) <= keep_recent:
                    return None

                to_comp = docs[:-keep_recent]
                concat = "\n\n".join([str(d[1]) for d in to_comp])
                # call LLM synchronously is not available; we'll return and let async call LLM
                return ("||TO_COMPRESS||", concat, [d[0] for d in to_comp])
            except Exception:
                logger.exception("Chroma compression failed")
                return None

        res = await loop.run_in_executor(None, _chroma_ops)
        if not res:
            return None

        # res is a tuple marker; perform async LLM call
        try:
            _, concat_text, ids_to_remove = res
            summary = await self._llm.generate(
                "Compress these memory documents into a concise archived summary.", context=concat_text
            )
        except Exception:
            logger.exception("LLM summarization failed for chroma compression")
            return None

        comp_id = f"compressed_{int(datetime.utcnow().timestamp())}_{abs(hash(summary))}"
        comp_meta = {"archived": True, "compressed_from": ids_to_remove, "timestamp": datetime.utcnow().isoformat()}

        def _commit_chroma():
            try:
                # attempt deletion then add compressed doc
                try:
                    self._collection.delete(ids=ids_to_remove)
                except Exception:
                    logger.debug("Chroma collection delete not supported or failed; continuing")
                try:
                    # sanitize comp_meta values to primitives or JSON strings for chroma
                    safe_comp_meta = {}
                    for kk, vv in (comp_meta or {}).items():
                        if vv is None or isinstance(vv, (str, int, float, bool)):
                            safe_comp_meta[kk] = vv
                        elif isinstance(vv, list):
                            new_list = []
                            for item in vv:
                                if item is None or isinstance(item, (str, int, float, bool)):
                                    new_list.append(item)
                                else:
                                    try:
                                        new_list.append(json.dumps(item))
                                    except Exception:
                                        new_list.append(str(item))
                            safe_comp_meta[kk] = new_list
                        else:
                            try:
                                safe_comp_meta[kk] = json.dumps(vv)
                            except Exception:
                                safe_comp_meta[kk] = str(vv)

                    self._collection.add(documents=[summary], metadatas=[safe_comp_meta], ids=[comp_id])
                except Exception:
                    logger.exception("Chroma add of compressed doc failed")
                    return None
                return comp_id
            except Exception:
                logger.exception("Chroma commit failed")
                return None

        out_id = await loop.run_in_executor(None, _commit_chroma)
        return out_id

    async def migrate_from_disk(self, data_dir: Optional[str] = None) -> int:
        """Ingest JSON files from `./data` into the vector DB if the DB appears empty.

        Returns number of ingested records.
        """
        data_dir = data_dir or os.getenv("DATA_DIR", os.path.join(os.getcwd(), "data"))
        if not os.path.isdir(data_dir):
            # Serverless environments may mount app code under /var/task (read-only)
            # and provide /tmp for writable disk. Prefer explicit DATA_DIR, /tmp/data,
            # and fallback to /var/task/data if writable for local-only setups.
            # Prefer an explicit DATA_DIR, then a writable /tmp/data (serverless),
            # then a repo-local ./data, and only use /var/task/data as a last-resort
            # if it is actually writable. Perform a quick write check to avoid
            # selecting a read-only path.
            candidates = [
                os.getenv("DATA_DIR", ""),
                "/tmp/data",
                str(Path(__file__).resolve().parent.parent / "data"),
                "/var/task/data",
            ]
            selected = None
            for candidate in candidates:
                if not candidate:
                    continue
                try:
                    os.makedirs(candidate, exist_ok=True)
                except Exception:
                    # can't create; try next candidate
                    continue
                # quick writable check
                test_path = os.path.join(candidate, ".write_test")
                try:
                    with open(test_path, "w", encoding="utf-8") as f:
                        f.write("ok")
                    try:
                        os.remove(test_path)
                    except Exception:
                        pass
                    selected = candidate
                    break
                except Exception:
                    # not writable, try next
                    continue

            if selected is None:
                logger.info("No available data directory; skipping migration from disk")
                return 0

            data_dir = selected

        # check if DB already has data
        try:
            if self._client is None:
                logger.debug("No vector DB client; skipping migration")
                return 0
            # chroma: try count via collection.count()
            if self._vector_db == "chroma" and self._collection is not None:
                try:
                    c = getattr(self._collection, "count", None)
                    if c is not None:
                        if callable(c) and c() > 0:
                            return 0
                except Exception:
                    pass
            if self._is_qdrant and self._client is not None:
                try:
                    cnt = self._client.count(collection_name=self._collection_name).count
                    if cnt and cnt > 0:
                        return 0
                except Exception:
                    pass
        except Exception:
            logger.exception("Migration pre-check failed")

        ingested = 0
        loop = asyncio.get_running_loop()

        for fname in os.listdir(data_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(data_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    obj = __import__("json").load(fh)
                key = os.path.splitext(fname)[0]
                summary = obj if not isinstance(obj, str) else str(obj)
                metadata = {"task_name": key, "migrated": True, "timestamp": datetime.utcnow().isoformat()}
                # store via existing API
                await self.store_summary(task_name=key, summary=str(summary), metadata=metadata)
                ingested += 1
            except Exception:
                logger.exception("Failed to ingest %s", path)

        logger.info("Migration ingested %d records from %s", ingested, data_dir)
        return ingested

    def schedule_migration(self, data_dir: Optional[str] = None) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.migrate_from_disk(data_dir=data_dir))
        except RuntimeError:
            # no running loop; caller may call migrate_from_disk explicitly
            logger.debug("No running event loop; migration not scheduled automatically")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.DEBUG)

    async def _demo():
        ms = MemoryStore()
        await ms.store_summary("taskA", "This is a test summary", {"status": "complete"})
        res = await ms.query("test", top_k=5)
        print(res)

    asyncio.run(_demo())
