import redis.asyncio

redis_client = redis.asyncio.Redis(host="111.230.137.152", port=6379, decode_responses=True)
