import os

# The API spawns an ingest worker unless this is set. Tests enqueue jobs themselves.
os.environ["AETHER_INGEST_WORKER"] = "0"
os.environ["AETHER_DATABASE_URL"] = ""
