import sys
import time

print("Starting imports...")
sys.stdout.flush()

t0 = time.time()
import fastapi
print(f"  fastapi: {time.time()-t0:.1f}s")
sys.stdout.flush()

t0 = time.time()
import uvicorn
print(f"  uvicorn: {time.time()-t0:.1f}s")
sys.stdout.flush()

t0 = time.time()
import faster_whisper
print(f"  faster_whisper: {time.time()-t0:.1f}s")
sys.stdout.flush()

t0 = time.time()
import sounddevice
print(f"  sounddevice: {time.time()-t0:.1f}s")
sys.stdout.flush()

print("ALL IMPORTS OK")
