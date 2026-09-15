# =======================================================
# Add-on: permanent storage for /gconnect (gplay) links
# Place this file at: VILLAIN_MUSIC/utils/gconnect_db.py
# =======================================================
#
# Requires MONGO_DB_URI to be set in config.py, e.g.:
#     MONGO_DB_URI = os.environ.get("MONGO_DB_URI", "")
# and in your .env / environment variables:
#     MONGO_DB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
#
# Requires the `motor` package (pulls in pymongo + dnspython):
#     pip install motor dnspython

import os

import config
from motor.motor_asyncio import AsyncIOMotorClient

_mongo_client = None
_db = None


def _get_db():
    global _mongo_client, _db
    if _db is None:
        mongo_uri = getattr(config, "MONGO_DB_URI", None) or os.environ.get(
            "MONGO_DB_URI"
        )
        if not mongo_uri:
            raise RuntimeError(
                "MONGO_DB_URI is not set. Add it to config.py / your environment "
                "to use /gconnect and /gplay."
            )
        _mongo_client = AsyncIOMotorClient(mongo_uri)
        _db = _mongo_client["PurviGConnect"]
    return _db


def _collection():
    return _get_db()["gconnections"]


async def save_gconnection(first_chat_id: int, second_chat_id: int):
    """Permanently link first_chat_id (command chat) -> second_chat_id (VC/playback chat)."""
    await _collection().update_one(
        {"_id": first_chat_id},
        {"$set": {"_id": first_chat_id, "play_chat": second_chat_id}},
        upsert=True,
    )


async def get_gconnection(first_chat_id: int):
    """Return the connected playback chat_id for a command chat, or None."""
    doc = await _collection().find_one({"_id": first_chat_id})
    return doc.get("play_chat") if doc else None


async def remove_gconnection(first_chat_id: int) -> bool:
    """Remove a saved connection. Returns True if something was deleted."""
    result = await _collection().delete_one({"_id": first_chat_id})
    return result.deleted_count > 0


async def resolve_playback_chat(chat_id: int) -> int:
    """
    Use this in EVERY playback-control command (skip, pause, resume,
    stop/end, forceplay, seek, volume, mute, unmute, queue, etc.).

    If `chat_id` (the chat the command was sent in) is a connected
    1st/command chat, returns the linked 2nd/VC chat_id instead.
    Otherwise returns chat_id unchanged, so normal groups keep
    working exactly as before.
    """
    linked = await get_gconnection(chat_id)
    return linked if linked else chat_id
