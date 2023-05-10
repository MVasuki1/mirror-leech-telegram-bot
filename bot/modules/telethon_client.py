from bot import TELETHON_SESSIONS, TELETHON_SESSION_ACQUIRE

async def get_telethon_client():
    c, l = (None, None)
    async with TELETHON_SESSION_ACQUIRE:
        for client, lock in TELETHON_SESSIONS:
            if not lock.locked():
                c, l = (client, lock)
                break
    return c, l
