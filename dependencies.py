import discord
from discord.ext import commands, tasks
import datetime
import aiohttp
import wavelink
import os
import re
import asyncio
from config import config
import logging
import asyncpg
import utils
from collections import Counter
import json


logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='.\logs\discord.log', encoding='utf-8', mode='w')
logger.addHandler(handler)


async def get_prefix(bot, message):
    if not message.guild:
        prefixes = ['pb']
    else:
        try:
            prefixes = bot.prefixes[message.guild.id]
        except KeyError:
            await bot.pool.execute("INSERT INTO prefixes VALUES ($1)", message.guild.id)
            prefixes = bot.prefixes[message.guild.id] = ['pb']
    for prefix in prefixes:
        match = re.match(f"^({prefix}\s*).*", message.content, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    # fallback
    return commands.when_mentioned(bot, message)


class PB_Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=get_prefix,
            case_insensitive=True,
            intents=discord.Intents.all(),
            owner_id=config["owner_id"],
            description="An easy to use, multipurpose discord bot written in Python by PB#4162."
        )
        self.start_time = datetime.datetime.now()
        self.session = aiohttp.ClientSession()
        self.wavelink = wavelink.Client(bot=self)
        self.coglist = [f"cogs.{item[:-3]}" for item in os.listdir("cogs") if item != "__pycache__"] + ["jishaku"]
        self.pool = asyncio.get_event_loop().run_until_complete(asyncpg.create_pool(**config["database"]))
        self.controllers = {}
        self.utils = utils
        self.command_list = []
        self.embed_colour = 0x01ad98
        self.prefixes = {}  # {guildId: [pb, PB, Pb]}
        self.github_url = "https://github.com/PB4162/PB-Bot"
        self.invite_url = discord.utils.oauth_url("719907834120110182", permissions=discord.Permissions(104189127))
        self.command_usage = Counter()
        self.emoji_dict = {
            "red_line": "<:red_line:793233362298601472>",
            "white_line": "<:white_line:793235072437846116>",
            "blue_button": "<:blue_button:776982842957234186>",
            "voice_channel": "<:voice_channel:787460989409951757>",
            "text_channel": "<:text_channel:787461133963231263>",
            "red_tick": "<:red_tick:795827295541133372>",
            "green_tick": "<:green_tick:795827014300598272>",
            "online": "<:online:787461591968645130>",
            "offline": "<:offline:787461784318902303>",
            "idle": "<:idle:787461645038256149>",
            "dnd": "<:dnd:787461694455808070>",
        }

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=cls or CustomContext)

    async def on_message_edit(self, before, after):
        if after.author.id == bot.owner_id:
            await self.process_commands(after)

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        if re.fullmatch(f"^(<@!?{self.user.id}>)\s*", message.content):
            ctx = await self.get_context(message)
            return await ctx.invoke(self.get_command("prefix"))
        await self.process_commands(message)

    async def on_guild_join(self, guild):
        await self.pool.execute("INSERT INTO prefixes VALUES ($1)", guild.id)
        self.prefixes[guild.id] = ['pb']

    async def on_guild_leave(self, guild):
        await self.pool.execute("DELETE FROM prefixes WHERE guild_id = $1", guild.id)
        self.prefixes.pop(guild.id)

    def beta_command(self):
        async def predicate(ctx):
            if ctx.author.id == self.owner_id:
                return True
            await ctx.send(f"The `{ctx.command}` command is currently in beta. Only my owner can use it.")
            return
        return commands.check(predicate)

    def whitelisted_servers(self):
        async def predicate(ctx):
            """todo:"""

        return commands.check(predicate)

    @tasks.loop(minutes=30)
    async def presence_update(self):
        await self.wait_until_ready()
        await self.change_presence(
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(self.guilds)} servers and {len(self.users)} users"))

    @tasks.loop(hours=24)
    async def clear_command_usage(self):
        if os.path.exists("temp.json"):
            os.remove("temp.json")
        self.command_usage.clear()

    @clear_command_usage.before_loop
    async def clear_command_usage_before(self):
        if os.path.exists("temp.json"):
            with open("temp.json") as f:
                self.command_usage.update(json.load(f))
            os.remove("temp.json")

        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        midnight = datetime.datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day)
        dt = midnight - datetime.datetime.now()
        await discord.utils.sleep_until(dt)

    async def on_command(self, ctx):
        self.command_usage.update({ctx.command.qualified_name: 1})

    async def close(self):
        with open("temp.json", "w") as f:
            json.dump(dict(self.command_usage), f)
        await super().close()

    async def load_prefixes(self):
        for entry in await self.pool.fetch("SELECT * FROM prefixes"):
            self.prefixes[entry["guild_id"]] = entry["guild_prefixes"]

    # async def dump_prefixes(self):
    #     for guild_id, prefixes in self.prefixes.items():
    #         await self.pool.execute("UPDATE prefixes SET guild_prefixes = $1 WHERE guild_id = $2", prefixes, guild_id)
    #
    # @tasks.loop(minutes=10)
    # async def dump_prefixes_task(self):
    #     await self.dump_prefixes()

    async def schemas(self):
        with open("schemas.sql") as f:
            await self.pool.execute(f.read())

    def run(self, *args, **kwargs):
        for cog in self.coglist:
            self.load_extension(cog)

        self.loop.run_until_complete(self.schemas())
        self.loop.run_until_complete(self.load_prefixes())

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

        self.clear_command_usage.start()
        self.presence_update.start()
        super().run(*args, **kwargs)

    async def mystbin(self, data):
        async with self.session.post('https://mystb.in/documents', data=data) as r:
            return f"https://mystb.in/{(await r.json())['key']}"

    async def hastebin(self, data):
        async with self.session.post('https://hastebin.com/documents', data=data) as r:
            return f"https://hastebin.com/{(await r.json())['key']}"


bot = PB_Bot()


class CustomContext(commands.Context):
    """
    Custom context class.
    """
    @property
    def clean_prefix(self):
        return re.sub(f"<@!?{bot.user.id}>", "@PB Bot", self.prefix)

    async def send(self, *args, **kwargs):
        try:
            return await self.reply(*args, **kwargs, mention_author=False)
        except discord.HTTPException:
            return await super().send(*args, **kwargs)
