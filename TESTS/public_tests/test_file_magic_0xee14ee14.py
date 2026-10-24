"""Public Black-Box: File Magic Header & Page Size - No core exposed"""
import os, struct
MAGIC_HEADER = b"\xee\x14\xee\x14"
EXPECTED_PAGE_SIZE = 8192
def verify_db_header(file_path: str) -> bool:
    with open(file_path, "rb") as f:
        header = f.read(4)
        page_size = struct.unpack(">I", f.read(4))[0]
        return header == MAGIC_HEADER and page_size == EXPECTED_PAGE_SIZE
