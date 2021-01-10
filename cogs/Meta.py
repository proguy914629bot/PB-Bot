import discord
from discord.ext import commands, menus
import asyncio
import random
import pytesseract
import cv2
import numpy as np
import re
import base64 as b64
import humanize
import datetime
import pathlib
from pyfiglet import Figlet
import typing

from dependencies import bot
from config import config

f = Figlet()
pytesseract.pytesseract.tesseract_cmd = config["tesseract_path"]


class Meta(commands.Cog):
    """
    Commands that don't belong to any specific category.
    """
    @commands.command()
    async def mystbin(self, ctx, *, text=None):
        """
        Paste text or a text file to https://mystb.in.

        `text` - The text to paste to mystbin.
        """
        data = []
        if text:
            data.append(text)
        if ctx.message.attachments:
            data.append("\n\nATTACHMENTS\n\n")
            for attachment in ctx.message.attachments:
                if attachment.height or attachment.width:
                    return await ctx.send("Only text files can be used.")
                if attachment.size > 500_000: # 500kb
                    return await ctx.send("File is too large (>500kb).")
                data.append((await attachment.read()).decode(encoding="utf-8"))
        data = "".join(item for item in data)
        embed = discord.Embed(title="Paste Successful!", description=f"[Click here to view]({await bot.mystbin(data)})", colour=bot.embed_colour, timestamp=ctx.message.created_at)
        await ctx.send(embed=embed)

    @commands.command()
    async def hastebin(self, ctx, *, text=None):
        """
        Paste text or a text file to https://hastebin.com.

        `text` - The text to paste to hastebin.
        """
        data = []
        if text:
            data.append(text)
        if ctx.message.attachments:
            data.append("\n\nATTACHMENTS\n\n")
            for attachment in ctx.message.attachments:
                if attachment.height or attachment.width:
                    return await ctx.send("Only text files can be used.")
                if attachment.size > 500_000: # 500kb
                    return await ctx.send("File is too large (>500kb).")
                data.append((await attachment.read()).decode(encoding="utf-8"))
        data = "".join(item for item in data)
        embed = discord.Embed(title="Paste Successful!", description=f"[Click here to view]({await bot.hastebin(data)})", colour=bot.embed_colour, timestamp=ctx.message.created_at)
        await ctx.send(embed=embed)

    @commands.command()
    async def xkcd(self, ctx, comic_number: int = None):
        """
        Get a specific or random comic from https://xkcd.com.

        `comic_number` - The comic number to get. Defaults to a random number.
        """
        async with ctx.typing():
            if not comic_number:
                async with bot.session.get("https://xkcd.com/info.0.json") as resp:
                    max_num = (await resp.json())["num"]
                comic_number = random.randint(1, max_num)
            async with bot.session.get(f"https://xkcd.com/{comic_number}/info.0.json") as resp:
                if resp.status in range(400, 500):
                    return await ctx.send("Couldn't find a comic with that number.")
                elif resp.status >= 500:
                    return await ctx.send("Server error.")
                data = await resp.json()
            embed = discord.Embed(title=f"{data['safe_title']} (Comic Number `{data['num']}`)", description=data['alt'],
                                  timestamp=datetime.datetime(year=int(data["year"]), month=int(data["month"]), day=int(data["day"])), colour=bot.embed_colour)
            embed.set_image(url=data['img'])
            embed.set_footer(text="Created:")
            await ctx.send(embed=embed)

    def _ocr(self, bytes):
        img = cv2.imdecode(np.fromstring(bytes, np.uint8), 1)
        return pytesseract.image_to_string(img)

    @commands.command()
    async def ocr(self, ctx):
        """
        Read the contents of an attachment using `pytesseract`.
        **NOTE:** This can be *very* inaccurate at times.
        """
        if not ctx.message.attachments:
            return await ctx.send("No attachment provided.")
        ocr_result = await bot.loop.run_in_executor(None, self._ocr, await ctx.message.attachments[0].read())
        await ctx.send(f"Text to image result for **{ctx.author}**```{ocr_result}```")

    @commands.command()
    async def ascii(self, ctx, *, text):
        """
        Convert text to ascii characters. Might look messed up on mobile.

        `text` - The text to convert to ascii.
        """
        char_list = bot.utils.split_on_num(text, 25)
        ascii_char_list = [f.renderText(char) for char in char_list]
        await menus.MenuPages(source=bot.utils.PaginatorSource(ascii_char_list, per_page=1), delete_message_after=True).start(ctx)

    # @bot.beta_command()
    # @commands.command(
    #     aliases=["pt"]
    # )
    # async def parsetoken(self, ctx, *, token):
    #     if not re.match("([a-zA-Z0-9]{24}\.[a-zA-Z0-9]{6}\.[a-zA-Z0-9_\-]{27}|mfa\.[a-zA-Z0-9_\-]{84})", token):
    #         return await ctx.send("Invalid token provided.")
    #     token_parts = token.split(".")
    #     print(token_parts)
    #     user_id = b64.b64decode(token_parts[0]).decode(encoding="ascii")
    #     if not user_id or not user_id.isdigit():
    #         return await ctx.send("Invalid user.")
    #     user_id = int(user_id)
    #     user = bot.get_user(user_id)
    #     if user is None:
    #         return await ctx.send(f"Could not find a user with id `{user_id}`.")
    #     unix = int.from_bytes(base64.standard_b64decode(token_parts[1] + "=="), "big")
    #     print(unix)
    #     timestamp = datetime.datetime.utcfromtimestamp(unix + 1293840000)
    #     embed = discord.Embed(title=f"{user.display_name}'s Token:", description=f"""
    #     **User**: {user}
    #     **ID**: {user.id}
    #     **Bot**: {user.bot}
    #     **Account Created**: {humanize.precisedelta(discord.utils.snowflake_time(user_id))} ago
    #     **Token Created**: {humanize.precisedelta(timestamp)} ago
    #     """, colour=bot.embed_colour)
    #     embed.set_thumbnail(url=user.avatar_url)
    #     await ctx.send(embed=embed)

    @commands.command()
    async def owoify(self, ctx, *, text):
        """
        Owoifies text. Mentions are escaped.

        `text` - The text to owoify.
        """
        await ctx.send(discord.utils.escape_mentions(bot.utils.owoify(text)))

    class TODOSOURCE(menus.ListPageSource):
        def __init__(self, data):
            super().__init__(data, per_page=5)

        async def format_page(self, menu, page):
            embed = discord.Embed(title=f"Todo List for `{menu.ctx.author}`",
                                  description="\n".join(f"**{number}.** {item}" for number, item in page) or "Nothing here!", colour=bot.embed_colour)
            return embed

    @commands.group(invoke_without_command=True)
    async def todo(self, ctx):
        """
        View the tasks in your todo list.
        """
        entries = await bot.pool.fetchval("SELECT tasks FROM todos WHERE user_id = $1", ctx.author.id)
        if entries is None:
            li = []
        else:
            li = [(number, item) for number, item in enumerate(entries, start=1)]
        await menus.MenuPages(source=self.TODOSOURCE(li), delete_message_after=True).start(ctx)

    @todo.command()
    async def add(self, ctx, *, task):
        """
        Add a task to your todo list.

        `task` - The task to add.
        """

        if len(task) > 100:
            return await ctx.send(f"{bot.emoji_dict['red_tick']} Task is too long.")
        tasks = await bot.pool.fetchval("SELECT tasks FROM todos WHERE user_id = $1", ctx.author.id)
        if tasks is None:
            await bot.pool.execute("INSERT INTO todos VALUES ($1)", ctx.author.id)
            tasks = []
        if len(tasks) >= 100:
            return await ctx.send(f"{bot.emoji_dict['red_tick']} Sorry, you can only have 100 tasks in your todo list at a time.")
        if task in tasks:
            return await ctx.send(f"{bot.emoji_dict['red_tick']} That task is already in your todo list.")
        await bot.pool.execute("UPDATE todos SET tasks = array_append(tasks, $1) WHERE user_id = $2", task, ctx.author.id)
        await ctx.send(f"{bot.emoji_dict['green_tick']} Added `{task}` to your todo list.")

    @todo.command()
    async def remove(self, ctx, *, task: typing.Union[int, str]):
        """
        Remove a task from your todo list.

        `task` - The task to remove. Can be the task number or the task name.
        """
        tasks = await bot.pool.fetchval("SELECT tasks FROM todos WHERE user_id = $1", ctx.author.id)
        if not tasks:
            return await ctx.send(f"{bot.emoji_dict['red_tick']} Your todo list is empty.")
        if isinstance(task, int):
            try:
                task = tasks.pop(task - 1)
            except IndexError:
                return await ctx.send(f"{bot.emoji_dict['red_tick']} Couldn't find a task with that number.")
            await bot.pool.execute("UPDATE todos SET tasks = $1 WHERE user_id = $2", tasks, ctx.author.id)
        else:
            if task not in tasks:
                return await ctx.send(f"{bot.emoji_dict['red_tick']} Couldn't find a task with that name.")
            await bot.pool.execute("UPDATE todos SET tasks = array_remove(tasks, $1) WHERE user_id = $2", task, ctx.author.id)
        if not await bot.pool.fetchval("SELECT tasks FROM todos WHERE user_id = $1", ctx.author.id):
            await bot.pool.execute("DELETE FROM todos WHERE user_id = $1", ctx.author.id)
        await ctx.send(f"{bot.emoji_dict['green_tick']} Removed `{task}` from your todo list.")


def setup(_):
    bot.add_cog(Meta())
