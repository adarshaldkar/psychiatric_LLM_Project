"""
Seed script — ingest the 3 psychiatry books as global documents.

Run once after Phase 2 setup:
    cd backend
    python seed_books.py

Books are ingested as is_global=True so all users can retrieve from them.
"""
import sys
import os
import shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, Base, engine, create_vector_indexes
from app.models.models import Document, User
from app.rag.ingestion import ingest_document
from app.core.config import settings

BOOKS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Books'))
UPLOAD_DIR = settings.UPLOAD_DIR

BOOKS = [
    {
        "path": os.path.join(BOOKS_DIR, "CabanissPsychodynamicPsychother.pdf"),
        "name": "Cabanis — Psychodynamic Psychotherapy",
        "author": "Deborah L. Cabanis et al.",
        "tags": ["psychodynamic", "psychotherapy", "clinical"],
    },
    {
        "path": os.path.join(BOOKS_DIR, "Theory and Practice of Counseling and Psychotherapy- Corey- 9ed.pdf"),
        "name": "Corey — Theory and Practice of Counseling and Psychotherapy (9th ed)",
        "author": "Gerald Corey",
        "tags": ["counseling", "psychotherapy", "theory"],
    },
    {
        "path": os.path.join(BOOKS_DIR, "1993_eysenck_-_forty_years_on_the_outcome_problem_in_psychotherapy.pdf"),
        "name": "Eysenck — Forty Years on the Outcome Problem in Psychotherapy",
        "author": "H.J. Eysenck",
        "tags": ["psychotherapy", "outcome", "research"],
    },
]


def get_or_create_system_user(db) -> User:
    """Get or create a system user for global documents."""
    system_email = "system@mindcare.ai"
    user = db.query(User).filter(User.email == system_email).first()
    if not user:
        from app.core.security import hash_password
        import uuid
        user = User(
            email=system_email,
            password_hash=hash_password("system_password_not_used"),
            full_name="MindCare System",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created system user: {user.id}")
    return user


def seed():
    print("\n" + "=" * 60)
    print("MindCare AI — Seeding Global Knowledge Base")
    print("=" * 60)

    # Ensure tables and indexes exist
    Base.metadata.create_all(bind=engine)
    try:
        create_vector_indexes()
    except Exception as e:
        print(f"[WARN] Vector indexes: {e}")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    db = SessionLocal()
    system_user = get_or_create_system_user(db)

    for book in BOOKS:
        book_path = os.path.abspath(book["path"])
        if not os.path.exists(book_path):
            print(f"[SKIP] File not found: {book_path}")
            continue

        # Check if already seeded
        existing = db.query(Document).filter(
            Document.original_name == book["name"],
            Document.is_global == True,
            Document.is_latest == True,
        ).first()
        if existing:
            print(f"[SKIP] Already seeded: {book['name']} (status: {existing.status})")
            continue

        # Copy to uploads dir
        import uuid as uuid_mod
        safe_name = f"{uuid_mod.uuid4().hex}_{os.path.basename(book_path)}"
        dest_path = os.path.join(UPLOAD_DIR, safe_name)
        shutil.copy2(book_path, dest_path)
        file_size = os.path.getsize(dest_path)

        # Create Document record
        doc = Document(
            user_id=system_user.id,
            filename=safe_name,
            original_name=book["name"],
            file_type='pdf',
            file_size_bytes=file_size,
            is_global=True,
            status='uploaded',
            author=book.get("author"),
            tags=book.get("tags", []),
            version_number=1,
            is_latest=True,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        print(f"\n[INGESTING] {book['name']}")
        print(f"  File: {os.path.basename(book_path)}")
        print(f"  Size: {file_size / 1024 / 1024:.1f}MB")
        print(f"  Document ID: {doc.id}")
        print("  Processing... (this may take several minutes)")

        # Run ingestion synchronously for seeding
        ingest_document(str(doc.id))

        # Check final status
        db.refresh(doc)
        print(f"  Final status: {doc.status}")
        if doc.chunk_count:
            print(f"  Chunks created: {doc.chunk_count} ({doc.total_tokens} tokens)")
        if doc.error_message:
            print(f"  Error: {doc.error_message}")

    db.close()
    print("\n" + "=" * 60)
    print("Seeding complete!")
    print("=" * 60)


if __name__ == '__main__':
    seed()
