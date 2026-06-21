import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.core.config import settings
from app.services.retriever import search_documents
from app.services.llm import generate_answer
from app.services.ingest import ingest_documents
from app.services.converter import (
    MarkdownConversionError,
    UnsupportedFileTypeError,
    convert_to_markdown,
)

logger = logging.getLogger(__name__)
router = APIRouter()

class AskRequest(BaseModel):
    question: str


class Source(BaseModel):
    file: str
    preview: str


class AskData(BaseModel):
    answer: str
    sources: list[Source]

class AskResponse(BaseModel):
    status: str
    message: str
    data: AskData


class IngestData(BaseModel):
    documents_indexed: int | None = None

class IngestResponse(BaseModel):
    status: str
    message: str
    data: IngestData | None = None


class UploadData(BaseModel):
    filename: str
    saved_path: str
    markdown_path: str

class UploadResponse(BaseModel):
    status: str
    message: str
    data: UploadData

def build_context(results) -> str:
    context_parts = []

    for doc, score in results:
        source = doc.metadata.get("original_file") or doc.metadata.get("source", "unknown")
        content = doc.page_content

        context_parts.append(
            f"Source: {source}\nContent:\n{content}"
        )

    return "\n\n---\n\n".join(context_parts)

@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    question = request.question.strip()
    logger.info("Received question: %s", question)

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )
    
    try:
        results = search_documents(question, k=3)
        logger.info("Retrieved %s chunks", len(results))

        if not results:
            raise HTTPException(
                status_code=404,
                detail="No relevant documents found.",
            )

        context = build_context(results)
        answer = generate_answer(context=context, question=question)

        sources = []

        for doc, score in results:
            sources.append(
                Source(
                    file=doc.metadata.get("original_file") or doc.metadata.get("source", "unknown"),
                    preview=doc.page_content[:200],
                )
            )

        return AskResponse(
            status="success",
            message="Answer generated successfully.",
            data=AskData(
                answer=answer,
                sources=sources,
            ),
        )
    
    except HTTPException:
        raise 

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ask failed: {str(e)}",
        )

@router.post("/ingest", response_model=IngestResponse)
def ingest():
    try:
        logger.info("Starting ingestion")
        ingest_documents()

        logger.info("Ingestion completed successfully")

        return IngestResponse(
            status="success",
            message="Documents ingested successfully.",
            data=None,
        )

    except Exception as e:
        logger.exception("Ingestion failed")

        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}",
        )
    
@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    try:
        allowed_extensions = {
            ".md",
            ".pdf",
            ".docx",
            ".pptx",
            ".xlsx",
            ".html",
            ".csv",
            ".json",
            ".txt",
        }

        filename = Path(file.filename or "").name
        file_ext = Path(filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type.",
            )

        if file_ext == ".md":
            upload_dir = settings.MARKDOWN_DIR
        else:
            upload_dir = settings.RAW_DOCUMENT_DIR

        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_path = upload_dir / filename

        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        saved_path.write_bytes(content)

        try:
            markdown_path = convert_to_markdown(saved_path)
        except UnsupportedFileTypeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except MarkdownConversionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        ingest_documents()

        logger.info("Knowledge base rebuilt after upload")

        return UploadResponse(
            status="success",
            message="File uploaded and indexed successfully.",
            data=UploadData(
                filename=filename,
                saved_path=str(saved_path),
                markdown_path=str(markdown_path),
            ),
        )
    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Upload failed")

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}",
        )
