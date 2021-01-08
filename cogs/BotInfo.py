import discord
import datetime
from discord.ext import commands
import humanize
import psutil
import time
import sys
import inspect

from dependencies import bot


class BotInfo(commands.Cog, name="Bot Info"):
    """
    Commands that display information about the bot.
    """
    @commands.command(
        aliases=["up"]
    )
    async def uptime(self, ctx):
        """
        Displays how long the bot has been online for since last reboot.
        """
        uptime = datetime.datetime.now() - bot.start_time
        await ctx.send(f"Bot has been online for **`{humanize.precisedelta(uptime)}`**.")

    @commands.command()
    async def ping(self, ctx, accuracy: int = 2):
        """
        Displays the websocket latency and the api response time.

        `accuracy` - The amount of decimal places to show. Defaults to 2.
        """
        start = time.perf_counter()
        await ctx.trigger_typing()
        api_response_time = time.perf_counter() - start
        try:
            await ctx.send(embed=discord.Embed(title="Pong!", description=f"**Websocket Latency:** `{bot.latency * 1000:.{accuracy}f}ms`\n**API response time:** `{api_response_time * 1000:.{accuracy}f}ms`", colour=bot.embed_colour))
        except (discord.errors.HTTPException, ValueError):
            await ctx.send(f"Too many decimal places ({accuracy}).")

    @commands.command()
    async def botinfo(self, ctx):
        """
        Displays information about the bot.
        """
        start = time.perf_counter()
        await ctx.trigger_typing()
        api_response_time = time.perf_counter() - start
        embed = discord.Embed(title="Bot Info", colour=bot.embed_colour)
        embed.set_thumbnail(url=bot.user.avatar_url)
        embed.add_field(name="General",
                    value= \
                    f"• Running discord.py version **{discord.__version__}** on python **{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}**\n"
                    f"• This bot is not sharded and can see **{len(bot.guilds)}** servers and **{len(bot.users)}** users\n"
                    f"• **{len(bot.cogs)}** cogs loaded and **{len(list(bot.walk_commands()))}** commands loaded\n"
                    f"• **Websocket latency:** `{bot.latency * 1000:.2f}ms`\n"
                    f"• **API response time:** `{api_response_time * 1000:.2f}ms`\n"
                    f"• **Uptime since last boot:** {humanize.precisedelta(datetime.datetime.now() - bot.start_time)}"
                    )
        p = psutil.Process()
        m = p.memory_full_info()
        embed.add_field(name="System",
                        value= \
                        f"• `{p.cpu_percent()}%` cpu\n"
                        f"• `{humanize.naturalsize(m.rss)}` physical memory\n"
                        f"• `{humanize.naturalsize(m.vms)}` virtual memory\n"
                        f"• running on PID `{p.pid}` with `{p.num_threads()}` thread(s)"
                        , inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx):
        """
        Shows the prefix or prefixes for the current server.
        """
        if not ctx.guild:
            return await ctx.send("My prefix is always `pb` in direct messages. You can also mention me.")
        prefixes = bot.prefixes[ctx.guild.id]
        if len(prefixes) == 1:
            return await ctx.send(f"My prefix for this server is `{prefixes[0]}`.")
        await ctx.send(f"My prefixes for this server are `{bot.utils.humanize_list(prefixes)}`.")

    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @prefix.command(name="add")
    async def add_(self, ctx, *, prefix):
        """
        Add a prefix to the prefix list for the current server. The `manage server` permission is required to use this command.

        `prefix` - The prefix to add.
        """
        if len(prefix) > 100:
            return await ctx.send("Sorry, that prefix is too long.")
        if prefix in bot.prefixes[ctx.guild.id]:
            return await ctx.send(f"`{prefix}` is already a prefix for this server.")
        if len(bot.prefixes[ctx.guild.id]) > 50:
            return await ctx.send("This server already has 50 prefixes.")
        bot.prefixes[ctx.guild.id].append(prefix)
        await bot.pool.execute("UPDATE prefixes SET guild_prefixes = array_append(guild_prefixes, $1) WHERE guild_id = $2", prefix, ctx.guild.id)
        await ctx.send(f"Added `{prefix}` to the list of server prefixes.")

    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @prefix.command()
    async def remove(self, ctx, *, prefix):
        """
        Remove a prefix from the prefix list for the current server. The `manage server` permission is required to use this command.

        `prefix` - The prefix to remove.
        """
        if len(prefix) > 100:
            return await ctx.send("Sorry, that prefix is too long.")
        if prefix not in bot.prefixes[ctx.guild.id]:
            return await ctx.send(f"Couldn't find `{prefix}` in the list of prefixes for this server.")
        if len(bot.prefixes[ctx.guild.id]) == 1:
            return await ctx.send("Sorry, you can't remove this server's only prefix.")
        bot.prefixes[ctx.guild.id].remove(prefix)
        await bot.pool.execute("UPDATE prefixes SET guild_prefixes = array_remove(guild_prefixes, $1) WHERE guild_id = $2", prefix, ctx.guild.id)
        await ctx.send(f"Removed `{prefix}` from the list of server prefixes.")

    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @prefix.command()
    async def clear(self, ctx):
        """
        Clears the current server's prefix list. The `manage server` permission is required to use this command.
        """
        confirm = await bot.utils.Confirm("Are you sure that you want to clear the prefix list for the current server?").prompt(ctx)
        if confirm:
            bot.prefixes[ctx.guild.id] = ["pb"]
            await bot.pool.execute("UPDATE prefixes SET guild_prefixes = '{pb}' WHERE guild_id = $1", ctx.guild.id)
            await ctx.send("Cleared the list of server prefixes.")

    @commands.command()
    async def invite(self, ctx):
        """
        Displays my invite link.
        """
        embed = discord.Embed(title="Invite me to your server!", url=bot.invite_url, colour=bot.embed_colour)
        await ctx.send(embed=embed)

    @commands.command()
    async def source(self, ctx, *, command=None):
        """
        View my source code for a specific command.

        `command` - The command to view the source code of (Optional).
        """
        if not command:
            embed = discord.Embed(title="Here is my source code.",
                                  description="Don't forget the license! (A star would also be appreciated ^^)", url=bot.github_url, colour=bot.embed_colour)
            return await ctx.send(embed=embed)
        command = bot.get_command(command)
        if not command:
            return await ctx.send("Couldn't find command.")
        lines, starting_line_num = inspect.getsourcelines(command.callback.__code__)
        ending_line_num = starting_line_num + len(lines) - 1
        filepath = f"{command.callback.__module__.replace('.', '/')}.py"
        embed = discord.Embed(title=f"Here is my source code for the `{command}` command.",
                              description="Don't forget the license! (A star would also be appreciated ^^)",
                              url=f"https://github.com/PB4162/PB-Bot/blob/master/{filepath}#L{starting_line_num}-L{ending_line_num}",
                              colour=bot.embed_colour)
        await ctx.send(embed=embed)


def setup(_):
    bot.add_cog(BotInfo())
