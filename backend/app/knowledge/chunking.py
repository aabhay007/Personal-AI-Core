"""Text chunking engine with configurable window and overlap."""
from typing import List, Dict, Any


class TextChunker:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def chunk_document_sections(
        self,
        sections: List[Dict[str, Any]],
        filename: str
    ) -> List[Dict[str, Any]]:
        """Split document sections into overlapping chunks preserving page metadata."""
        chunks = []
        global_index = 0

        for section in sections:
            text = section.get("content", "")
            page_num = section.get("page_number", 1)

            section_chunks = self._split_text(text)
            for c_text in section_chunks:
                if not c_text.strip():
                    continue
                chunks.append({
                    "content": c_text.strip(),
                    "chunk_index": global_index,
                    "metadata": {
                        "filename": filename,
                        "page_number": page_num,
                        "character_count": len(c_text.strip())
                    }
                })
                global_index += 1

        return chunks

    def _split_text(self, text: str) -> List[str]:
        """Recursively split text based on natural separators within size constraints."""
        if len(text) <= self.chunk_size:
            return [text]

        # Find best separator
        separator = ""
        for sep in self.separators:
            if sep in text:
                separator = sep
                break

        splits = text.split(separator) if separator else list(text)

        chunks = []
        current_chunk = []
        current_len = 0

        for piece in splits:
            piece_len = len(piece) + (len(separator) if current_chunk else 0)
            if current_len + piece_len > self.chunk_size and current_chunk:
                merged = separator.join(current_chunk)
                chunks.append(merged)

                # Keep overlap pieces from the end of current_chunk
                overlap_pieces = []
                overlap_len = 0
                for p in reversed(current_chunk):
                    if overlap_len + len(p) <= self.chunk_overlap:
                        overlap_pieces.insert(0, p)
                        overlap_len += len(p)
                    else:
                        break
                current_chunk = overlap_pieces
                current_len = overlap_len

            current_chunk.append(piece)
            current_len += len(piece)

        if current_chunk:
            chunks.append(separator.join(current_chunk))

        return chunks
