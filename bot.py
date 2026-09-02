import os
from datetime import datetime, date

import discord
from zoneinfo import ZoneInfo

TOKEN = os.environ["DISCORD_TOKEN"]
CATEGORY_ID = int(os.environ["CATEGORY_ID"])
PROJECT_START = date.fromisoformat(os.environ["PROJECT_START"])

TIMEZONE = ZoneInfo("Australia/Sydney")

intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    category = client.get_channel(CATEGORY_ID)

    if category is None:
        print("Category not found.")
        await client.close()
        return

    today = datetime.now(TIMEZONE).date()
    day_number = (today - PROJECT_START).days + 1
    day_number = max(day_number, 1)

    new_name = f"» 24 CHOPIN ETUDES • DAY {day_number:03d}"

    if category.name != new_name:
        await category.edit(name=new_name)
        print(f"Updated category to: {new_name}")
    else:
        print(f"Category already correct: {new_name}")

    await client.close()


client.run(TOKEN)