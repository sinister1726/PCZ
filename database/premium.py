from database.connection import db
from datetime import datetime, timedelta

PLANS = {
    "silver": {
        "name":     "🥈 Silver",
        "price":    30,
        "duration": 28,
        "features": ["spam_free", "ball_timeout"],
    },
    "gold": {
        "name":     "🥇 Gold",
        "price":    80,
        "duration": 28,
        "features": ["spam_free", "ball_timeout", "disabled_numbers", "edge_rule"],
    },
}

PLAN_ORDER = ["silver", "gold"]

_cache: dict = {}


async def grant_premium(chat_id: int, plan: str, granted_by: int, days: int = 28) -> bool:
    if plan not in PLANS:
        return False
    await db.ensure_pool()
    expires_at = datetime.utcnow() + timedelta(days=days)
    await db.db["premium_groups"].update_one(
        {"chat_id": chat_id},
        {"$set": {
            "chat_id":    chat_id,
            "plan":       plan,
            "granted_by": granted_by,
            "granted_at": datetime.utcnow(),
            "expires_at": expires_at,
            "active":     True,
        }},
        upsert=True,
    )
    _cache[chat_id] = {
        "plan":       plan,
        "active":     True,
        "expires_at": expires_at,
    }
    return True


async def revoke_premium(chat_id: int) -> bool:
    await db.ensure_pool()
    res = await db.db["premium_groups"].update_one(
        {"chat_id": chat_id},
        {"$set": {"active": False}},
    )
    _cache.pop(chat_id, None)
    return res.modified_count > 0


async def get_premium(chat_id: int):
    cached = _cache.get(chat_id)
    if cached:
        if not cached.get("active"):
            return None
        exp = cached.get("expires_at")
        if exp and datetime.utcnow() > exp:
            await _expire(chat_id)
            return None
        return cached

    await db.ensure_pool()
    doc = await db.db["premium_groups"].find_one({"chat_id": chat_id, "active": True})
    if not doc:
        _cache[chat_id] = {"active": False}
        return None

    exp = doc.get("expires_at")
    if exp and datetime.utcnow() > exp:
        await _expire(chat_id)
        return None

    entry = {"plan": doc["plan"], "active": True, "expires_at": exp}
    _cache[chat_id] = entry
    return entry


async def _expire(chat_id: int):
    """Mark a group's premium as expired in DB and cache."""
    try:
        await db.db["premium_groups"].update_one(
            {"chat_id": chat_id},
            {"$set": {"active": False}},
        )
    except Exception:
        pass
    _cache[chat_id] = {"active": False}


async def check_and_expire_all():
    """Background task — call periodically to auto-expire subscriptions."""
    try:
        await db.ensure_pool()
        now = datetime.utcnow()
        cursor = db.db["premium_groups"].find({"active": True, "expires_at": {"$lt": now}})
        async for doc in cursor:
            cid = doc["chat_id"]
            await db.db["premium_groups"].update_one(
                {"_id": doc["_id"]},
                {"$set": {"active": False}},
            )
            _cache.pop(cid, None)
            print(f"⏰ Premium expired for group {cid}")
    except Exception as e:
        print(f"Expiry check error: {e}")


async def is_premium(chat_id: int) -> bool:
    return (await get_premium(chat_id)) is not None


async def get_plan_features(chat_id: int) -> list:
    p = await get_premium(chat_id)
    if not p:
        return []
    return PLANS.get(p["plan"], {}).get("features", [])


async def can_use_feature(chat_id: int, feature: str) -> bool:
    return feature in (await get_plan_features(chat_id))


def plan_unlocked(premium: dict, req_plan: str) -> bool:
    if not premium or not premium.get("active"):
        return False
    try:
        return PLAN_ORDER.index(premium["plan"]) >= PLAN_ORDER.index(req_plan)
    except ValueError:
        return False
