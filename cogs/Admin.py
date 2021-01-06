import discord
from discord.ext import commands, menus
import datetime
import re
import subprocess


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

        `args` - Any amount of cogs to load.
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

        `args` - Any amount of cogs to unload.
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

        `args` - Any amount of cogs to reload.
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
        View the tasks in the todo list.
        """
        entries = [entry['task'] for entry in await bot.pool.fetch("SELECT * FROM todolist")]
        li = [(number, item) for number, item in enumerate(entries, start=1)]
        await menus.MenuPages(source=self.TODOSOURCE(li), delete_message_after=True).start(ctx)

    @todo.command()
    async def add(self, ctx, *, task):
        """
        Add a task to the todo list.

        `task` - The task to add.
        """
        if await bot.pool.fetchval("SELECT * FROM todolist WHERE task = $1", task):
            return await ctx.send(f"`{task}` is already in the todo list.")
        await bot.pool.execute("INSERT INTO todolist VALUES ($1)", task)
        await ctx.send(f"Added `{task}` to the todo list.")

    @todo.command()
    async def remove(self, ctx, *, task):
        """
        Remove a task from the todo list.

        `task` - The task to remove.
        """
        if not await bot.pool.fetchval("SELECT * FROM todolist WHERE task = $1", task):
            return await ctx.send(f"`{task}` is not in the todo list.")
        await bot.pool.execute("DELETE FROM todolist WHERE task = $1", task)
        await ctx.send(f"Removed `{task}` from the todo list.")

    @admin.command()
    async def cleanup(self, ctx: commands.Context, amount: int = 10, limit: int = 100):
        """
        Self-deletes messages in the current channel.

        `amount` - The amount of messages to delete. Defaults to 10.
        `limit` - The amount of messages to search through. Defaults to 100.
        """
        counter = 0
        async for message in ctx.channel.history(limit=limit):
            if message.author.id == bot.user.id:
                await message.delete()
                counter += 1
                if counter >= amount:
                    break
        await ctx.send(f"Successfully purged `{counter}` message(s).")

    @admin.command()
    async def emojisnipe(self, ctx, name: str, emoji: discord.Emoji=None):
        """
        Snipes emojis for personal use.

        `name` - The name of the emoji.
        `emoji` - The emoji to snipe (can NOT be unicode).
        """
        if emoji:
            emoji = await emoji.url.read()
        else:
            try:
                emoji = await ctx.message.attachments[0].read()
            except (IndexError, TypeError):
                return await ctx.send("No emoji provided.")
        await bot.get_guild(719665666696675369).create_custom_emoji(name=name, image=emoji)
        await ctx.send("👌")

    class ErrorSource(menus.ListPageSource):
        async def format_page(self, menu, page):
            if isinstance(page, list):
                page = page[0]
            traceback = page['traceback'] if len(page['traceback']) < 2000 else await bot.mystbin(page['traceback'])
            embed = discord.Embed(title=f"Error Number {page['err_num']}", description=f"```py\n{traceback}```")
            for k, v in list(page.items()):
                if k in ("err_num", "traceback"):
                    continue
                value = f"`{v}`" if len(v) < 1000 else await bot.mystbin(v)
                embed.add_field(name=k.replace("_", " ").title(), value=value)
            return embed

    @admin.group(invoke_without_command=True)
    async def error(self, ctx):
        """
        View the errors in the database.
        """
        data = await bot.pool.fetch("SELECT * FROM errors")
        await menus.MenuPages(self.ErrorSource(data, per_page=1)).start(ctx)

    @error.command()
    async def view(self, ctx, err_num: int):
        """
        View information about an error in the database.

        `err_num` - The error number to search for.
        """
        error = await bot.pool.fetch(f"SELECT * FROM errors WHERE err_num = $1", err_num)
        if not error:
            return await ctx.send(f"Could not find an error with the number `{err_num}` in the database.")
        await menus.MenuPages(self.ErrorSource([error], per_page=1)).start(ctx)  # lazy me :p

    @error.command()
    async def fix(self, ctx, error):
        """
        Remove an error or errors from the database.

        `error` - The errors to remove from the database.
        """
        if re.match(r"\d+-\d+", error):  # x-x
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

    @admin.command()
    async def sync(self, ctx):
        """
        Syncs code with github and restarts the bot.
        """
        out = subprocess.check_output("git pull", shell=True)
        await ctx.send(f"```{out.decode('utf-8')}```")
        await ctx.message.add_reaction("🔁")
        await bot.close()


# todo rewrite the error handling system
# and sync command


def setup(_):
    bot.add_cog(Admin())
