import discord
from discord.ext import commands
import aiohttp
import logging


class Bloxlink:
    def __init__(self, bot: commands.Bot, key: str):
        self.api_key = key
        self.session = aiohttp.ClientSession()
        bot.external_http_sessions.append(self.session)
        self.bot = bot

    async def _send_request(self, method, url, params=None, body=None):
        async with self.session.request(
            method, url, params=params, headers={"Authorization": self.api_key}
        ) as resp:
            return (resp, await resp.json())

    async def find_roblox(self, user_id: int, guild_id: int):
        doc = await self.bot.oauth2_users.db.find_one({"discord_id": user_id})
        if doc:
            return {"robloxID": str(doc["roblox_id"])}

        # Use Server API only (requires Bloxlink bot in server)
        url = f"https://api.blox.link/v4/public/guilds/{guild_id}/discord-to-roblox/{user_id}"

        masked_key = "<empty>"
        if self.api_key:
            if len(self.api_key) <= 8:
                masked_key = "<set>"
            else:
                masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}"

        logging.debug("[Bloxlink] Fetching %s (auth=%s)", url, masked_key)

        response, resp_json = await self._send_request("GET", url)

        if response.status != 200:
            logging.warning(
                "[Bloxlink] Non-200 response (%s) for guild=%s user=%s error=%s",
                response.status,
                guild_id,
                user_id,
                resp_json.get("error"),
            )
        else:
            logging.debug(
                "[Bloxlink] 200 OK for guild=%s user=%s resolved=%s",
                guild_id,
                user_id,
                bool(resp_json.get("robloxID")),
            )
        
        # API returns {"robloxID": "...", "resolved": {}} on success
        # or {"error": "..."} on failure
        if response.status != 200 or resp_json.get("error") or not resp_json.get("robloxID"):
            return {}
        
        return resp_json

    async def get_roblox_info(self, user_id: int):
        if not user_id:
            return {}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://users.roblox.com/v1/users/{}".format(user_id)
            ) as resp:
                return await resp.json()
