import discord
from discord.ext import commands

from menus import YesNoMenu, AccountLinkingMenu
from utils.constants import BLANK_COLOR, GREEN_COLOR
import asyncio
import time


class OAuth2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="link",
        description="Link your Roblox account with ERM using Bloxlink.",
        extras={"ephemeral": True},
    )
    async def link_roblox(self, ctx: commands.Context):
        # Check if user already has an OAuth2 link
        existing_oauth = await self.bot.oauth2_users.db.find_one(
            {"discord_id": ctx.author.id}
        )
        
        if existing_oauth:
            user = await self.bot.roblox.get_user(existing_oauth["roblox_id"])
            await ctx.send(
                embed=discord.Embed(
                    title="Already Linked",
                    description=f"You are already linked to `{user.name}`. This command uses Bloxlink verification. Open a ticket if this needs to be changed.",
                    color=BLANK_COLOR,
                )
            )
            return

        # Fetch from Bloxlink API using Server API
        bloxlink_data = await self.bot.bloxlink.find_roblox(ctx.author.id, ctx.guild.id)
        
        # Debug logging
        print(f"[DEBUG] Bloxlink response for {ctx.author.id}: {bloxlink_data}")
        
        if not bloxlink_data or not bloxlink_data.get("robloxID"):
            await ctx.send(
                embed=discord.Embed(
                    title="Not Linked",
                    description=f"You are not linked with Bloxlink. Please verify your account at https://blox.link and try again.\n\nDebug: {bloxlink_data}",
                    color=BLANK_COLOR,
                )
            )
            return

        roblox_id = bloxlink_data["robloxID"]
        
        try:
            # robloxID is returned as string, convert to int for storage
            user = await self.bot.roblox.get_user(int(roblox_id))
            
            # Store in oauth2_users collection for compatibility
            await self.bot.oauth2_users.db.update_one(
                {"discord_id": ctx.author.id},
                {
                    "$set": {
                        "discord_id": ctx.author.id,
                        "roblox_id": int(roblox_id),
                        "last_updated": time.time(),
                    }
                },
                upsert=True,
            )
            
            await ctx.send(
                embed=discord.Embed(
                    title=f"{self.bot.emoji_controller.get_emoji('success')} Linked",
                    description=f"Your Roblox account `{user.name}` has been successfully linked via Bloxlink.",
                    color=GREEN_COLOR,
                )
            )
        except Exception as e:
            await ctx.send(
                embed=discord.Embed(
                    title="Error",
                    description=f"Failed to link your account: {e}",
                    color=BLANK_COLOR,
                )
            )


async def setup(bot):
    await bot.add_cog(OAuth2(bot))
