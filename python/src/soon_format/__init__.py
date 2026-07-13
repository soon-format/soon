"""SOON (Shape-Oriented Object Notation).

Lossless, token-efficient encoding of nested JSON for LLM prompts.

>>> from soon_format import encode, decode
>>> doc = encode({"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]})
>>> decode(doc) == {"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]}
True
"""

from .decode import decode
from .encode import encode
from .errors import SoonDecodeError, SoonEncodeError, SoonError
from .stats import stats

__version__ = "0.1.0"
__all__ = [
    "SoonDecodeError",
    "SoonEncodeError",
    "SoonError",
    "__version__",
    "decode",
    "encode",
    "stats",
]
