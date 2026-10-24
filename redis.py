import redis.asyncio as redis
import os
from dotenv import load_dotenv

load_dotenv()

    
REDIS_PORT = os.getenv("REDIS_PORT")

redis_client = redis.Redis(
    host='localhost',
    port=REDIS_PORT,
    db=int(0),
    decode_responses=True
)
# REDIS_URL = os.getenv("REDIS_URL")

# redis_client = redis.from_url(REDIS_URL, decode_responses=True)



