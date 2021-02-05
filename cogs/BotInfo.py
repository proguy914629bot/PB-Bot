import discord
import datetime
from discord.ext import commands
import humanize
import psutil
import sys
import inspect
from jishaku import Jishaku


class BotInfo(commands.Cog, name="Bot Info"):
    """
    Commands that display information about the bot.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.rtt_cooldown = commands.CooldownMapping.from_cooldown(1, 30, type=commands.BucketType.channel)

    @commands.command(aliases=["up"])
    async def uptime(self, ctx):
        """
        Displays how long the bot has been online for since last restart.
        """
        uptime = datetime.datetime.now() - ctx.bot.start_time
        await ctx.send(f"Bot has been online for **`{humanize.precisedelta(uptime)}`**.")

    @commands.command(usage="[-rtt|--round-trip-time]")
    async def ping(self, ctx, *flags):
        """
        Displays the websocket latency, api response time and the database response time.

        **Flags:**
        `-rtt|--round-trip-time` - If this flag is provided, round-trip time will also be displayed.
        """
        decimal_places = 5

        embed = discord.Embed(title="Pong!", colour=ctx.bot.embed_colour)
        embed.add_field(name="Websocket Latency",
                        value=f"```py\n{ctx.bot.latency * 1000:.{decimal_places}f}ms```")
        embed.add_field(name="API Response Time",
                        value=f"```py\n{(first_ping := await ctx.bot.api_ping(ctx)) * 1000:.{decimal_places}f}ms```")
        embed.add_field(name="Database Ping (postgresql)",
                        value=f"```py\n{await ctx.bot.postgresql_ping() * 1000:.{decimal_places}f}ms```")
        embed.add_field(name="Database Ping (redis)",
                        value=f"```py\n{await ctx.bot.redis_ping() * 1000:.{decimal_places}f}ms```")

        if "-rtt" in flags or "--round-trip-time" in flags:
            # cooldown check
            bucket = self.rtt_cooldown.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            if retry_after:
                raise commands.CommandOnCooldown(bucket, retry_after)

            rtts = [first_ping] + [await ctx.bot.api_ping(ctx) for _ in range(4)]  # makes 5 api requests instead of 6
            rtt_str = "\n".join(f"Reading {number}: {ms * 1000:{decimal_places}f}ms" for number, ms in enumerate(rtts, start=1))
            embed.insert_field_at(2, name="\u200b", value="\u200b")
            embed.add_field(name="\u200b", value="\u200b")
            embed.add_field(name="Round-Trip Time", value=f"```py\n{rtt_str}```")

        await ctx.send(embed=embed)

    @commands.command()
    async def botinfo(self, ctx):
        """
        Displays information about the bot.
        """
        embed = discord.Embed(title="Bot Info", colour=ctx.bot.embed_colour)
        embed.set_thumbnail(url=ctx.bot.user.avatar_url)
        v = sys.version_info
        embed.add_field(
            name="General",
            value=
            f"• Running discord.py version **{discord.__version__}** on python **{v.major}.{v.minor}.{v.micro}**\n"
            f"• This bot is not sharded and can see **{len(ctx.bot.guilds)}** servers and **{len(ctx.bot.users)}** users\n"
            f"• **{len(ctx.bot.cogs)}** cogs loaded and **{len(list(ctx.bot.walk_commands()))}** commands loaded\n"
            f"• **Websocket Latency:** `{ctx.bot.latency * 1000:.2f}ms`\n"
            f"• **API Response Time:** `{await ctx.bot.api_ping(ctx) * 1000:.2f}ms`\n"
            f"• **Database Ping (postgresql):** `{await ctx.bot.postgresql_ping() * 1000:.2f}ms`\n"
            f"• **Database Ping (redis):** `{await ctx.bot.redis_ping() * 1000:.2f}ms`\n"
            f"• **Uptime since last restart:** {humanize.precisedelta(datetime.datetime.now() - ctx.bot.start_time)}")
        p = psutil.Process()
        m = p.memory_full_info()
        embed.add_field(
            name="System",
            value=
            f"• `{p.cpu_percent()}%` cpu\n"
            f"• `{humanize.naturalsize(m.rss)}` physical memory\n"
            f"• `{humanize.naturalsize(m.vms)}` virtual memory\n"
            f"• running on PID `{p.pid}` with `{p.num_threads()}` thread(s)",
            inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx):
        """
        Shows the prefix or prefixes for the current server.
        """
        if not ctx.guild:
            return await ctx.send("My prefix is always `pb` in direct messages. You can also mention me.")
        prefixes = (await ctx.cache())["prefixes"] or ["pb"]
        if len(prefixes) == 1:
            return await ctx.send(f"My prefix for this server is `{prefixes[0]}`.")
        await ctx.send(f"My prefixes for this server are `{ctx.bot.utils.humanize_list(prefixes)}`.")

    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @prefix.command(name="add")
    async def add_(self, ctx, *, prefix: str):
        """
        Add a prefix to the prefix list for the current server. The `manage server` permission is required to use this command.

        `prefix` - The prefix to add.
        """
        if len(prefix) > 100:
            return await ctx.send("Sorry, that prefix is too long (>100 characters).")

        prefixes = (await ctx.cache())["prefixes"]

        if prefix in prefixes:
            return await ctx.send(f"`{prefix}` is already a prefix for this server.")
        if len(prefixes) > 50:
            return await ctx.send("This server already has 50 prefixes.")

        await ctx.bot.cache.add_prefix(ctx.guild.id, prefix)
        await ctx.send(f"Added `{prefix}` to the list of server prefixes.")

    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @prefix.command()
    async def remove(self, ctx, *, prefix: str):
        """
        Remove a prefix from the prefix list for the current server. The `manage server` permission is required to use this command.

        `prefix` - The prefix to remove.
        """
        if len(prefix) > 100:
            return await ctx.send("Sorry, that prefix is too long (>100 characters).")

        prefixes = (await ctx.cache())["prefixes"]

        if not prefixes:
            return await ctx.send("This server doesn't have any custom prefixes.")
        if prefix not in prefixes:
            return await ctx.send(f"Couldn't find `{prefix}` in the list of prefixes for this server.")

        await ctx.bot.cache.remove_prefix(ctx.guild.id, prefix)
        await ctx.send(f"Removed `{prefix}` from the list of server prefixes.")

    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @prefix.command()
    async def clear(self, ctx):
        """
        Clears the current server's prefix list. The `manage server` permission is required to use this command.
        """
        confirm = await ctx.bot.utils.Confirm("Are you sure that you want to clear the prefix list for this server?").prompt(ctx)
        if confirm:
            await ctx.bot.cache.clear_prefixes(ctx.guild.id)
            await ctx.send("Cleared the list of server prefixes.")

    @commands.command()
    async def invite(self, ctx):
        """
        Displays my invite link.
        """
        embed = discord.Embed(title="Invite me to your server!", url=ctx.bot.invite_url, colour=ctx.bot.embed_colour)
        await ctx.send(embed=embed)

    @commands.command(aliases=["src"])
    async def source(self, ctx, *, command: str = None):
        """
        View my source code for a specific command.

        `command` - The command to view the source code of (Optional).
        """
        if not command:
            embed = discord.Embed(title="Here is my source code.",
                                  description="Don't forget the license! (A star would also be appreciated ^^)",
                                  url=ctx.bot.github_url, colour=ctx.bot.embed_colour)
            return await ctx.send(embed=embed)

        command = ctx.bot.help_command if command.lower() == "help" else ctx.bot.get_command(command)
        if not command:
            return await ctx.send("Couldn't find command.")
        if isinstance(command.cog, Jishaku):
            return await ctx.send("<https://github.com/Gorialis/jishaku>")

        if isinstance(command, commands.HelpCommand):
            lines, starting_line_num = inspect.getsourcelines(type(command))
            filepath = f"{command.__module__.replace('.', '/')}.py"
        else:
            lines, starting_line_num = inspect.getsourcelines(command.callback.__code__)
            filepath = f"{command.callback.__module__.replace('.', '/')}.py"

        ending_line_num = starting_line_num + len(lines) - 1
        command = "help" if isinstance(command, commands.HelpCommand) else command
        embed = discord.Embed(
            title=f"Here is my source code for the `{command}` command.",
            description="Don't forget the license! (A star would also be appreciated ^^)",
            url=f"https://github.com/PB4162/PB-Bot/blob/master/{filepath}#L{starting_line_num}-L{ending_line_num}",
            colour=ctx.bot.embed_colour)
        await ctx.send(embed=embed)

    @commands.command()
    async def stats(self, ctx):
        """
        Displays the command usage stats.
        """
        top5commands_today = ctx.bot.cache.command_stats["top_commands_today"].most_common(5)
        top5commands_overall = ctx.bot.cache.command_stats["top_commands_overall"].most_common(5)
        top5users_today = [(f"<@!{user_id}>", counter)
                           for user_id, counter in ctx.bot.cache.command_stats["top_users_today"].most_common(5)]
        top5users_overall = [(f"<@!{user_id}>", counter)
                             for user_id, counter in ctx.bot.cache.command_stats["top_users_overall"].most_common(5)]

        embed = discord.Embed(title="Command Stats", colour=ctx.bot.embed_colour)
        embed.add_field(name="Top 5 Commands Today",
                        value=ctx.bot.utils.top5(top5commands_today) or "No commands have been used today.")
        embed.add_field(name="Top 5 Users Today",
                        value=ctx.bot.utils.top5(top5users_today) or "No one has used any commands today.")
        embed.add_field(name="\u200b", value="\u200b")
        embed.add_field(name="Top 5 Commands Overall",
                        value=ctx.bot.utils.top5(top5commands_overall) or "No commands have been used.")
        embed.add_field(name="Top 5 Users Overall",
                        value=ctx.bot.utils.top5(top5users_overall) or "No one has used any commands.")
        embed.add_field(name="\u200b", value="\u200b")

        await ctx.send(embed=embed)

    @commands.command()
    async def support(self, ctx):
        """
        Displays my support server's invite link.
        """
        embed = discord.Embed(title=f"Support Server Invite", url=ctx.bot.support_server_invite, colour=ctx.bot.embed_colour)
        await ctx.send(embed=embed)

    @commands.command()
    async def vote(self, ctx):
        """
        Displays my vote link.
        """
        embed = discord.Embed(title="Top.gg Page", description="Remember to leave an honest review. :)",
                              url=ctx.bot.top_gg_url, colour=ctx.bot.embed_colour)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(BotInfo())
