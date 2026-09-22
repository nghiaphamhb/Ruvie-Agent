import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "backend"))
from ruvie.document_citation import CitationBuilder

class CitationTests(unittest.TestCase):
    def test_stable_id_uses_immutable_document_revision_and_chunk_ids(self) -> None:
        citation = CitationBuilder.build("document-1", "revision-1", "chunk-3", 3, 12, 42, "Guide", "a" * 64, "Revit", "2026")
        self.assertEqual(citation.citation_id, "document-1:revision-1:chunk-3")
        self.assertEqual(citation.start_offset, 12)

if __name__ == "__main__": unittest.main()
