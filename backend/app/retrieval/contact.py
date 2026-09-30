import re
from typing import Any


NOT_MENTIONED = "Not mentioned in ad"
PHONE_PATTERN = re.compile(r"(?:\+94|0)?(?:\s|-|\.)?(?:7\d)(?:\s|-|\.)?\d{3}(?:\s|-|\.)?\d{4}")


def extract_contact_number(*values: Any) -> str:
    text = " ".join("" if value is None else str(value) for value in values)
    match = PHONE_PATTERN.search(text)
    if not match:
        return NOT_MENTIONED
    return re.sub(r"\s+", " ", match.group(0)).strip()
