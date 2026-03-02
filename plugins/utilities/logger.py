from pyrogram.enums import ParseMode

LOG_GROUP_ID = -1001234567890 

async def send_match_log(client, action_title, match, extra_text=""):
    """Function to send logs to the bot's private group"""
    if not LOG_GROUP_ID:
        return

    game_id = match.get("game_id", "Unknown")
    chat_id = match.get("chat_id", "Unknown")
    host_name = match.get("host_name", "Unknown")
    
    text = (
        f"📝 **{action_title}**\n"
        f"──┈┄┄╌╌╌╌┄┄┈──\n"
        f"🆔 **Match ID:** `{game_id}`\n"
        f"👤 **Host:** {host_name}\n"
        f"💬 **Group ID:** `{chat_id}`\n\n"
        f"{extra_text}"
    )
    
    try:
        await client.send_message(
            chat_id=LOG_GROUP_ID, 
            text=text, 
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"❌ Error while sending log: {e}")
      
