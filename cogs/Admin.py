import discord
from discord.ext import commands, menus
import datetime
import re
import subprocess
import typing


class Admin(commands.Cog):
    """
    Commands that only my owner can use.
    """
    async def cog_check(self, ctx):
        if not ctx.bot.is_owner(ctx.author):
            raise commands.NotOwner
        return True

    @commands.group(invoke_without_command=True, aliases=['adm', 'dev', 'owner'])
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
        confirm_embed = ctx.bot.utils.EmbedConfirm(discord.Embed(title="Are you sure?", colour=ctx.bot.embed_colour),
                                                   delete_message_after=False)
        confirm = await confirm_embed.prompt(ctx)
        if confirm:
            await confirm_embed.message.edit(
                embed=discord.Embed(title="Logging out now...",
                                    colour=ctx.bot.embed_colour,
                                    timestamp=datetime.datetime.utcnow())
            )
            await ctx.bot.close()
        else:
            await confirm_embed.message.delete()

    @admin.command()
    async def load(self, ctx, *cogs):
        """
        Loads cogs.

        `args` - Any amount of cogs to load.
        """
        if any(cog.lower() == "all" for cog in cogs):
            cogs_to_load = ctx.bot.coglist
        else:
            cogs_to_load = [f"cogs.{cog}" if cog.lower() != "jishaku" else "jishaku" for cog in cogs]

        finished_cogs = []
        for cog in cogs_to_load:
            try:
                ctx.bot.load_extension(cog)
                finished_cogs.append(f"✅ `{cog}`")
            except Exception as e:
                finished_cogs.append(f"❌ `{cog}`: {e}")
        finished_cogs = "\n".join(finished_cogs)
        await ctx.send(f"**Finished Loading Cogs**\n\n{finished_cogs}")

    @admin.command()
    async def unload(self, ctx, *cogs):
        """
        Unloads cogs.

        `args` - Any amount of cogs to unload.
        """
        if any(cog.lower() == "all" for cog in cogs):
            cogs_to_unload = list(ctx.bot.extensions)
        else:
            cogs_to_unload = [f"cogs.{cog}" if cog.lower() != "jishaku" else "jishaku" for cog in cogs]

        try:
            cogs_to_unload.remove("cogs.Admin")  # :^)
        except ValueError:
            pass

        finished_cogs = []
        for cog in cogs_to_unload:
            try:
                ctx.bot.unload_extension(cog)
                finished_cogs.append(f"✅ `{cog}`")
            except Exception as e:
                finished_cogs.append(f"❌ `{cog}`: {e}")
        finished_cogs = "\n".join(finished_cogs)
        await ctx.send(f"**Finished Unloading Cogs**\n\n{finished_cogs}")

    @admin.command()
    async def reload(self, ctx, *cogs):
        """
        Reloads cogs.

        `args` - Any amount of cogs to reload.
        """
        if any(cog.lower() == "all" for cog in cogs):
            cogs_to_reload = list(ctx.bot.extensions)
        else:
            cogs_to_reload = [f"cogs.{cog}" if cog.lower() != "jishaku" else "jishaku" for cog in cogs]
        finished_cogs = []
        for cog in cogs_to_reload:
            try:
                ctx.bot.reload_extension(cog)
                finished_cogs.append(f"✅ `{cog}`")
            except Exception as e:
                finished_cogs.append(f"❌ `{cog}`: {e}")
        finished_cogs = '\n'.join(finished_cogs)
        await ctx.send(f"**Finished Reloading Cogs**\n\n{finished_cogs}")

    @admin.command()
    async def cleanup(self, ctx, amount: int = 10, limit: int = 100):
        """
        Self-deletes messages in the current channel.

        `amount` - The amount of messages to delete. Defaults to 10.
        `limit` - The amount of messages to search through. Defaults to 100.
        """
        counter = 0
        async for message in ctx.channel.history(limit=limit):
            if message.author.id == ctx.bot.user.id:
                await message.delete()
                counter += 1
                if counter >= amount:
                    break
        await ctx.send(f"Successfully purged `{counter}` message(s).")

    @admin.command()
    async def emojisnipe(self, ctx, name: str, emoji: typing.Union[discord.Emoji, discord.PartialEmoji] = None):
        """
        Snipes emojis for personal use.

        `name` - The name of the emoji.
        `emoji` - The emoji to snipe (can NOT be unicode).
        """
        if emoji:
            emoji = await emoji.url.read()
        else:
            if not ctx.message.attachments:
                return await ctx.send("No emoji provided.")
            emoji = await ctx.message.attachments[0].read()
        await ctx.bot.get_guild(798329404325101600).create_custom_emoji(name=name, image=emoji)
        await ctx.send("👌")

    class ErrorSource(menus.ListPageSource):
        async def format_page(self, menu: menus.MenuPages, page):
            if isinstance(page, list):
                page = page[0]
            traceback = f"```py\n{page['traceback']}```" if len(page["traceback"]) < 2000 else await menu.ctx.bot.mystbin(page["traceback"])
            embed = discord.Embed(title=f"Error Number {page['err_num']}", description=traceback)
            for k, v in list(page.items()):
                if k in ("err_num", "traceback"):
                    continue
                value = f"`{v}`" if len(v) < 1000 else await menu.ctx.bot.mystbin(v)
                embed.add_field(name=k.replace("_", " ").title(), value=value)
            return embed

    @admin.group(invoke_without_command=True)
    async def error(self, ctx):
        """
        View the errors in the database.
        """
        errors = await ctx.bot.pool.fetch("SELECT * FROM errors")
        if not errors:
            return await ctx.send("No errors in the database! 🥳")
        await menus.MenuPages(self.ErrorSource(errors, per_page=1), delete_message_after=True).start(ctx)

    @error.command()
    async def view(self, ctx, err_num: int):
        """
        View information about an error in the database.

        `err_num` - The error number to search for.
        """
        error = await ctx.bot.pool.fetch(f"SELECT * FROM errors WHERE err_num = $1", err_num)
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
                await ctx.bot.pool.execute("DELETE FROM errors WHERE err_num = $1", i)
            await ctx.send(f"Successfully removed errors `{rnge[0]}` to `{rnge[1]}`.")
        elif error.lower() == "all":
            await ctx.bot.pool.execute("DELETE FROM errors")
            await ctx.send("Thanks for fixing all my errors!")
        elif error.isdigit():
            await ctx.bot.pool.execute("DELETE FROM errors WHERE err_num = $1", int(error))
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
        await ctx.bot.close()  # process manager handles the rest


def setup(bot):
    bot.add_cog(Admin())
