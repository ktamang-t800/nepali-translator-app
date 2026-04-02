from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass
class ExtractedPage:
    page_number: int
    text: str


@dataclass
class ExtractedDocument:
    source_file_name: str
    source_file_path: str
    file_type: str
    total_pages: int
    pages: List[ExtractedPage]

    def to_dict(self) -> Dict:
        return {
            "source_file_name": self.source_file_name,
            "source_file_path": self.source_file_path,
            "file_type": self.file_type,
            "total_pages": self.total_pages,
            "pages": [asdict(page) for page in self.pages],
        }