import os
from datetime import datetime, date, time

import discord
from discord.ext import tasks
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CATEGORY_ID = int(os.getenv("CATEGORY_ID"))
PROJECT_START = date.fromisoformat(os.getenv("PROJECT_START"))

# Change this to the streamer's actual Australian timezone if needed.
TIMEZONE = ZoneInfo("Australia/Sydney")

intents = discord.Intents.default()
client = discord.Client(intents=intents)


async def update_category_name():
    category = client.get_channel(CATEGORY_ID)

    if category is None:
        print("Category not found.")
        return

    today = datetime.now(TIMEZONE).date()
    day_number = (today - PROJECT_START).days + 1

    # Prevent weird values before the project start date
    day_number = max(day_number, 1)

    new_name = f"» 24 CHOPIN ETUDES • DAY {day_number:03d}"

    if category.name != new_name:
        await category.edit(name=new_name)
        print(f"Updated category to: {new_name}")
    else:
        print(f"Category already correct: {new_name}")


# Runs every day at midnight in the streamer's timezone
@tasks.loop(time=time(hour=0, minute=0, tzinfo=TIMEZONE))
async def daily_update():
    await update_category_name()


@daily_update.before_loop
async def before_daily_update():
    await client.wait_until_ready()


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    # Update immediately whenever the bot starts
    await update_category_name()

    if not daily_update.is_running():
        daily_update.start()


client.run(TOKEN)