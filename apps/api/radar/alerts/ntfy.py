import httpx


async def send_ntfy(topic_url: str, title: str, message: str, priority: str = "default") -> None:
    """
    Publish a notification to an ntfy topic.

    topic_url examples:
      https://ntfy.sh/meu-radar-floripa   (hosted)
      http://localhost:2586/meu-topico    (self-hosted)

    priority: min | low | default | high | urgent
    """
    if not topic_url:
        return

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            topic_url,
            content=message.encode(),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": "house,chart_increasing",
            },
        )
