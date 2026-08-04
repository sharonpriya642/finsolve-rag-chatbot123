import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # None when running against local Docker Qdrant
COLLECTION_NAME = "finsolve_company_data"

# One folder in data/ per department -- these become the "department" tag
# stored in every chunk's metadata inside Qdrant.
DEPARTMENTS = ["finance", "hr", "marketing", "engineering", "general"]

# Which departments each role is allowed to search.
# "general" is included everywhere since it's company-wide info (handbook etc).
ROLE_ACCESS = {
    "finance": ["finance", "general"],
    "hr": ["hr", "general"],
    "marketing": ["marketing", "general"],
    "engineering": ["engineering", "general"],
    "c-level": ["finance", "hr", "marketing", "engineering", "general"],
}
