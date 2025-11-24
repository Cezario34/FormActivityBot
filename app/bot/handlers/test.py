import asyncio
from psycopg import AsyncConnection

async def main():
    conninfo = "postgresql://ddenil2:foR2m2bo1t1@localhost:5432/formemployee"
    try:
        conn = await AsyncConnection.connect(conninfo=conninfo)
        print("OK connected")
        await conn.close()
    except Exception as e:
        print("FAILED:", e)
