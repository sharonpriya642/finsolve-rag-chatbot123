"""
create_index.py

One-time fix: creates a payload index on "metadata.department" in Qdrant
Cloud. RBAC filtering (rbac/filters.py) filters search results by this
field, and some Qdrant configurations require an explicit index to exist
before you can filter on a field at all.

Run once from the project root:
    python create_index.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType

from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

print(f"Creating payload index on 'metadata.department' in collection '{COLLECTION_NAME}' ...")
client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="metadata.department",
    field_schema=PayloadSchemaType.KEYWORD,
)
print("Done. RBAC department filtering should now work.")
