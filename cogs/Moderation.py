import discord
from discord.ext import commands

from dependencies import bot


class Moderation(commands.Cog):
    """
    Moderation commands.
    """
    def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    @commands.has_guild_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """
        Kicks a member from the server.

        `member` - The member to kick.
        `reason` - The reason why the member was kicked. Defaults to "No reason provided.".
        """
        reason = reason or "No reason provided."
        await member.send(f"You have been kicked from **`{ctx.guild}`** by `{ctx.author}`.\n**Reason:** {reason}")
        await member.kick(reason=f"kick done by {ctx.author}; reason: {reason}")
        await ctx.send("👌")

    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """
        Bans a member from the server.

        `member` - The member to ban.
        `reason` - The reason why the member was banned. Defaults to "No reason provided.".
        """
        reason = reason or "No reason provided."
        await member.send(f"You have been banned from **`{ctx.guild}`** by `{ctx.author}`.\n**Reason:** {reason}")
        await member.ban(reason=f"ban done by {ctx.author}; reason: {reason}")
        await ctx.send("👌")


def setup(_):
    bot.add_cog(Moderation())
