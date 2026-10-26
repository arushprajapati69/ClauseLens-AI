"""Configuration constants and calibration thresholds for ClauseLens AI."""

# Models & Ollama Endpoint
GEN_MODEL = "llama3.1:8b"
LOW_RAM_GEN_MODEL = "llama3.2:3b"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_HOST = "http://localhost:11434"
LLM_TIMEOUT = 120.0  # seconds
MAX_PREDICT_TOKENS = 650

# Ingestion & Chunking
CHUNK_MAX_CHARS = 900
MAX_FILE_MB = 10
MAX_PAGES = 60

# Query & Verification Bounds
MAX_QUESTION_CHARS = 1000
MIN_QUOTE_CHARS = 15
MAX_QUOTE_CHARS = 400

# Retrieval & Conflict Matching
TOP_K = 6
# Calibrated on synthetic eval benchmark:
# MIN_RETRIEVAL_SCORE: Below 0.38, retrieved chunks are off-topic boilerplate.
# Above 0.38 preserves relevant clause retrieval while cleanly rejecting irrelevant queries.
MIN_RETRIEVAL_SCORE = 0.38

# PAIR_SIM_THRESHOLD: Threshold to consider two cross-document chunks on the "same topic"
# for potential conflict evaluation.
PAIR_SIM_THRESHOLD = 0.50

MAX_CONFLICT_PAIRS = 3

# Localization / Currency
CURRENCY = "INR"
CURRENCY_SYMBOL = "₹"
