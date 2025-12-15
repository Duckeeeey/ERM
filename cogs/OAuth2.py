import discord
from discord.ext import commands
from discord import app_commands
import logging

from menus import YesNoMenu, AccountLinkingMenu
from utils.constants import BLANK_COLOR, GREEN_COLOR
import asyncio
import time


class OAuth2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="link",
        description="Link your Roblox account with MSRP Mo using Bloxlink.",
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

    # Register a global-only slash command for /link that uses the same logic
    async def _global_link(interaction: discord.Interaction):
        bot = interaction.client
        # Check if user already has an OAuth2 link
        existing_oauth = await bot.oauth2_users.db.find_one({"discord_id": interaction.user.id})
        if existing_oauth:
            user = await bot.roblox.get_user(existing_oauth["roblox_id"])
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Already Linked",
                    description=f"You are already linked to `{user.name}`. This command uses Bloxlink verification. Open a ticket if this needs to be changed.",
                    color=BLANK_COLOR,
                ),
                ephemeral=True,
            )
            return

        # If invoked in DMs, we can only rely on existing DB links; Bloxlink server lookup requires a guild
        if interaction.guild is None:
            bloxlink_data = await bot.oauth2_users.db.find_one({"discord_id": interaction.user.id})
            if bloxlink_data:
                bloxlink_data = {"robloxID": str(bloxlink_data.get("roblox_id"))}
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Not Linked",
                        description=(
                            "You are not linked with Bloxlink. Linking via Bloxlink requires the Bloxlink bot in a server. "
                            "Please run this command in a server where Bloxlink is present, or link via the web at https://blox.link."
                        ),
                        color=BLANK_COLOR,
                    ),
                    ephemeral=True,
                )
                return
        else:
            bloxlink_data = await bot.bloxlink.find_roblox(interaction.user.id, interaction.guild.id)

        if not bloxlink_data or not bloxlink_data.get("robloxID"):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Not Linked",
                    description="You are not linked with Bloxlink. Please verify your account at https://blox.link and try again.",
                    color=BLANK_COLOR,
                ),
                ephemeral=True,
            )
            return

        roblox_id = bloxlink_data["robloxID"]
        try:
            user = await bot.roblox.get_user(int(roblox_id))
            await bot.oauth2_users.db.update_one(
                {"discord_id": interaction.user.id},
                {
                    "$set": {
                        "discord_id": interaction.user.id,
                        "roblox_id": int(roblox_id),
                        "last_updated": time.time(),
                    }
                },
                upsert=True,
            )

            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{bot.emoji_controller.get_emoji('success')} Linked",
                    description=f"Your Roblox account `{user.name}` has been successfully linked via Bloxlink.",
                    color=GREEN_COLOR,
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Error",
                    description=f"Failed to link your account: {e}",
                    color=BLANK_COLOR,
                ),
                ephemeral=True,
            )

    cmd = app_commands.command(name="link", description="Link your Roblox account with ERM using Bloxlink.")(_global_link)

    async def _register_global():
        try:
            await bot.wait_until_ready()

            # Add to local tree so runtime can resolve it, but avoid global syncing of entire tree
            if not any(c.name == "link" and c.parent is None for c in bot.tree.walk_commands()):
                bot.tree.add_command(cmd)

            # Ensure a single global command exists via REST without syncing the whole tree
            try:
                from discord.http import Route

                app_id = bot.application_id or getattr(bot.user, "id", None)
                if not app_id:
                    # Try to fetch application info
                    try:
                        app_info = await bot.application_info()
                        app_id = app_info.id
                    except Exception:
                        logging.exception("Could not determine application id for global command registration")
                        return

                # Fetch existing global commands
                get_route = Route("GET", "/applications/{application_id}/commands", application_id=app_id)
                existing = await bot.http.request(get_route)
                # existing is a list of dicts
                # Remove any existing global commands except 'link'
                to_delete = [c for c in existing if c.get("name") != "link"]
                for c in to_delete:
                    try:
                        del_route = Route("DELETE", "/applications/{application_id}/commands/{command_id}", application_id=app_id, command_id=c.get("id"))
                        await bot.http.request(del_route)
                        logging.info("Deleted global command: %s", c.get("name"))
                    except Exception:
                        logging.exception("Failed to delete global command %s", c.get("name"))

                if not any(c.get("name") == "link" for c in existing):
                    payload = {"name": "link", "description": "Link your Roblox account with ERM using Bloxlink.", "dm_permission": True}
                    post_route = Route("POST", "/applications/{application_id}/commands", application_id=app_id)
                    await bot.http.request(post_route, json=payload)
                    logging.info("Created global /link command via REST")
                else:
                    logging.info("Global /link command already exists")
            except Exception:
                logging.exception("Failed to ensure global /link command via REST")

        except Exception as e:
            logging.exception("Failed to register global /link command task: %s", e)

    try:
        bot.loop.create_task(_register_global())
    except Exception:
        # fallback: start in background without blocking
        try:
            bot.loop.call_soon_threadsafe(lambda: bot.loop.create_task(_register_global()))
        except Exception:
            logging.exception("Failed to schedule global /link registration task")
