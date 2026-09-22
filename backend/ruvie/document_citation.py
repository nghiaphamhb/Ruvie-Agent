from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Citation:
    citation_id: str
    document_id: str
    revision_id: str
    chunk_id: str
    ordinal: int
    start_offset: int
    end_offset: int
    title: str
    source_hash: str
    software: str
    software_version: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class CitationBuilder:
    @staticmethod
    def build(document_id: str, revision_id: str, chunk_id: str, ordinal: int, start_offset: int, end_offset: int, title: str, source_hash: str, software: str, software_version: str) -> Citation:
        return Citation(f"{document_id}:{revision_id}:{chunk_id}", document_id, revision_id, chunk_id, ordinal, start_offset, end_offset, title, source_hash, software, software_version)
