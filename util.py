from starlette.types import Receive, Scope, Send
import random
import asyncio

# dev middleware that adds a delay before returning requests
class DelayMiddleware:
    # delays are in seconds
    def __init__(self, app, delayMin: int = 0, delayRange: int = 0):
        self.app = app
        self.delayMin = delayMin
        self.delayRange = delayRange

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = await self.app(scope, receive, send)
        await asyncDelay(self.delayMin, self.delayRange)
        return response
    
# total delay is the min plus a random range, delays are in seconds. Returns total delay
async def asyncDelay(delayMin: int, delayRange: int = 0):
    totalDelay = delayMin + (random.random() * delayRange)
    await asyncio.sleep(totalDelay)
    return totalDelay