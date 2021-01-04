import discord
from discord.ext import commands, menus
from fuzzywuzzy import process

from dependencies import bot


class HelpSource(menus.ListPageSource):
    """
    Page Source for paginated help command.
    """
    def __init__(self, data, ctx):
        super().__init__(data, per_page=1)
        self.ctx = ctx

    async def format_page(self, menu, page):
        embed = discord.Embed(title="Help Menu for PB Bot", description=f"Page {menu.current_page + 1}/{self.get_max_pages()}", color=bot.embed_colour)
        embed.set_thumbnail(url=bot.user.avatar_url)
        if self.ctx.clean_prefix.endswith(" "):
            self.ctx.clean_prefix = self.ctx.clean_prefix.strip() + " "
        embed.set_footer(text=f"Type {self.ctx.clean_prefix}help (command) for more info on a command.\nYou can also type {self.ctx.clean_prefix}help (category) for more info on a category.")
        if menu.current_page == 0:
            embed.add_field(name="About", value=bot.description)
        else:
            # page[0] = cog name
            # page[1] = cog instance
            _commands = "\n".join(str(command) for command in page[1].get_commands())
            if not _commands:
                _commands = "No commands in this category."
            embed.add_field(name=page[0], value=_commands)
        return embed


class PaginatedHelpCommand(menus.MenuPages):
    """
    Paginated help command implementation.
    """
    @menus.button('\U00002139', position=menus.Last(2))
    async def on_info(self, _):
        embed = discord.Embed(title="How to Use the Paginator",
                              color=bot.embed_colour)
        embed.add_field(name="Add and Remove Reactions to Navigate the Help Menu:", value = \
        "➡️ next page\n"
        "⬅️ previous page\n"
        "⏮️ first page\n"
        "⏭️ last page\n"
        "ℹ️ shows this message\n"
        "❔    shows how to read the bot's signature\n"
        "⏹️ closes the paginator"
        )
        embed.set_thumbnail(url=bot.user.avatar_url)
        embed.set_footer(text=f"You were on page {self.current_page + 1} before this message.")
        await self.message.edit(embed=embed)

    @menus.button('\U00002754', position=menus.Last(3))
    async def on_question_mark(self, _):
        embed = discord.Embed(title="How to read the Bot's Signature", description= \
        "`<argument>`: required argument\n"
        "`[argument]`: optional argument (These arguments will usually have an '=' followed by their default value.)\n"
        , color=bot.embed_colour)
        embed.set_thumbnail(url=bot.user.avatar_url)
        embed.set_footer(text=f"You were on page {self.current_page + 1} before this message.")
        await self.message.edit(embed=embed)

    @menus.button('\N{BLACK SQUARE FOR STOP}\ufe0f', position=menus.Last(4))
    async def end_menu(self, _):
        self.stop()


class CustomHelpCommand(commands.HelpCommand):
    """
    Custom help command for PB Bot.
    """
    async def send_bot_help(self, _):
        data = {0: None}
        data.update({num: cog_pair for num, cog_pair in enumerate(bot.cogs.items(), start=1)})
        pages = PaginatedHelpCommand(source=HelpSource(data, self.context), clear_reactions_after=True)
        # try:
        #     user = await self.context.author.create_dm()
        #     await pages.start(self.context, channel=user)
        # except discord.Forbidden:
        #     confirm = await Confirm("Your DMs are off. Do you want me to send help in this channel?").prompt(self.context)
        #     if confirm:
        #         await pages.start(self.context)
        await pages.start(self.context)
        try:
            await self.context.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
        except discord.Forbidden:
            pass

    async def send_command_help(self, command):
        if not command.aliases:
            aliases = 'None'
        else:
            aliases = "\n".join(alias for alias in command.aliases)
        embed = discord.Embed(title=f"Help on Command `{command.name}`", description=command.help or 'No info available.', colour=bot.embed_colour)
        embed.set_thumbnail(url=bot.user.avatar_url)
        embed.add_field(name="Signature:", value=f"{command.name} {command.signature}", inline=False)
        embed.add_field(name="Category:", value=f"{command.cog_name}", inline=False)
        embed.add_field(name="Aliases:", value=aliases, inline=False)

        if self.clean_prefix.endswith(" "):
            clean_prefix = self.clean_prefix.strip() + " "
        else:
            clean_prefix = self.clean_prefix

        embed.set_footer(text=f"Type {clean_prefix}help (command) for more info on a command.\nYou can also type {clean_prefix}help (category) for more info on a category.")
        return await self.context.send(embed=embed)

    async def send_cog_help(self, cog):
        if not cog.get_commands():
            _commands = 'None'
        else:
            _commands = "\n".join(str(command) for command in cog.get_commands())
        embed = discord.Embed(title=f"Help on Category `{cog.qualified_name}`", description=cog.description or 'No info available.', colour=bot.embed_colour)
        embed.set_thumbnail(url=bot.user.avatar_url)
        embed.add_field(name="Commands in this Category:", value=_commands)

        if self.clean_prefix.endswith(" "):
            clean_prefix = self.clean_prefix.strip() + " "
        else:
            clean_prefix = self.clean_prefix

        embed.set_footer(text=f"Type {clean_prefix}help (command) for more info on a command.\nYou can also type {clean_prefix}help (category) for more info on a category.")
        return await self.context.send(embed=embed)

    async def send_group_help(self, group):
        if not group.aliases:
            aliases = 'None'
        else:
            aliases = "\n".join(alias for alias in group.aliases)
        if not group.walk_commands():
            _commands = "None"
        else:
            _commands = "\n".join(str(command) for command in group.walk_commands())
        embed = discord.Embed(title=f"Help on Command Group `{group.name}`", description=group.help or 'No info available.', colour=bot.embed_colour)
        embed.add_field(name="Signature:", value=f"{group.name} {group.signature}", inline=False)
        embed.add_field(name="Category:", value=f"{group.cog_name}", inline=False)
        embed.add_field(name="Aliases:", value=aliases, inline=False)
        embed.add_field(name="Commands in this Group:", value=_commands)
        embed.set_thumbnail(url=bot.user.avatar_url)

        if self.clean_prefix.endswith(" "):
            clean_prefix = self.clean_prefix.strip() + " "
        else:
            clean_prefix = self.clean_prefix

        embed.set_footer(text=f"Type {clean_prefix}help (command) for more info on a command.\nYou can also type {clean_prefix}help (category) for more info on a category.")
        return await self.context.send(embed=embed)

    async def command_not_found(self, string):
        match, ratio = process.extractOne(string, bot.command_list)
        if ratio < 75:
            return f"Command '{string}' is not found."
        return f"Command '{string}' is not found. Did you mean `{match}`?"


def setup(_):
    bot.help_command = CustomHelpCommand()


def teardown(_):
    bot.help_command = None
