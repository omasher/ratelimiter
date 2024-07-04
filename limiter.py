import asyncio
from collections import deque
import functools
import time

class AsyncRateLimiter:
    def __init__(self, max_calls, period=1.0, callback=None):
        if period <= 0:
            raise ValueError('Period must be > 0')
        if max_calls <= 0:
            raise ValueError('Number of calls must be > 0')

        self.calls = deque()
        self.period = period
        self.max_calls = max_calls
        self.callback = callback
        self._lock = asyncio.Lock()

    def __call__(self, f):
        @functools.wraps(f)
        async def wrapped(*args, **kwargs):
            async with self:
                return await f(*args, **kwargs)
        return wrapped
    
    async def __aenter__(self):
        async with self._lock:
            if len(self.calls) >= self.max_calls:
                until = time.time() + self.period - self._timespan
                if self.callback:
                    await self.callback(until)
                sleeptime = until - time.time()
                if sleeptime > 0:
                    await asyncio.sleep(sleeptime)
            self.calls.append(time.time())
            while self._timespan >= self.period:
                self.calls.popleft()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            self.calls.append(time.time())
        while self._timespan >= self.period:
            self.calls.popleft()

    @property
    def _timespan(self):
        if len(self.calls) == 0:
            return 0
        return self.calls[-1] - self.calls[0]


# Example of usage
async def example_callback(until):
    print(f"Rate limit exceeded. Please wait until {until}.")

rate_limiter = AsyncRateLimiter(max_calls=3, period=3, callback=example_callback)

@rate_limiter
async def limited():
    print("Function executed")

async def main():
    tasks = [limited() for _ in range(10)]
    await asyncio.gather(*tasks)

asyncio.run(main())
