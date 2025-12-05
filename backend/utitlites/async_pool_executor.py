import asyncio
import concurrent.futures

executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

async def run_in_threadpool(func, *args, **kwargs):
    """Run synchronous DB code in a worker thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))