import shutil
import json
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma

from app.core.config import settings


MARKDOWN_DIR = settings.MARKDOWN_DIR
CHROMA_DIR = settings.CHROMA_DIR

COLLECTION_NAME = settings.CHROMA_COLLECTION

def load_markdown_documents():
    loader = DirectoryLoader(
        path=str(MARKDOWN_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={
            "encoding": "utf-8",
        },
        show_progress=True,
    )

    documents = loader.load()
    return enrich_document_metadata(documents)

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
    )

    chunks = splitter.split_documents(documents)
    return chunks

def reset_chroma_db():
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)

def ingest_documents():
    print("Loading Markdown documents...")
    documents = load_markdown_documents()

    print(f"Loaded documents: {len(documents)}")

    if not documents:
        print("No Markdown documents found.")
        return

    print("Splitting documents into chunks...")
    chunks = split_documents(documents)

    print(f"Created chunks: {len(chunks)}")

    print("Resetting Chroma database...")
    reset_chroma_db()

    print("Creating embeddings and saving to Chroma...")
    embeddings = FastEmbedEmbeddings()

    Chroma.from_documents(
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
        documents=chunks,
        embedding=embeddings,
    )

    print("Ingestion completed.")
    print(f"Chroma DB saved at: {CHROMA_DIR}")

def enrich_document_metadata(documents):
    for document in documents:
        source = Path(document.metadata.get("source", ""))
        cache_path = source.with_suffix(".json")

        if cache_path.exists():
            try:
                metadata = json.loads(cache_path.read_text(encoding="utf-8"))
                metadata.setdefault("original_file", metadata.get("source_file", str(source)))
                metadata.setdefault("original_extension", metadata.get("source_extension", source.suffix.lower()))
                metadata.setdefault("markdown_file", str(source))
                metadata.setdefault("converter", "markitdown")
                document.metadata.update(metadata)
            except (OSError, json.JSONDecodeError):
                document.metadata.update(
                    {
                        "original_file": str(source),
                        "markdown_file": str(source),
                        "converter": "markitdown",
                        "original_extension": source.suffix.lower(),
                    }
                )
        else:
            document.metadata.update(
                {
                    "original_file": str(source),
                    "markdown_file": str(source),
                    "converter": "none",
                    "original_extension": source.suffix.lower(),
                }
            )

    return documents
