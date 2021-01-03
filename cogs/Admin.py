import discord
from discord.ext import commands, menus
import datetime
import re


from dependencies import bot


class Admin(commands.Cog):
    """
    Commands that only my owner can use.
    """
    def cog_check(self, ctx):
        if ctx.author.id == bot.owner_id:
            return True
        raise commands.NotOwner()

    @commands.group(invoke_without_command=True, aliases=['adm', 'dev'])
    async def admin(self, ctx):
        """
        Admin commands.
        """

    @admin.command(
        aliases=['terminate', 'stop']
    )
    async def shutdown(self, ctx):
        """
        Terminates the bot.
        """
        confirm_embed = bot.utils.EmbedConfirm(discord.Embed(title="Are you sure?", colour=bot.embed_colour), delete_message_after=False)
        confirm = await confirm_embed.prompt(ctx)
        if confirm:
            await confirm_embed.message.edit(
                embed=discord.Embed(title="Logging out now...",
                colour=bot.embed_colour,
                timestamp=datetime.datetime.utcnow())
            )
            await bot.close()
        else:
            await confirm_embed.message.delete()

    @admin.command()
    async def load(self, ctx, *args):
        """
        Loads cogs.
        """
        if "all" in args or "All" in args:
            cogs_to_load = bot.coglist
        else:
            cogs_to_load = [f"cogs.{cog}" if cog != "jishaku" else "jishaku" for cog in args]
        finished_cog_list = []
        for cog in cogs_to_load:
            try:
                bot.load_extension(cog)
                finished_cog_list.append(f"✅ `{cog}`")
            except Exception as e:
                finished_cog_list.append(f"❌ `{cog}`: {e}")
        finished_cogs = '\n'.join(expression for expression in finished_cog_list)
        await ctx.send(f"**Finished Loading Cogs**\n\n{finished_cogs}")

    @admin.command()
    async def unload(self, ctx, *args):
        """
        Unloads cogs.
        """
        if "all" in args or "All" in args:
            cogs_to_unload = bot.coglist
        else:
            cogs_to_unload = [f"cogs.{cog}" if cog != "jishaku" else "jishaku" for cog in args]
        try:
            cogs_to_unload.remove("cogs.Admin")  # :^)
        except ValueError:
            pass
        finished_cog_list = []
        for cog in cogs_to_unload:
            try:
                bot.unload_extension(cog)
                finished_cog_list.append(f"✅ `{cog}`")
            except Exception as e:
                finished_cog_list.append(f"❌ `{cog}`: {e}")
        finished_cogs = '\n'.join(expression for expression in finished_cog_list)
        await ctx.send(f"**Finished Unloading Cogs**\n\n{finished_cogs}")

    @admin.command()
    async def reload(self, ctx, *args):
        """
        Reloads cogs.
        """
        if "all" in args or "All" in args:
            cogs_to_reload = list(bot.extensions.keys())
        else:
            cogs_to_reload = [f"cogs.{cog}" if cog != "jishaku" else "jishaku" for cog in args]
        finished_cog_list = []
        for cog in cogs_to_reload:
            try:
                bot.reload_extension(cog)
                finished_cog_list.append(f"✅ `{cog}`")
            except Exception as e:
                finished_cog_list.append(f"❌ `{cog}`: {e}")
        finished_cogs = '\n'.join(expression for expression in finished_cog_list)
        await ctx.send(f"**Finished Reloading Cogs**\n\n{finished_cogs}")

    class TODOSOURCE(menus.ListPageSource):
        def __init__(self, data):
            super().__init__(data, per_page=5)

        async def format_page(self, menu, page):
            embed = discord.Embed(title="Todo List", description="\n".join(f"**{number}.** {item}" for number, item in page) or "Nothing here!", colour=bot.embed_colour)
            return embed

    @admin.group(invoke_without_command=True)
    async def todo(self, ctx):
        """
        View the items in the todo list.
        """
        entries = [entry['task'] for entry in await bot.pool.fetch("SELECT * FROM todolist")]
        li = [(number, item) for number, item in enumerate(entries, start=1)]
        await menus.MenuPages(source=self.TODOSOURCE(li), delete_message_after=True).start(ctx)

    @todo.command()
    async def add(self, ctx, *, task):
        """
        Add an item to the todo list.
        """
        if await bot.pool.fetchval("SELECT * FROM todolist WHERE task = $1", task):
            return await ctx.send(f"`{task}` is already in the todo list.")
        await bot.pool.execute("INSERT INTO todolist VALUES ($1)", task)
        await ctx.send(f"Added `{task}` to the todo list.")

    @todo.command()
    async def remove(self, ctx, *, task):
        """
        Remove an item from the todo list.
        """
        if not await bot.pool.fetchval("SELECT * FROM todolist WHERE task = $1", task):
            return await ctx.send(f"`{task}` is not in the todo list.")
        await bot.pool.execute("DELETE FROM todolist WHERE task = $1", task)
        await ctx.send(f"Removed `{task}` from the todo list.")

    @admin.command()
    async def cleanup(self, ctx: commands.Context, amount: int = 10, limit: int = 100):
        """
        Delete the first `x` messages that I sent in the current channel. `x` defaults to 10.
        """
        counter = 0
        async for message in ctx.channel.history(limit=limit):
            if message.author.id == bot.user.id:
                await message.delete()
                counter += 1
                if counter >= amount:
                    break
        await ctx.send(f"Successfully purged `{counter}` message(s).")  # using `counter` here as the message limit can prevent all the messages from being purged.

    @admin.command()
    async def emojisnipe(self, ctx, name: str, emoji: bytes=None):
        """
        Snipes emojis.
        """
        if not emoji:
            emoji = await ctx.message.attachments[0].read()
        await bot.get_guild(719665666696675369).create_custom_emoji(name=name, image=emoji)
        await ctx.send("👌")

    @admin.group(invoke_without_command=True)
    async def error(self, ctx):
        """
        Commands to manage the error database.
        """
        data = await bot.pool.fetch("SELECT * FROM errors")
        await ctx.send(f"There are `{len(data)}` errors in the database.")

    @error.command()
    async def view(self, ctx, err_num: int, thing_to_view="traceback"):
        """
        View information of an error in the database.
        """
        thing_to_view = thing_to_view.lower()
        data = await bot.pool.fetchval(f"SELECT {thing_to_view} FROM errors WHERE err_num = $1", err_num)
        if not data:
            return await ctx.send("Could not find entry in database.")
        if thing_to_view == "traceback":
            if len(data) > 1991: # 1991 + len("```py\n```")
                data = await bot.mystbin(data)
            else:
                data = f"```py\n{data}```"
        await ctx.send(data)

    @error.command()
    async def fix(self, ctx, error):
        """
        Remove an error (or errors) from the database.
        """
        if re.match(r"\d+-\d+", error): # x-x
            rnge = error.split("-")
            for i in range(int(rnge[0]), int(rnge[1]) + 1):
                await bot.pool.execute("DELETE FROM errors WHERE err_num = $1", i)
            await ctx.send(f"Successfully removed errors `{rnge[0]}` to `{rnge[1]}`.")
        elif error.lower() == "all":
            await bot.pool.execute("DELETE FROM errors")
            await ctx.send("Thanks for fixing all my errors!")
        elif error.isdigit():
            await bot.pool.execute("DELETE FROM errors WHERE err_num = $1", int(error))
            await ctx.send("👌")
        else:
            await ctx.send("Invalid option.")

# todo rewrite the error handling system

def setup(_):
    bot.add_cog(Admin())
