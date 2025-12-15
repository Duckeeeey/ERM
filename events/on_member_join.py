import logging

import discord
from discord.ext import commands
from discord.http import Route


class OnMemberJoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: discord.Member):
        
        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}!",
            description=(
                "Welcome to Minnesota State Roleplay.\n\n"
                + (f"Want to stop recieving invite messages to our Discord Server in ERLC? Run </link:1450244427628019770> in this DM or in MSRP to link your account.\n\n")
                + "Issues? Reach out to our staff team via a support ticket."
            ),
            color=0x2F3136,
        )

        try:
            await member.send(embed=embed)
            logging.info("Sent welcome DM to %s", member.id)
        except Exception:
            logging.info("Could not DM welcome to %s (closed DMs)", member.id)


async def setup(bot):
    await bot.add_cog(OnMemberJoin(bot))
