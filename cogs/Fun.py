import discord
from discord.ext import commands, menus
import random
from fuzzywuzzy import process
import asyncio
import time
from utils import SnakeGame

from dependencies import bot


class SnakeMenu(menus.Menu):
    """
    Menu for snake game.
    """
    def __init__(self, player_ids, **kwargs):
        super().__init__(**kwargs)
        self.game = SnakeGame(empty="⬛")
        self.player_ids = player_ids
        self.direction = None
        self.task = None
        self.embed = None
        self.is_game_start = asyncio.Event()

    async def send_initial_message(self, ctx, channel):
        await self.refresh_embed()
        self.task = bot.loop.create_task(self.loop())
        return await ctx.send(embed=self.embed)

    async def get_players(self):
        if not self.player_ids:
            return "anyone can control the game"
        return "\n".join(str(player) for player in [await bot.fetch_user(player_id) for player_id in self.player_ids])

    async def refresh_embed(self):
        self.embed = discord.Embed(title=f"Snake Game", description=self.game.show_grid(), colour=bot.embed_colour)
        self.embed.add_field(name="Players", value=await self.get_players())
        self.embed.add_field(name="Score", value=self.game.score)
        self.embed.add_field(name="Current Direction", value=self.direction)

    async def loop(self):
        await self.is_game_start.wait()
        while not self.game.lose:
            await asyncio.sleep(1.5)
            self.game.update(self.direction)
            await self.refresh_embed()
            await self.message.edit(embed=self.embed)
        self.embed.add_field(name="Game Over", value=self.game.lose)
        await self.message.edit(embed=self.embed)
        self.stop()

    def reaction_check(self, payload):
        if payload.message_id != self.message.id:
            return False

        if self.player_ids:  # only specific people can access the board
            if payload.user_id not in self.player_ids:
                return False
        else:
            if payload.user_id == bot.user.id:
                return False
        return payload.emoji in self.buttons

    @menus.button("⬆️")
    async def up(self, _):
        self.direction = "up"
        self.is_game_start.set()

    @menus.button("⬇️")
    async def down(self, _):
        self.direction = "down"
        self.is_game_start.set()

    @menus.button("⬅️")
    async def left(self, _):
        self.direction = "left"
        self.is_game_start.set()

    @menus.button("➡️")
    async def right(self, _):
        self.direction = "right"
        self.is_game_start.set()

    @menus.button("⏹️")
    async def on_stop(self, _):
        self.stop()


class Fun(commands.Cog):
    """
    Fun commands.
    """
    @commands.command()
    async def coinflip(self, ctx):
        """
        Returns heads, tails or ???.
        """
        result = random.choices(population=["heads", "tails", "side"], weights=[0.45, 0.45, 0.01], k=1)[0]
        if result == "side":
            return await ctx.send("You flipped a coin and it landed on it's `side`!")
        await ctx.send(f"You flipped a coin and got `{result}`!")

    @commands.command(
        aliases=["cm"]
    )
    async def cleanmeme(self, ctx, category=None):
        """
        Gets a random post from r/CleanMemes.

        `category` - The category to search in. Available categories: hot, new, top, rising.
        """
        if category is None:
            category = "hot"
        category, _ = process.extractOne(category, ["hot", "new", "top", "rising"])
        async with bot.session.get(f"https://www.reddit.com/r/CleanMemes/new.json?sort={category}") as r:
            response = await r.json()
            embed = discord.Embed(title=response['data']['children']
            [random.randint(0, len(response['data']['children']) - 1)]['data']['title'], colour=bot.embed_colour)
            embed.set_image(url=response['data']['children']
                            [random.randint(0, len(response['data']['children']) - 1)]['data']['url'])
        try:
            await ctx.author.send(embed=embed)
            try:
                await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
            except discord.Forbidden:
                pass
        except discord.Forbidden:
            await ctx.send(f"Your DMs are off {ctx.author}.")

    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.command(
        aliases=["c"]
    )
    async def cookie(self, ctx):
        """
        Yum yum.
        """
        cookies = ["🍪", "🥠"]
        reaction = random.choices(cookies, weights=[0.9, 0.1], k=1)[0]
        embed = discord.Embed(description=f"First one to eat the {reaction} wins!", colour=bot.embed_colour)
        message = await ctx.send(embed=embed)
        await asyncio.sleep(4)
        for i in reversed(range(1, 4)):
            await message.edit(embed=discord.Embed(description=str(i), colour=bot.embed_colour))
            await asyncio.sleep(1)
        # await asyncio.sleep(random.randint(1, 3))
        await message.edit(embed=discord.Embed(description="Eat the cookie!", colour=bot.embed_colour))
        await message.add_reaction(reaction)
        start = time.perf_counter()
        try:
            _, user = await bot.wait_for("reaction_add", timeout=60,
                                        check=lambda _reaction, user: _reaction.message.guild == ctx.guild
                                        and _reaction.message.channel == ctx.message.channel
                                        and _reaction.message == message and str(_reaction.emoji) == reaction and user != bot.user
                                        and not user.bot)
        except asyncio.TimeoutError:
            return await message.edit(embed=discord.Embed(description="No one ate the cookie...", colour=bot.embed_colour))
        end = time.perf_counter()
        await message.edit(embed=discord.Embed(description=f"**{user}** ate the cookie in `{end - start:.3f}` seconds!", colour=bot.embed_colour))

    @commands.command(
        aliases=["ttt", "tic-tac-toe"]
    )
    async def tictactoe(self, ctx, *, player2: discord.Member):
        """
        Challenge someone to a game of tic-tac-toe!

        `player2` - The user to challenge.
        """
        if player2 == ctx.author:
            return await ctx.send(f"You can't challenge yourself {ctx.author.mention}.")
        if player2.bot:
            return await ctx.send(f"You can't challenge bots {ctx.author.mention}.")
        msg = await ctx.send(f"{player2.mention}, **{ctx.author}** has challenged you to a game of tic tac toe! Do you accept their challenge?")
        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{CROSS MARK}")
        try:
            response, _ = await bot.wait_for("reaction_add",
                                check=lambda reaction, user: reaction.message.guild == ctx.guild
                                and reaction.message.channel == ctx.message.channel
                                and reaction.message == msg
                                and str(reaction.emoji) in ["\N{WHITE HEAVY CHECK MARK}", "\N{CROSS MARK}"]
                                and user == player2, timeout=300)
        except asyncio.TimeoutError:
            return await ctx.send(f"**{player2}** took too long to respond. {msg.jump_url}")
        if response.emoji == "\N{CROSS MARK}":
            return await ctx.send(f"**{player2}** has declined your challenge {ctx.author.mention}.")
        ttt = bot.utils.TicTacToe(ctx, ctx.author, player2)
        await ttt.start()

    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.command()
    async def snake(self, ctx, *args):
        """
        Play a game of snake by yourself or with others.

        `args` - The users who can control the game. Set this to `--public` to allow anyone to control the game.
        """
        if "--public" in args:
            player_ids = []
        else:
            player_ids = [(await commands.MemberConverter().convert(ctx, arg)).id for arg in args]
            player_ids.append(ctx.author.id)
        menu = SnakeMenu(player_ids, clear_reactions_after=True)
        await menu.start(ctx, wait=True)


def setup(_):
    bot.add_cog(Fun())
