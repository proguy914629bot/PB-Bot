import discord
from discord.ext import commands
import traceback
from fuzzywuzzy import process
import re

from dependencies import bot


@bot.event
async def on_command_error(ctx, error, *, from_local=False):
    """
    Global error handler.
    ---------------------
    If an error is raised in a command, it goes to the local error handler.
    If the local error handler handles the error correctly, the global error handler does nothing.
    If the local error handler does not handle the error correctly, then it goes to the global error handler.
    """
    if hasattr(ctx.command, 'on_error') and not from_local:
        return
    error = getattr(error, 'original', error)

    if isinstance(error, commands.CommandNotFound):
        failed_command = re.match(f"^({ctx.prefix})\s*(.*)", ctx.message.content, flags=re.IGNORECASE).group(2)
        match, ratio = process.extractOne(failed_command, bot.command_list)
        if ratio < 75:
            return
        await ctx.send(f"Command '{failed_command}' is not found. Did you mean `{match}`?")
    elif isinstance(error, discord.ext.commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown, please try again in `{error.retry_after:.2f}` seconds.")
    elif isinstance(error, commands.NotOwner):
        await ctx.send(f"Only my owner can use the `{ctx.command}` command.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command can only be used in a server.")
    elif isinstance(error, commands.MissingPermissions):
        perms = bot.utils.humanize_list(error.missing_perms).replace('_', ' ').replace('guild', 'server')
        await ctx.send(f"You need the `{perms}` permission(s) to use this command.")
    elif isinstance(error, discord.HTTPException):
        embed = discord.Embed(title=f"An HTTP Exception Occurred", description= \
            f"HTTP error code `{error.status}`\n"
            f"Discord error code `{error.code}` ([understanding what the error codes mean](https://discord.com/developers/docs/topics/opcodes-and-status-codes#http-http-response-codes))",
            colour=bot.embed_colour)
        embed.add_field(name="Error Message", value=error.text or 'No error message.')
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title=f"`{str(error.param).split(':')[0]}` is a required argument that is missing.", description=f"Confused? Run the command `{ctx.clean_prefix}help {ctx.command}`.", colour=bot.embed_colour)
        await ctx.send(embed=embed)
    elif isinstance(error, commands.BadArgument):
        # argument = list(ctx.command.clean_params)[len(ctx.args[2:] if ctx.command.cog else ctx.args[1:])]
        pattern = re.compile(r'(Converting to "(.+)" failed for parameter "(.+)"\.)|((.+) "(.+)" not found.)')
        # groups:
        # 0: entire match
        # 1: entire match for error message 1
        # 2: type for error message 1
        # 3: argument name for error message 1

        # 4: entire match for error message 2
        # 5: "type" for error message 2
        # 6: argument value for error message 2
        match = pattern.match(str(error))
        if match.group(1):  # error message 1
            err_message = f"Value passed to `{match.group(3)}` is not a `{match.group(2) if match.group(2) != 'int' else 'number'}`."
        else:  # error message 2
            err_message = f"{match.group(5)} `{match.group(6)}` not found."
        embed = discord.Embed(title=err_message, description=f"Confused? Run the command `{ctx.clean_prefix}help {ctx.command}`.", colour=bot.embed_colour)
        await ctx.send(embed=embed)
    elif isinstance(error, commands.TooManyArguments):
        await ctx.send(error)
    elif isinstance(error, commands.MaxConcurrencyReached):
        await ctx.send(f"The `{ctx.command}` command is limited to `{error.number}` {'use' if error.number == 1 else 'uses'} per `{error.per.name}` at a time.")
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        # unexpected errors get handled here.
        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
        tb = ''.join(tb_lines)

        if not ctx.guild:
            guild_id = None
        else:
            guild_id = ctx.guild.id
        await bot.pool.execute("""INSERT INTO errors (
        traceback, author, author_id, channel, channel_id, guild, guild_id, message, message_id, command
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
        tb, str(ctx.author), str(ctx.author.id), str(ctx.channel), str(ctx.channel.id), str(ctx.guild), str(guild_id),
                               ctx.message.content, str(ctx.message.id), ctx.command.name) # h
        embed = discord.Embed(
            title=f"An unexpected error occurred in command `{ctx.command}`",
            description=f"```diff\n-{error.__class__.__name__}: {error}```",
            timestamp=ctx.message.created_at,
            colour=0xff0000)
        embed.set_footer(text="Error report sent to owner")
        await ctx.send(embed=embed)


def setup(_):
    pass
