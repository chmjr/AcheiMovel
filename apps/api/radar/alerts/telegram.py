import httpx


async def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    if not bot_token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
