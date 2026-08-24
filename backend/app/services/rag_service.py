import logging
import re
from pathlib import Path
from typing import Any
import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from ..config import settings

logger = logging.getLogger("rag_interviewer.rag")

def sanitize_role_name(role: str) -> str:
    """Sanitize a role name into a valid Chroma collection name."""
    if not role or role.strip().lower() in ("global", "general", "all", "kb_global"):
        return "kb_global"
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", role.lower().strip()).strip("_")
    return f"kb_{clean}" if not clean.startswith("kb_") else clean

def create_sliding_window_chunks(
    text: str,
    source: str = "knowledge_base",
    role: str = "global",
    page: int = 1,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    extra_metadata: dict[str, Any] | None = None
) -> list[dict]:
    """
    Split text into sliding-window chunks with configurable word size and overlap.
    Preserves page and source metadata for grounded citations.
    """
    cleaned_text = " ".join(text.split())
    if not cleaned_text:
        return []

    words = cleaned_text.split()
    chunks: list[dict] = []
    start = 0
    chunk_idx = 0
    safe_source_stem = re.sub(r"[^a-zA-Z0-9]+", "_", Path(source).stem).strip("_")

    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        if chunk_text.strip():
            chunk_id = f"{safe_source_stem}-p{page}-c{chunk_idx}"
            chunk_data = {
                "id": chunk_id,
                "text": chunk_text,
                "source": Path(source).name,
                "chunk": chunk_idx,
                "page": page,
                "role": role,
                "char_count": len(chunk_text),
                "word_count": len(chunk_words),
            }
            if extra_metadata:
                chunk_data.update(extra_metadata)
            chunks.append(chunk_data)
            chunk_idx += 1

        if end >= len(words):
            break
        start = end - chunk_overlap
        if start < 0:
            start = 0

    return chunks

class RAGService:
    def __init__(
        self,
        chroma_path: str | None = None,
        embedding_model: str | None = None
    ):
        self.chroma_path = chroma_path or settings.chroma_path
        self.embedding_model_name = embedding_model or settings.embedding_model
        self.embedder = SentenceTransformer(self.embedding_model_name)
        self.client = chromadb.PersistentClient(path=self.chroma_path)

    def collection(self, role: str):
        """Get or create collection for a given role (backward compatible)."""
        name = sanitize_role_name(role)
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

    def get_collection(self, role: str):
        """Alias to collection()."""
        return self.collection(role)

    def list_collections(self) -> list[str]:
        """List all collection names in the vector database."""
        return [c.name for c in self.client.list_collections()]

    def get_collection_stats(self, role: str | None = None) -> dict:
        """Get item count for a specific collection or all collections."""
        if role:
            col = self.collection(role)
            return {"role": role, "collection": col.name, "count": col.count()}
        stats = {}
        for col_name in self.list_collections():
            c = self.client.get_collection(col_name)
            stats[col_name] = c.count()
        return stats

    def ingest(self, role: str, chunks: list[dict], also_to_global: bool = True) -> int:
        """
        Upsert chunks into the role collection, and optionally into the global collection.
        """
        if not chunks:
            return 0

        target_col = self.collection(role)
        docs = [x["text"] for x in chunks]
        ids = [x["id"] for x in chunks]
        metadatas = [
            {
                "source": x.get("source", "knowledge_base"),
                "chunk": int(x.get("chunk", 0)),
                "page": int(x.get("page", 1)),
                "role": str(x.get("role", role)),
                "char_count": int(x.get("char_count", len(x["text"]))),
            }
            for x in chunks
        ]

        embeddings = self.embedder.encode(docs, normalize_embeddings=True).tolist()

        target_col.upsert(
            ids=ids,
            documents=docs,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        logger.info(f"Ingested {len(chunks)} chunks into collection '{target_col.name}'")

        # Also ingest into global pool if not already the global collection
        if also_to_global and sanitize_role_name(role) != "kb_global":
            global_col = self.collection("global")
            global_ids = [f"global-{chunk_id}" for chunk_id in ids]
            global_col.upsert(
                ids=global_ids,
                documents=docs,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            logger.info(f"Mirrored {len(chunks)} chunks into '{global_col.name}'")

        return len(chunks)

    def retrieve(
        self,
        role: str,
        query: str,
        top_k: int | None = None,
        metadata_filter: dict | None = None,
        score_threshold: float = 0.0
    ) -> list[dict]:
        """
        Retrieve relevant chunks with fallback to global pool, metadata filtering,
        cosine similarity scoring, and formatted citation metadata.
        """
        target_col = self.collection(role)
        effective_role = role

        # Fallback to global collection if role collection is empty
        if target_col.count() == 0 and sanitize_role_name(role) != "kb_global":
            global_col = self.collection("global")
            if global_col.count() > 0:
                logger.info(
                    f"Role collection '{target_col.name}' is empty. Falling back to '{global_col.name}'."
                )
                target_col = global_col
                effective_role = "global"

        if target_col.count() == 0:
            logger.warning(f"No knowledge base documents found in '{target_col.name}' or fallback.")
            return []

        limit = min(top_k or settings.top_k, target_col.count())
        query_embedding = self.embedder.encode([query], normalize_embeddings=True).tolist()

        query_args: dict[str, Any] = {
            "query_embeddings": query_embedding,
            "n_results": limit,
        }
        if metadata_filter:
            query_args["where"] = metadata_filter

        try:
            result = target_col.query(**query_args)
        except Exception as e:
            logger.error(f"Chroma query failed with filter {metadata_filter}: {e}")
            # Retry without metadata filter if filter failed
            if metadata_filter:
                query_args.pop("where")
                result = target_col.query(**query_args)
            else:
                return []

        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0] if result.get("distances") else []
        ids = result.get("ids", [[]])[0] if result.get("ids") else []

        retrieved: list[dict] = []
        for i, (doc, meta) in enumerate(zip(docs, metas)):
            chunk_id = ids[i] if i < len(ids) else f"chunk-{i}"
            dist = distances[i] if i < len(distances) else 0.0
            # For cosine distance in [0, 2], similarity is 1.0 - distance
            similarity = max(0.0, min(1.0, 1.0 - dist)) if distances else 1.0

            if similarity < score_threshold:
                continue

            source_name = meta.get("source", "knowledge_base")
            page_num = meta.get("page", 1)
            chunk_num = meta.get("chunk", i)

            citation = f"[{source_name} (p. {page_num}, chunk {chunk_num})]"

            retrieved.append({
                "text": doc,
                "source": source_name,
                "chunk_id": chunk_id,
                "chunk_index": chunk_num,
                "page": page_num,
                "role": meta.get("role", effective_role),
                "score": round(similarity, 4),
                "citation": citation,
            })

        return retrieved

    def ingest_pdf(
        self,
        file_path: str | Path,
        role: str = "global",
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        also_to_global: bool = True
    ) -> int:
        """Extract pages from a PDF file, apply sliding-window chunking, and ingest."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        reader = PdfReader(str(path))
        all_chunks: list[dict] = []

        for page_idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                page_chunks = create_sliding_window_chunks(
                    text=page_text,
                    source=path.name,
                    role=role,
                    page=page_idx,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                all_chunks.extend(page_chunks)

        if not all_chunks:
            logger.warning(f"No extractable text found in PDF: {path.name}")
            return 0

        return self.ingest(role=role, chunks=all_chunks, also_to_global=also_to_global)

