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
import aioredis
from copy import deepcopy

EMPTY_GUILD_CACHE = {"prefixes": []}
EMPTY_TODO = []


async def get_prefix(bot, message: discord.Message):
    """
    Get prefix function.
    """
    if not message.guild:
        prefixes = ["pb"]
    else:
        prefixes = (await bot.cache.get_guild_info(message.guild.id))["prefixes"]
        if not prefixes:  # couldn't find it or no prefixes
            prefixes = ["pb"]
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

        self.pool = asyncio.get_event_loop().run_until_complete(asyncpg.create_pool(**config["postgresql"]))
        self.redis = asyncio.get_event_loop().run_until_complete(aioredis.create_redis_pool(config["redis"]))

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
        await self.cache.delete_guild_info(guild.id)

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

    async def postgresql_ping(self):
        with self.utils.StopWatch() as sw:
            await self.pool.fetch("SELECT 1")
        return sw.elapsed

    async def redis_ping(self):
        with self.utils.StopWatch() as sw:
            await self.redis.ping()
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
    async def clear_cmd_stats(self):
        await self.cache.clear_cmd_stats()

    @clear_cmd_stats.before_loop
    async def clear_command_stats_before(self):
        # wait until midnight to start the loop
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        midnight = datetime.datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day)
        dt = midnight - datetime.datetime.now()
        await asyncio.sleep(dt.total_seconds())

    @tasks.loop(minutes=5)
    async def dump_cmd_stats(self):
        await self.cache.dump_cmd_stats()

    async def on_command(self, ctx):
        self.cache.command_stats["top_commands_today"].update({ctx.command.qualified_name: 1})
        self.cache.command_stats["top_commands_overall"].update({ctx.command.qualified_name: 1})

        self.cache.command_stats["top_users_today"].update({str(ctx.author.id): 1})
        self.cache.command_stats["top_users_overall"].update({str(ctx.author.id): 1})

    async def close(self):
        await self.cache.dump_all()
        await super().close()

    async def schemas(self):
        with open("schemas.sql") as f:
            await self.pool.execute(f.read())

    def run(self, *args, **kwargs):
        for cog in self.coglist:
            self.load_extension(cog)

        self.loop.run_until_complete(self.schemas())
        self.loop.run_until_complete(self.cache.load_all())

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

        self.presence_update.start()
        self.dump_cmd_stats.start()
        self.clear_cmd_stats.start()
        super().run(*args, **kwargs)

    async def mystbin(self, data):
        async with self.session.post("https://mystb.in/documents", data=data) as r:
            return f"https://mystb.in/{(await r.json())['key']}"

    async def hastebin(self, data):
        async with self.session.post("https://hastebin.com/documents", data=data) as r:
            return f"https://hastebin.com/{(await r.json())['key']}"


class Cache:
    def __init__(self, bot: PB_Bot):
        self.bot = bot

        self.guild_cache = {}
        self.command_stats = {"top_commands_today": Counter(), "top_commands_overall": Counter(),
                              "top_users_today": Counter(), "top_users_overall": Counter()}
        self.todos = {}

    async def load_all(self):
        await self.load_guild_info()
        await self.load_cmd_stats()
        await self.load_todos()

    async def dump_all(self):
        await self.dump_guild_info()
        await self.dump_cmd_stats()
        await self.dump_todos()

    # guild info

    async def load_guild_info(self):
        data = await self.bot.pool.fetch("SELECT * FROM guild_info")
        for entry in data:
            self.guild_cache[entry["guild_id"]] = {k: v for k, v in list(entry.items())[1:]}  # skip the guild_id

    async def dump_guild_info(self):
        items = deepcopy(self.guild_cache).items()
        for guild_id, data in items:
            await self.bot.pool.execute("UPDATE guild_info SET prefixes = $1 WHERE guild_id = $2", data["prefixes"], guild_id)
            # idk how to make this dynamic

    async def create_guild_info(self, guild_id):
        await self.bot.pool.execute("INSERT INTO guild_info VALUES ($1)", guild_id)
        self.guild_cache[guild_id] = deepcopy(EMPTY_GUILD_CACHE)
        return self.guild_cache[guild_id]

    async def delete_guild_info(self, guild_id):
        await self.bot.pool.execute("DELETE FROM guild_info WHERE guild_id = $1", guild_id)
        self.guild_cache.pop(guild_id, None)

    async def get_guild_info(self, guild_id):
        info = self.guild_cache.get(guild_id, None)
        if info is None:
            return await self.create_guild_info(guild_id)
        return info

    async def cleanup_guild_info(self, guild_id):
        cache = await self.get_guild_info(guild_id)
        if cache == EMPTY_GUILD_CACHE:
            await self.delete_guild_info(guild_id)

    async def add_prefix(self, guild_id, prefix):
        await self.bot.pool.execute("UPDATE guild_info SET prefixes = array_append(prefixes, $1) WHERE guild_id = $2", prefix, guild_id)
        (await self.get_guild_info(guild_id))["prefixes"].append(prefix)

    async def remove_prefix(self, guild_id, prefix):
        await self.bot.pool.execute("UPDATE guild_info SET prefixes = array_remove(prefixes, $1) WHERE guild_id = $2", prefix, guild_id)
        (await self.get_guild_info(guild_id))["prefixes"].remove(prefix)

        await self.cleanup_guild_info(guild_id)

    async def clear_prefixes(self, guild_id):
        await self.bot.pool.execute("UPDATE guild_info SET prefixes = '{}' WHERE guild_id = $1", guild_id)
        (await self.get_guild_info(guild_id))["prefixes"].clear()

        await self.cleanup_guild_info(guild_id)

    # command stats

    async def load_cmd_stats(self):
        top_cmds_today = await self.bot.redis.hgetall("top_commands_today", encoding="utf-8")
        top_users_today = await self.bot.redis.hgetall("top_users_today", encoding="utf-8")
        top_cmds_overall = await self.bot.redis.hgetall("top_commands_overall", encoding="utf-8")
        top_users_overall = await self.bot.redis.hgetall("top_users_overall", encoding="utf-8")
        self.command_stats["top_commands_today"].update({k: int(v) for k, v in top_cmds_today.items()})
        self.command_stats["top_users_today"].update({k: int(v) for k, v in top_users_today.items()})
        self.command_stats["top_commands_overall"].update({k: int(v) for k, v in top_cmds_overall.items()})
        self.command_stats["top_users_overall"].update({k: int(v) for k, v in top_users_overall.items()})

    async def dump_cmd_stats(self):
        top_cmds_today = dict(self.command_stats["top_commands_today"])
        top_users_today = dict(self.command_stats["top_users_today"])
        top_cmds_overall = dict(self.command_stats["top_commands_overall"])
        top_users_overall = dict(self.command_stats["top_users_overall"])
        if top_cmds_today:  # will error if it's empty
            await self.bot.redis.hmset_dict("top_commands_today", top_cmds_today)
        if top_users_today:
            await self.bot.redis.hmset_dict("top_users_today", top_users_today)
        if top_cmds_overall:
            await self.bot.redis.hmset_dict("top_commands_overall", top_cmds_overall)
        if top_users_overall:
            await self.bot.redis.hmset_dict("top_users_overall", top_users_overall)

    async def clear_cmd_stats(self):
        # dump
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        cmds = json.dumps(dict(self.command_stats["top_commands_today"]))
        users = json.dumps(dict(self.command_stats["top_users_today"]))
        await self.bot.pool.execute("INSERT INTO command_stats VALUES ($1, $2, $3)", yesterday, cmds, users)

        # clear
        self.command_stats["top_commands_today"].clear()
        self.command_stats["top_users_today"].clear()

    # todos

    async def load_todos(self):
        data = await self.bot.pool.fetch("SELECT * FROM todos")
        for entry in data:
            self.todos[entry["user_id"]] = entry["tasks"]

    async def dump_todos(self):
        items = deepcopy(self.todos).items()
        for user_id, tasks_ in items:
            await self.bot.pool.execute("UPDATE todos SET tasks = $1 WHERE user_id = $2", tasks_, user_id)

    async def create_todo(self, user_id):
        await self.bot.pool.execute("INSERT INTO todos VALUES ($1)", user_id)
        self.todos[user_id] = deepcopy(EMPTY_TODO)
        return self.todos[user_id]

    async def delete_todo(self, user_id):
        await self.bot.pool.execute("DELETE FROM todos WHERE user_id = $1", user_id)
        self.todos.pop(user_id)

    async def get_todo(self, user_id):
        todo = self.todos.get(user_id, None)
        if todo is None:
            return await self.create_todo(user_id)
        return todo

    async def cleanup_todo(self, user_id):
        todo = await self.get_todo(user_id)
        if todo == EMPTY_TODO:
            await self.delete_todo(user_id)

    async def add_todo(self, user_id, task):
        await self.bot.pool.execute("UPDATE todos SET tasks = array_append(tasks, $1) WHERE user_id = $2", task, user_id)
        (await self.get_todo(user_id)).append(task)

    async def remove_todo(self, user_id, task):
        await self.bot.pool.execute("UPDATE todos SET tasks = array_remove(tasks, $1) WHERE user_id = $2", task, user_id)
        (await self.get_todo(user_id)).remove(task)

        await self.cleanup_todo(user_id)

    async def clear_todos(self, user_id):
        await self.bot.pool.execute("UPDATE todos SET tasks = '{}' WHERE user_id = $1", user_id)
        (await self.get_todo(user_id)).clear()

        await self.cleanup_todo(user_id)


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

    async def send(self, content=None, **kwargs):
        if "reply" in kwargs and not kwargs.pop("reply"):
            return await super().send(content, **kwargs)
        try:
            return await self.reply(content, **kwargs, mention_author=False)
        except discord.HTTPException:
            return await super().send(content, **kwargs)

    async def quote(self, content=None, **kwargs):
        if content is None:
            content = ""
        mention_author = kwargs.get("mention_author", "")
        if mention_author:
            mention_author = f"{self.author.mention} "
        quote = "\n".join(f"> {string}" for string in self.message.content.split("\n"))
        quote_msg = f"{quote}\n{mention_author}{content}"
        return await super().send(quote_msg, **kwargs)

    async def cache(self):
        return await self.bot.cache.get_guild_info(self.guild.id)


class StopSpammingMe(commands.CheckFailure):
    pass
