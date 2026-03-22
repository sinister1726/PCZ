import uuid
import asyncio
from database.connection import db


async def _pool():
    await db.ensure_pool()
    if not db.pool:
        raise RuntimeError("Database unavailable. Please try again in a moment.")
    return db.pool


async def is_game_active(chat_id: int) -> bool:
    try:
        async with (await _pool()).acquire() as conn:
            return await conn.fetchval(
                "SELECT 1 FROM games WHERE chat_id=$1 AND status='active'", chat_id
            ) is not None
    except Exception as e:
        print(f"[DB] is_game_active error: {e}")
        return False


async def create_game(chat_id: int, mode: str, host_id: int, title: str):
    game_id = uuid.uuid4()
    try:
        async with (await _pool()).acquire() as conn:
            await conn.execute(
                "INSERT INTO games (game_id, chat_id, title, mode, host_id, status, phase) "
                "VALUES ($1, $2, $3, $4, $5, 'active', 'setup')",
                game_id, chat_id, title, mode, host_id,
            )
    except Exception as e:
        print(f"[DB] create_game error: {e}")
    return game_id


async def end_game(chat_id: int):
    try:
        async with (await _pool()).acquire() as conn:
            await conn.execute(
                "UPDATE games SET status='ended' WHERE chat_id=$1 AND status='active'", chat_id
            )
    except Exception as e:
        print(f"[DB] end_game error: {e}")


async def get_active_game(chat_id: int):
    try:
        async with (await _pool()).acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM games WHERE chat_id=$1 AND status='active'", chat_id
            )
    except Exception as e:
        print(f"[DB] get_active_game error: {e}")
        return None


async def set_phase(chat_id: int, phase: str):
    try:
        async with (await _pool()).acquire() as conn:
            await conn.execute(
                "UPDATE games SET phase=$1 WHERE chat_id=$2 AND status='active'", phase, chat_id
            )
    except Exception as e:
        print(f"[DB] set_phase error: {e}")


async def get_phase(chat_id: int):
    try:
        async with (await _pool()).acquire() as conn:
            return await conn.fetchval(
                "SELECT phase FROM games WHERE chat_id=$1 AND status='active'", chat_id
            )
    except Exception as e:
        print(f"[DB] get_phase error: {e}")
        return None


async def user_in_other_game(user_id: int, current_chat_id: int):
    try:
        async with (await _pool()).acquire() as conn:
            return await conn.fetchrow(
                "SELECT g.chat_id, g.title FROM game_players p "
                "JOIN games g ON p.game_id = g.game_id "
                "WHERE p.user_id=$1 AND g.chat_id!=$2 AND g.status='active'",
                user_id, current_chat_id,
            )
    except Exception as e:
        print(f"[DB] user_in_other_game error: {e}")
        return None


async def get_shift_count(game_id, user_id):
    try:
        async with (await _pool()).acquire() as conn:
            return await conn.fetchval(
                "SELECT shifts FROM team_shifts WHERE game_id=$1 AND user_id=$2", game_id, user_id
            ) or 0
    except Exception as e:
        print(f"[DB] get_shift_count error: {e}")
        return 0


async def increment_shift(game_id, user_id):
    try:
        async with (await _pool()).acquire() as conn:
            await conn.execute(
                "INSERT INTO team_shifts (game_id, user_id, shifts) VALUES ($1, $2, 1) "
                "ON CONFLICT (game_id, user_id) DO UPDATE SET shifts = team_shifts.shifts + 1",
                game_id, user_id,
            )
    except Exception as e:
        print(f"[DB] increment_shift error: {e}")


async def get_team_players(game_id, team: str):
    try:
        async with (await _pool()).acquire() as conn:
            return await conn.fetch(
                "SELECT user_id, is_out, is_captain, role FROM game_players "
                "WHERE game_id=$1 AND team=$2 ORDER BY joined_at ASC",
                game_id, team,
            )
    except Exception as e:
        print(f"[DB] get_team_players error: {e}")
        return []


async def update_team_penalty(game_id: uuid.UUID, team: str, amount: int = 6):
    column = "team_a_penalty" if team == "A" else "team_b_penalty"
    try:
        async with (await _pool()).acquire() as conn:
            await conn.execute(
                f"UPDATE games SET {column} = {column} + $1 WHERE game_id = $2", amount, game_id
            )
    except Exception as e:
        print(f"[DB] update_team_penalty error: {e}")


async def increment_user_penalty_count(user_id: int):
    try:
        async with (await _pool()).acquire() as conn:
            await conn.execute(
                "INSERT INTO user_stats (user_id, penalties_received) VALUES ($1, 1) "
                "ON CONFLICT (user_id) DO UPDATE SET penalties_received = user_stats.penalties_received + 1",
                user_id,
            )
    except Exception as e:
        print(f"[DB] increment_user_penalty_count error: {e}")


async def save_match_result(conn, match, winner, motm_id):
    await conn.execute(
        "UPDATE games SET winner=$1, team_a_runs=$2, team_a_wickets=$3, "
        "team_b_runs=$4, team_b_wickets=$5, team_a_penalty=$6, team_b_penalty=$7, "
        "motm=$8, status='ended', phase='finished' WHERE game_id=$9",
        winner,
        match["teams"]["A"]["runs"],
        match["teams"]["A"]["wickets"],
        match["teams"]["B"]["runs"],
        match["teams"]["B"]["wickets"],
        match["teams"]["A"].get("penalty", 0),
        match["teams"]["B"].get("penalty", 0),
        motm_id,
        match["game_id"],
    )
