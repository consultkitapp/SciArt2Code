import uuid
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import chromadb
from sentence_transformers import SentenceTransformer


class AgentMemory:
    def __init__(self, workspace_path: str | Path = "~/agent_workspace"):
        # Use pathlib for robust path resolution
        self.workspace_path = Path(workspace_path).expanduser()
        db_path = self.workspace_path / "chroma_memory"
        
        # Load the model (runs synchronously during initialization)
        self.encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        
        # Initialize ChromaDB persistent client
        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_or_create_collection(name="project_memory")

    async def remember(self, text: str, metadata: Optional[dict[str, Any]] = None) -> str:
        """Asynchronously stores text and metadata into ChromaDB without blocking the event loop."""
        doc_id = str(uuid.uuid4())
        safe_metadata = metadata or {}
        safe_metadata["timestamp"] = time.time()

        # Run CPU-bound encoding in a separate thread
        vector = await asyncio.to_thread(self.encoder.encode, text)
        
        # Run DB I/O in a separate thread
        await asyncio.to_thread(
            self.collection.add,
            ids=[doc_id],
            embeddings=[vector.tolist()],
            documents=[text],
            metadatas=[safe_metadata]
        )
        
        return doc_id

    async def recall_chronological(self, query: str, n_results: int = 5) -> str:
        """Asynchronously retrieves and chronologically sorts relevant memories."""
        # Run CPU-bound encoding in a separate thread
        query_vector = await asyncio.to_thread(self.encoder.encode, query)

        # Run DB query in a separate thread
        results = await asyncio.to_thread(
            self.collection.query,
            query_embeddings=[query_vector.tolist()],
            n_results=n_results
        )

        if not results.get("documents") or not results["documents"][0]:
            return "No previous context found."

        docs = results["documents"][0]
        metas = results["metadatas"][0]

        paired_results = list(zip(docs, metas))
        
        # Sort oldest to newest (ascending) so the most recent fact is at the bottom
        paired_results.sort(key=lambda x: x[1].get("timestamp", 0))

        timeline = []
        for doc, meta in paired_results:
            date_str = datetime.fromtimestamp(meta["timestamp"]).strftime('%Y-%m-%d %H:%M')
            timeline.append(f"[{date_str}] {doc}")

        return "\n".join(timeline)


class MemoryBuffer:
    def __init__(self):
        self.events: list[str] = []

    def add_event(self, event: str):
        self.events.append(event)

    def flush(self) -> list[str]:
        """Returns the current buffer and clears it."""
        events = self.events.copy()
        self.events.clear()
        return events
