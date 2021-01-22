import discord
from discord.ext import commands, tasks
import datetime
import aiohttp
import wavelink
import os
import re
import asyncio
from config import config
import asyncpg
import utils
from collections import Counter
import json


async def get_prefix(bot, message: discord.Message):
    """
    get_prefix function.
    """
    if not message.guild:
        prefixes = ['pb']
    else:
        prefixes = bot.cache.prefixes.get(message.guild.id, ['pb'])
    for prefix in prefixes:
        match = re.match(f"^({prefix}\s*).*", message.content, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    # fallback
    return commands.when_mentioned(bot, message)


class PB_Bot(commands.Bot):
    """
    Subclassed bot.
    """
    def __init__(self):
        super().__init__(
            command_prefix=get_prefix,
            case_insensitive=True,
            intents=discord.Intents.all(),
            owner_id=config["owner_id"],
            description="An easy to use, multipurpose discord bot written in Python by PB#4162."
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()
        
        self.start_time = datetime.datetime.now()
        self.session = aiohttp.ClientSession()
        self.wavelink = wavelink.Client(bot=self)
        self.coglist = [f"cogs.{item[:-3]}" for item in os.listdir("cogs") if item != "__pycache__"] + ["jishaku"]

        self.pool = asyncio.get_event_loop().run_until_complete(asyncpg.create_pool(**config["database"]))

        self.utils = utils
        self.command_list = []
        self.embed_colour = 0x01ad98

        self.cache = Cache(self)

        self.github_url = "https://github.com/PB4162/PB-Bot"
        self.invite_url = discord.utils.oauth_url("719907834120110182", permissions=discord.Permissions(104189127))
        self.support_server_invite = "https://discord.gg/qQVDqXvmVt"
        self.top_gg_url = "https://top.gg/bot/719907834120110182"

        self._cd = commands.CooldownMapping.from_cooldown(rate=5, per=5, type=commands.BucketType.user)

        @self.check
        async def global_check(ctx):
            # check if ratelimited
            bucket = self._cd.get_bucket(ctx.message)
            retry_after = bucket.update_rate_limit()
            if retry_after:
                raise StopSpammingMe()
            return True

        self.emoji_dict = {
            "red_line": "<:red_line:799429087352717322>",
            "white_line": "<:white_line:799429050061946881>",
            "blue_button": "<:blue_button:799429556879753226>",
            "voice_channel": "<:voice_channel:799429142902603877>",
            "text_channel": "<:text_channel:799429180109750312>",
            "red_tick": "<:red_tick:799429329372971049>",
            "green_tick": "<:green_tick:799429375719899139>",
            "online": "<:online:799429451771150386>",
            "offline": "<:offline:799429511199850546>",
            "idle": "<:idle:799429473611153409>",
            "dnd": "<:dnd:799429487749103627>",
            "tickon": "<:tickon:799429228415156294>",
            "tickoff": "<:tickoff:799429264188637184>",
            "xon": "<:xon:799428912195174442>",
            "xoff": "<:xoff:799428963775807489>",
            "upvote": "<:upvote:799432692595687514>",
            "downvote": "<:downvote:799432736892911646>",
        }

    async def get_context(self, message: discord.Message, *, cls=None):
        return await super().get_context(message, cls=cls or CustomContext)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.id == self.owner_id:
            await self.process_commands(after)

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if re.fullmatch(f"^(<@!?{self.user.id}>)\s*", message.content):
            ctx = await self.get_context(message)
            return await ctx.invoke(self.get_command("prefix"))
        await self.process_commands(message)

    async def on_guild_leave(self, guild: discord.Guild):
        await self.pool.execute("DELETE FROM prefixes WHERE guild_id = $1", guild.id)
        self.cache.prefixes.pop(guild.id, None)

    def beta_command(self):
        async def predicate(ctx):
            if ctx.author.id != self.owner_id:
                await ctx.send(f"The `{ctx.command}` command is currently in beta. Only my owner can use it.")
                return False
            return True
        return commands.check(predicate)

    async def api_ping(self, ctx):
        with self.utils.StopWatch() as sw:
            await ctx.trigger_typing()
        return sw.elapsed

    async def db_ping(self):
        with self.utils.StopWatch() as sw:
            await self.pool.fetch("SELECT * FROM information_schema.tables")
        return sw.elapsed

    @tasks.loop(minutes=30)
    async def presence_update(self):
        await self.change_presence(
            status=discord.Status.idle,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers and {len(self.users)} users")
        )

    @presence_update.before_loop
    async def before_presence(self):
        await self.wait_until_ready()

    @tasks.loop(hours=24)
    async def refresh_command_usage(self):
        # dump
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        top_commands_today = str(dict(self.cache.command_stats["top_commands_today"]))
        top_users_today = str(dict(self.cache.command_stats["top_users_today"]))
        await self.pool.execute("INSERT INTO command_stats VALUES ($1, $2, $3)", yesterday, top_commands_today, top_users_today)

        # clear
        self.cache.command_stats["top_commands_today"].clear()
        self.cache.command_stats["top_users_today"].clear()

    @refresh_command_usage.before_loop
    async def refresh_command_usage_before(self):
        # wait until midnight to start the loop
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        midnight = datetime.datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day)
        dt = midnight - datetime.datetime.now()
        await asyncio.sleep(dt.total_seconds())

    async def on_command(self, ctx):
        self.cache.command_stats["top_commands_today"].update({ctx.command.qualified_name: 1})
        self.cache.command_stats["top_commands_overall"].update({ctx.command.qualified_name: 1})

        self.cache.command_stats["top_users_today"].update({ctx.author.id: 1})
        self.cache.command_stats["top_users_overall"].update({ctx.author.id: 1})

    async def close(self):
        await self.cache.dump_command_stats()  # temporarily storing them
        await super().close()

    # @tasks.loop(minutes=10)
    # async def dump_prefixes_task(self):
    #     await self.cache.dump_prefixes()

    async def schemas(self):
        with open("schemas.sql") as f:
            await self.pool.execute(f.read())

    def run(self, *args, **kwargs):
        for cog in self.coglist:
            self.load_extension(cog)

        self.loop.run_until_complete(self.schemas())
        self.loop.run_until_complete(self.cache.load_prefixes())
        self.loop.run_until_complete(self.cache.load_command_stats())

        for command in self.commands:
            self.command_list.append(str(command))
            self.command_list.extend([alias for alias in command.aliases])
            if isinstance(command, commands.Group):
                for subcommand in command.commands:
                    self.command_list.append(str(subcommand))
                    self.command_list.extend([f"{command} {subcommand_alias}" for subcommand_alias in subcommand.aliases])
                    if isinstance(subcommand, commands.Group):
                        for subcommand2 in subcommand.commands:
                            self.command_list.append(str(subcommand2))
                            self.command_list.extend([f"{subcommand} {subcommand2_alias}" for subcommand2_alias in subcommand2.aliases])
                            if isinstance(subcommand2, commands.Group):
                                for subcommand3 in subcommand2.commands:
                                    self.command_list.append(str(subcommand3))
                                    self.command_list.extend([f"{subcommand2} {subcommand3_alias}" for subcommand3_alias in subcommand3.aliases])

        self.refresh_command_usage.start()
        self.presence_update.start()
        super().run(*args, **kwargs)

    async def mystbin(self, data):
        async with self.session.post('https://mystb.in/documents', data=data) as r:
            return f"https://mystb.in/{(await r.json())['key']}"

    async def hastebin(self, data):
        async with self.session.post('https://hastebin.com/documents', data=data) as r:
            return f"https://hastebin.com/{(await r.json())['key']}"


class Cache:
    def __init__(self, bot: PB_Bot):
        self.bot = bot

        self.prefixes = {}
        self.command_stats = {"top_commands_today": Counter(), "top_commands_overall": Counter(),
                              "top_users_today": Counter(), "top_users_overall": Counter()}

    async def load_prefixes(self):
        for entry in await self.bot.pool.fetch("SELECT * FROM prefixes"):
            self.prefixes[entry["guild_id"]] = entry["guild_prefixes"]

    async def dump_prefixes(self):
        for guild_id, prefixes in self.prefixes.items():
            await self.bot.pool.execute("UPDATE prefixes SET guild_prefixes = $1 WHERE guild_id = $2", prefixes, guild_id)

    async def load_command_stats(self):
        if os.path.exists("temp.json"):
            with open("temp.json") as f:
                data = json.load(f)
                self.command_stats["top_commands_today"].update(data["top_commands_today"])
                self.command_stats["top_commands_overall"].update(data["top_commands_overall"])
                self.command_stats["top_users_today"].update(data["top_users_today"])
                self.command_stats["top_users_overall"].update(data["top_users_overall"])

    async def dump_command_stats(self):
        with open("temp.json", "w") as f:
            json.dump(self.command_stats, f)


class CustomContext(commands.Context):
    """
    Custom context class.
    """
    @property
    def clean_prefix(self):
        prefix = re.sub(f"<@!?{self.bot.user.id}>", "@PB Bot", self.prefix)
        if prefix.endswith("  "):
            prefix = f"{prefix.strip()} "
        return prefix

    async def send(self, *args, **kwargs):
        try:
            return await self.reply(*args, **kwargs, mention_author=False)
        except discord.HTTPException:
            return await super().send(*args, **kwargs)

    async def quote(self, content=None, **kwargs):
        if content is None:
            content = ""
        mention_author = kwargs.get("mention_author", "")
        if mention_author:
            mention_author = f"{self.author.mention} "
        quote = "\n".join(f"> {string}" for string in self.message.content.split("\n"))
        quote_msg = f"{quote}\n{mention_author}{content}"
        return await super().send(quote_msg, **kwargs)


class StopSpammingMe(commands.CheckFailure):
    pass
