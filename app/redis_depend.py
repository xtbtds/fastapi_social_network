import aioredis

async def get_redis_pool():
    return await aioredis.create_redis_pool(('redis', 6379), encoding='utf-8')
