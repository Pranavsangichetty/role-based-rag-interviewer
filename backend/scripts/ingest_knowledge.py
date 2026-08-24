import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.services.rag_service import RAGService, create_sliding_window_chunks
from pypdf import PdfReader

DEFAULT_ROLES = ["AI/ML Engineer", "Backend Engineer", "Data Scientist"]

def ingest_directory(
    input_dir: Path,
    target_role: str = "all",
    chunk_size: int = 500,
    chunk_overlap: int = 100
):
    rag = RAGService()
    kb_dir = Path(input_dir)

    if not kb_dir.exists():
        kb_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(kb_dir.rglob("*.pdf"))
    if not pdfs:
        print(f"[!] No PDF files found in: {kb_dir}")
        print("    Place your textbook or reference PDF in 'backend/data/knowledge_base/' and run again.")
        return 0

    print(f"[*] Found {len(pdfs)} PDF file(s) in {kb_dir}")
    total_ingested = 0

    for pdf in pdfs:
        print(f"[*] Processing: {pdf.name}")
        reader = PdfReader(str(pdf))
        file_chunks = []

        for page_idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                p_chunks = create_sliding_window_chunks(
                    text=page_text,
                    source=pdf.name,
                    role=target_role,
                    page=page_idx,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                file_chunks.extend(p_chunks)

        if not file_chunks:
            print(f"[-] Warning: No extractable text found in {pdf.name}")
            continue

        # Ingest into target roles
        if target_role == "all":
            # Ingest into global pool and all default interview roles
            for role in DEFAULT_ROLES:
                rag.ingest(role=role, chunks=file_chunks, also_to_global=True)
            print(f"[+] Ingested {len(file_chunks)} chunks from '{pdf.name}' into roles {DEFAULT_ROLES} and 'kb_global'")
        else:
            rag.ingest(role=target_role, chunks=file_chunks, also_to_global=True)
            print(f"[+] Ingested {len(file_chunks)} chunks from '{pdf.name}' into role '{target_role}' and 'kb_global'")

        total_ingested += len(file_chunks)

    print("\n--- Vector Database Statistics ---")
    stats = rag.get_collection_stats()
    for col_name, count in stats.items():
        print(f"  Collection '{col_name}': {count} documents")
    print(f"Total processed chunks: {total_ingested}")
    return total_ingested

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest knowledge base PDFs into ChromaDB.")
    parser.add_argument("--input-dir", type=str, default=settings.knowledge_base_dir, help="Directory containing knowledge base PDFs")
    parser.add_argument("--role", type=str, default="all", help="Target role (e.g., 'AI/ML Engineer', 'Backend Engineer', or 'all')")
    parser.add_argument("--chunk-size", type=int, default=500, help="Sliding window chunk size in words")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="Sliding window overlap in words")

    args = parser.parse_args()
    ingest_directory(
        input_dir=Path(args.input_dir),
        target_role=args.role,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )

