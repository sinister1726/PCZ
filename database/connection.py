import asyncio
import asyncpg
from config import Config


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self, retries: int = 10, delay: float = 3.0):
        for attempt in range(1, retries + 1):
            try:
                print(f"🗄️ Connecting to PostgreSQL... (attempt {attempt}/{retries})")
                self.pool = await asyncpg.create_pool(
                    dsn=Config.DATABASE_URL,
                    min_size=5,
                    max_size=85,
                    command_timeout=30,
                )
                print("✅ Database Pool Created (PRO MODE: 85 Max Connections).")
                return
            except Exception as e:
                print(f"⚠️ DB connect attempt {attempt} failed: {e}")
                if attempt < retries:
                    wait = delay * attempt
                    print(f"🔄 Retrying in {wait:.0f}s…")
                    await asyncio.sleep(wait)
        print("❌ Could not connect to the database after all retries. Some features will be unavailable.")

    async def ensure_pool(self):
        if not self.pool:
            await self.connect(retries=5, delay=2.0)

    def acquire(self):
        if not self.pool:
            raise RuntimeError("Database pool is not available yet. Please wait a moment and try again.")
        return self.pool.acquire()

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None


db = Database()
