"""
MindCare AI — Database Inspector Script
Run this script to view all stored data in PostgreSQL (Users, Documents, Vector Chunks, Memories, Conversations).
"""
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine
from app.models.models import User, Document, DocumentChunk, Conversation, Message, LongTermMemory
from sqlalchemy import text

def inspect_database():
    db = SessionLocal()
    print("=" * 80)
    print("  MINDCARE AI -- POSTGRESQL + PGVECTOR LIVE DATABASE INSPECTION")
    print("=" * 80)

    try:
        # 1. Connection check
        res = db.execute(text("SELECT current_database(), current_user, version();")).fetchone()
        print(f"\n[+] Connected to DB: {res[0]} | User: {res[1]}")
        print(f"[+] Postgres Version: {res[2][:50]}...")

        # 2. Check pgvector extension
        vec_check = db.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")).fetchone()
        if vec_check:
            print(f"[OK] pgvector Extension Installed: v{vec_check[1]}")
        else:
            print("[WARN] pgvector extension check skipped or not in default schema")

        # 3. Users Table
        users = db.query(User).all()
        print(f"\n[USERS] Registered ({len(users)} users):")
        for u in users:
            print(f"   * ID: {u.id} | Email: {u.email} | Name: {u.full_name} | Joined: {u.created_at}")

        # 4. Documents Table
        docs = db.query(Document).all()
        print(f"\n[DOCUMENTS] Uploaded ({len(docs)} docs):")
        for d in docs:
            progress = round(d.embedded_chunk_count/d.child_chunk_count*100) if (d.embedded_chunk_count and d.child_chunk_count) else 0
            print(f"   * Name: {d.original_name} | Type: {d.file_type} | Status: {d.status}")
            print(f"     ID: {d.id} | Chunks: Total={d.chunk_count}, Embedded={d.embedded_chunk_count}/{d.child_chunk_count} ({progress}%)")

        # 5. Vector Chunks Table (DocumentChunk)
        total_chunks = db.query(DocumentChunk).count()
        embedded_chunks = db.query(DocumentChunk).filter(DocumentChunk.embedding != None).count()
        print(f"\n[VECTOR CHUNKS] PostgreSQL pgvector store:")
        print(f"   * Total Text Chunks in DB: {total_chunks}")
        print(f"   * Chunks with 1536-dim Vector Embeddings: {embedded_chunks}")

        # Show sample vector chunk with text snippet and embedding preview
        sample_chunk = db.query(DocumentChunk).filter(DocumentChunk.embedding != None).first()
        if sample_chunk:
            emb_str = str(sample_chunk.embedding) if sample_chunk.embedding else "None"
            emb_preview = emb_str[:60] + "..." if len(emb_str) > 60 else emb_str
            print(f"\n   --- Sample Vector Chunk in PostgreSQL ---")
            print(f"   Document ID:  {sample_chunk.document_id}")
            print(f"   Page Number:  {sample_chunk.page_number} | Type: {sample_chunk.chunk_type} | Section: {sample_chunk.section}")
            print(f"   Text Snippet: {sample_chunk.chunk_text[:120]}...")
            print(f"   1536-d HNSW Vector: {emb_preview}")

        # 6. Conversations & Messages
        convs = db.query(Conversation).all()
        total_msgs = db.query(Message).count()
        print(f"\n[CONVERSATIONS] Active Chat Sessions ({len(convs)} convs, {total_msgs} messages):")
        for c in convs[:5]:  # print first 5
            print(f"   * [{c.title}] ID: {c.id} | Messages: {len(c.messages)}")
        if len(convs) > 5:
            print(f"   ... and {len(convs) - 5} more conversations")

        # 7. Long-Term Memories
        mems = db.query(LongTermMemory).all()
        print(f"\n[LONG-TERM MEMORIES] Recalled Facts ({len(mems)} memories):")
        for m in mems[:5]:
            print(f"   * Type: {m.memory_type} | Content: {m.content[:80]}... | Importance: {getattr(m, 'importance_score', 1.0)}")
        if len(mems) > 5:
            print(f"   ... and {len(mems) - 5} more memories")

        print("\n" + "=" * 80)
        print("  [SUCCESS] Live PostgreSQL + pgvector inspection complete!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Inspection failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_database()
