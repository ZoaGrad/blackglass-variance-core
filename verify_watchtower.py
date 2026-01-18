
from src.tools.watch_variance import watch_variance
import os
from dotenv import load_dotenv

load_dotenv()

print("Starting Direct Watchtower Verification...")
summary = watch_variance(
    iterations=10,
    interval_sec=5,
    duration_sec=30,
    variance_threshold=0.15,
    queue_threshold=50
)
print("Watchtower Finished:")
print(summary)
