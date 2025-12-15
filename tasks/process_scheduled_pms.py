import asyncio
import discord
from discord.ext import tasks, commands
import logging
from utils import prc_api


@tasks.loop(seconds=10)
async def process_scheduled_pms(bot):
    try:
        logging.info("Processing scheduled PMs.")
        while not bot.scheduled_pm_queue.empty():
            pm_data = await bot.scheduled_pm_queue.get()
            guild_id, usernames, message = pm_data
            logging.info("Not empty, grabbed last queue of scheduled PMs.")
            try:
                status_code, response_json = await bot.prc_api.run_command(
                    guild_id, f":pm {usernames} {message}"
                )

                if status_code == 429:
                    # Rate limited; put it back and try again after retry_after.
                    retry_after = float(response_json.get("retry_after", 5))
                    logging.info(
                        "429 for scheduled PM; re-queuing with delay %.1fs | guild=%s"
                        % (retry_after, guild_id)
                    )
                    await asyncio.sleep(retry_after)
                    await bot.scheduled_pm_queue.put(pm_data)
                    break  # exit loop to respect rate limit

                if status_code != 200:
                    logging.warning(
                        "Scheduled PM failed | guild=%s status=%s response=%s",
                        guild_id,
                        status_code,
                        response_json,
                    )
                    # drop instead of tight loop; do not requeue to avoid spam

            except prc_api.ResponseFailure as e:
                if e.status_code == 429:
                    logging.info(
                        "429 exception for scheduled PM, putting back into queue."
                    )
                    await bot.scheduled_pm_queue.put(pm_data)
                    break
            except Exception as e:
                logging.error(f"Error sending scheduled PM for guild {guild_id}: {e}")
    except Exception as e:
        logging.error(f"Error in process_scheduled_pms: {e}")
