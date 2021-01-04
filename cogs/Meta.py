import discord
from discord.ext import commands, flags, menus
import asyncio
import random
import pytesseract
import io
import cv2
import numpy as np
from distutils.util import strtobool
import re
import base64 as b64
import humanize
import datetime
import pathlib
from pyfiglet import Figlet

from dependencies import bot
from config import config

f = Figlet()
pytesseract.pytesseract.tesseract_cmd = config["tesseract_path"]


class Meta(commands.Cog):
    """
    Commands that don't belong to any specific category.
    """
    @commands.command()
    async def mystbin(self, ctx, *, text_to_paste=None):
        """
        Paste text or a text file to https://mystb.in.

        `text_to_paste` - The text to paste to mystbin.
        """
        data = []
        if text_to_paste:
            data.append(text_to_paste)
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
    async def hastebin(self, ctx, *, text_to_paste=None):
        """
        Paste text or a text file to https://hastebin.com.

        `text_to_paste` - The text to paste to hastebin.
        """
        data = []
        if text_to_paste:
            data.append(text_to_paste)
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
        if comic_number is None:
            comic_number = random.randint(1, 2406)
        if comic_number == 0:
            return await ctx.send("There is no comic number zero.")
        if comic_number > 2406:
            return await ctx.send("Xkcd has only 2406 comics.")
        async with bot.session.get(f"https://xkcd.com/{comic_number}/info.0.json") as r:
            response = await r.json()
        embed = discord.Embed(title=response["title"], colour=bot.embed_colour)
        embed.set_image(url=response["img"])
        await ctx.send(embed=embed)

    def _ocr(self, bytes):
        img = cv2.imdecode(np.fromstring(bytes, np.uint8), 1)
        _, buffer = cv2.imencode(".png", img)
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

    @commands.command()
    async def define(self, ctx, *, word):
        """
        Search up the definition of a word. Source: https://dictionaryapi.dev/

        `word` - The word to search up.
        """
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        async with bot.session.get(url) as r:
            response = await r.json()
        if isinstance(response, dict):  # no definitions found
            return await ctx.send(response["message"])
        word_info = response[0]
        embed = discord.Embed(title=f"Dictionary search results for `{word}`; found `{word_info['word']}`",
                              description=f"""
        **Phonetics**: {word_info["phonetics"][0]["text"]} [audio]({word_info["phonetics"][0]["audio"]})
        """, colour=bot.embed_colour)
        for item in word_info["meanings"]:
            def_str = ""
            definition = item["definitions"][0]
            try:
                synonyms = " | ".join(synonym for synonym in definition["synonyms"])
            except KeyError:
                synonyms = "None"
            try:
                example = definition["example"]
            except KeyError:
                example = "None"
            def_str += f"""
            **Definition**: {definition["definition"]}
            **Example**: {example}
            **Synonyms**: {synonyms}\n\n
            """
            embed.add_field(name=item["partOfSpeech"], value=def_str)
        embed.add_field(name="Raw JSON Response", value=f"[Click Here]({url})")
        await ctx.send(embed=embed)

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


def setup(_):
    bot.add_cog(Meta())
