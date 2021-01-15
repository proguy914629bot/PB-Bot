import discord
from discord.ext import commands, menus
import random
from fuzzywuzzy import process
import asyncio
import time
import humanize
import datetime

from utils import SnakeGame


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
        self.task = ctx.bot.loop.create_task(self.loop())
        return await channel.send(embed=self.embed)

    async def get_players(self):
        if not self.player_ids:
            return "anyone can control the game"
        players = [str(await self.ctx.bot.fetch_user(player_id)) for player_id in self.player_ids]
        if len(self.player_ids) > 10:
            first10 = "\n".join(player for player in players[:10])
            return f"{first10}\nand {len(players[10:])} more..."
        return "\n".join(str(player) for player in players)

    async def refresh_embed(self):
        self.embed = discord.Embed(title=f"Snake Game", description=self.game.show_grid(),
                                   colour=self.ctx.bot.embed_colour)
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
            if payload.user_id == self.ctx.bot.user.id:
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


class TicTacToe:
    """
    Game class for tic-tac-toe.
    """
    __slots__ = ("player1", "player2", "ctx", "msg", "turn", "player_mapping", "x_and_o_mapping", "board")

    def __init__(self, ctx, player1, player2):
        self.player1 = player1
        self.player2 = player2
        self.ctx = ctx
        self.msg = None
        self.board = {'↖️': "⬜", '⬆️': "⬜", '↗️': "⬜",
                      '➡️': "⬜", '↘️': "⬜", '⬇️': "⬜",
                      '↙️': "⬜", '⬅️': "⬜", '⏺️': "⬜"}
        self.turn = random.choice([self.player1, self.player2])
        if self.turn == player1:
            self.player_mapping = {self.player1: "🇽", self.player2: "🅾️"}
            self.x_and_o_mapping = {"🇽": self.player1, "🅾️": self.player2}
            return
        self.player_mapping = {self.player2: "🇽", self.player1: "🅾️"}
        self.x_and_o_mapping = {"🇽": self.player2, "🅾️": self.player1}

    def show_board(self):
        return f"**Tic-Tac-Toe Game between `{self.player1}` and `{self.player2}`**\n\n" \
            f"🇽: `{self.x_and_o_mapping['🇽']}`\n🅾️: `{self.x_and_o_mapping['🅾️']}`\n\n" \
            f"{self.board['↖️']} {self.board['⬆️']} {self.board['↗️']}\n" \
            f"{self.board['⬅️']} {self.board['⏺️']} {self.board['➡️']}\n" \
            f"{self.board['↙️']} {self.board['⬇️']} {self.board['↘️']}\n\n"

    def switch_turn(self):
        if self.turn == self.player1:
            self.turn = self.player2
            return
        self.turn = self.player1

    async def loop(self):
        while True:
            try:
                move, user = await self.ctx.bot.wait_for(
                    "reaction_add",
                    check=lambda reaction, user: reaction.message.guild == self.ctx.guild
                    and reaction.message.channel == self.ctx.message.channel
                    and reaction.message == self.msg and str(reaction.emoji) in self.board.keys() and user == self.turn,
                    timeout=300
                )
            except asyncio.TimeoutError:
                await self.msg.edit(content=f"{self.show_board()}Game Over.\n**{self.turn}** took too long to move.")
                await self.ctx.send(f"{self.turn.mention} game over, you took too long to move. {self.msg.jump_url}")
                return
            if self.board[move.emoji] == "⬜":
                self.board[move.emoji] = self.player_mapping[self.turn]
            else:
                await self.msg.edit(content=f"{self.show_board()}**Current Turn**: `{self.turn}`\nThat place is already filled.")
                continue
            condition = (
                self.board['↖️'] == self.board['⬆️'] == self.board['↗️'] != '⬜',  # across the top
                self.board['⬅️'] == self.board['⏺️'] == self.board['➡️'] != '⬜',  # across the middle
                self.board['↙️'] == self.board['⬇️'] == self.board['↘️'] != '⬜',  # across the bottom
                self.board['↖️'] == self.board['⬅️'] == self.board['↙️'] != '⬜',  # down the left side
                self.board['⬆️'] == self.board['⏺️'] == self.board['⬇️'] != '⬜',  # down the middle
                self.board['↗️'] == self.board['➡️'] == self.board['↘️'] != '⬜',  # down the right side
                self.board['↖️'] == self.board['⏺️'] == self.board['↘️'] != '⬜',  # diagonal
                self.board['↙️'] == self.board['⏺️'] == self.board['↗️'] != '⬜',  # diagonal
            )
            if any(condition):
                await self.msg.edit(content=f"{self.show_board()}Game Over.\n**{self.turn}** won!")
                break
            if "⬜" not in self.board.values():
                await self.msg.edit(content=f"{self.show_board()}Game Over.\nIt's a Tie!")
                break
            self.switch_turn()
            await self.msg.edit(content=f"{self.show_board()}**Current Turn**: `{self.turn}`")

    async def start(self):
        self.msg = await self.ctx.send(f"{self.show_board()}Setting up the board...")
        for reaction in self.board.keys():
            await self.msg.add_reaction(reaction)
        await self.msg.edit(content=f"{self.show_board()}**Current Turn**: `{self.turn}`")
        await self.loop()


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

    @commands.command()
    async def reddit(self, ctx, *, subreddit):
        """
        Gets a random post from a subreddit of your choice.

        `subreddit` - The subreddit.
        """
        async with ctx.bot.session.get(f"https://www.reddit.com/r/{subreddit}/new.json") as resp:
            r = await resp.json()
        if r.get("error", None) is not None:
            return await ctx.send("Couldn't find a subreddit with that name.")

        posts = r["data"]["children"]
        random_post = random.choice(posts)["data"]
        posted_when = datetime.datetime.now() - datetime.datetime.fromtimestamp(random_post["created"])

        embed = discord.Embed(
            title=random_post["title"],
            description=f"Posted by `u/{random_post['author']}` {humanize.naturaldelta(posted_when)} ago\n"
            f"{ctx.bot.emoji_dict['upvote']} {random_post['ups']} {ctx.bot.emoji_dict['downvote']} {random_post['downs']}",
            colour=ctx.bot.embed_colour)
        embed.set_author(name=random_post["subreddit_name_prefixed"])
        embed.set_image(url=random_post["url"])
        embed.set_footer(text=f"{random_post['num_comments']} comment{'s' if random_post['num_comments'] > 1 else ''} • {random_post['upvote_ratio'] * 100}% upvote ratio")

        if random_post["over_18"]:
            cembed = discord.Embed(
                title="This post has been marked as nsfw. Are you sure that you want to view it?",
                description="If you agree, it will be sent to your dms.", colour=ctx.bot.embed_colour)
            confirm = await ctx.bot.utils.EmbedConfirm(cembed).prompt(ctx)
            if confirm:
                await ctx.author.send(embed=embed)
            return
        await ctx.send(embed=embed)

    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.command(aliases=["c"])
    async def cookie(self, ctx):
        """
        Yum yum.
        """
        cookies = ["🍪", "🥠"]
        reaction = random.choices(cookies, weights=[0.9, 0.1], k=1)[0]
        embed = discord.Embed(description=f"First one to eat the {reaction} wins!", colour=ctx.bot.embed_colour)
        message = await ctx.send(embed=embed)
        await asyncio.sleep(4)
        for i in reversed(range(1, 4)):
            await message.edit(embed=discord.Embed(description=str(i), colour=ctx.bot.embed_colour))
            await asyncio.sleep(1)
        await asyncio.sleep(random.randint(1, 3))
        await message.edit(embed=discord.Embed(description="Eat the cookie!", colour=ctx.bot.embed_colour))
        await message.add_reaction(reaction)
        start = time.perf_counter()
        try:
            _, user = await ctx.bot.wait_for(
                "reaction_add",
                check=lambda _reaction, user: _reaction.message.guild == ctx.guild
                and _reaction.message.channel == ctx.message.channel
                and _reaction.message == message and str(_reaction.emoji) == reaction and user != ctx.bot.user
                and not user.bot,
                timeout=60,)
        except asyncio.TimeoutError:
            return await message.edit(embed=discord.Embed(description="No one ate the cookie...",
                                                          colour=ctx.bot.embed_colour))
        end = time.perf_counter()
        await message.edit(embed=discord.Embed(description=f"**{user}** ate the cookie in `{end - start:.3f}` seconds!",
                                               colour=ctx.bot.embed_colour))

    @commands.command(aliases=["ttt", "tic-tac-toe"])
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
            response, _ = await ctx.bot.wait_for(
                "reaction_add",
                check=lambda reaction, user: reaction.message.guild == ctx.guild
                and reaction.message.channel == ctx.message.channel
                and reaction.message == msg
                and str(reaction.emoji) in ["\N{WHITE HEAVY CHECK MARK}", "\N{CROSS MARK}"]
                and user == player2,
                timeout=300)
        except asyncio.TimeoutError:
            return await ctx.send(f"**{player2}** took too long to respond. {msg.jump_url}")
        if response.emoji == "\N{CROSS MARK}":
            return await ctx.send(f"**{player2}** has declined your challenge {ctx.author.mention}.")
        ttt = TicTacToe(ctx, ctx.author, player2)
        await ttt.start()

    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.command()
    async def snake(self, ctx, *args):
        """
        Play a game of snake by yourself or with others.

        `args` - The users who can control the game. Set this to `--public` to allow anyone to control the game.
        """
        async with ctx.typing():
            if "--public" in args:
                player_ids = []
            else:
                player_ids = set()
                for arg in args:
                    player = await commands.MemberConverter().convert(ctx, arg)
                    if not player.bot:
                        player_ids.add(player.id)
                player_ids.add(ctx.author.id)
            menu = SnakeMenu(player_ids, clear_reactions_after=True)
        await menu.start(ctx, wait=True)  # end typing


def setup(bot):
    bot.add_cog(Fun())
