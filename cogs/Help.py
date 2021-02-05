import discord
from discord.ext import commands, menus
import difflib
from contextlib import suppress


class PaginatedHelpCommand(menus.MenuPages):
    """
    Paginated help command.
    """
    @menus.button('\U00002139', position=menus.Last(2))
    async def on_info(self, _):
        embed = discord.Embed(title="How to Use the Paginator", color=self.ctx.bot.embed_colour)
        embed.add_field(name="Add and Remove Reactions to Navigate the Help Menu:",
                        value=
                        "➡️ next page\n"
                        "⬅️ previous page\n"
                        "⏮️ first page\n"
                        "⏭️ last page\n"
                        "ℹ️ shows this message\n"
                        "❔    shows how to read the bot's signature\n"
                        "⏹️ closes the paginator")
        embed.set_thumbnail(url=self.ctx.bot.user.avatar_url)
        embed.set_footer(text=f"You were on page {self.current_page + 1} before this message.")
        await self.message.edit(embed=embed)

    @menus.button('\U00002754', position=menus.Last(3))
    async def on_question_mark(self, _):
        embed = discord.Embed(
            title="How to read the Bot's Signature",
            description=
            "`<argument>`: required argument\n"
            "`[argument]`: optional argument (These arguments will usually have an '=' followed by their default value.)\n"
            "`argument...`: multiple arguments can be provided",
            color=self.ctx.bot.embed_colour)
        embed.set_thumbnail(url=self.ctx.bot.user.avatar_url)
        embed.set_footer(text=f"You were on page {self.current_page + 1} before this message.")
        await self.message.edit(embed=embed)

    @menus.button('\N{BLACK SQUARE FOR STOP}\ufe0f', position=menus.Last(4))
    async def end_menu(self, _):
        self.stop()


class CustomHelpCommand(commands.HelpCommand):
    """
    Custom help command.
    """
    async def send_bot_help(self, _):
        data = {0: None}
        data.update({num: cog_pair for num, cog_pair in enumerate(self.context.bot.cogs.items(), start=1)})
        pages = PaginatedHelpCommand(source=self.context.bot.utils.HelpSource(data), clear_reactions_after=True)
        # try:
        #     user = await self.context.author.create_dm()
        #     await pages.start(self.context, channel=user)
        # except discord.Forbidden:
        #     confirm = await Confirm("Your DMs are off. Do you want me to send help in this channel?").prompt(self.context)
        #     if confirm:
        #         await pages.start(self.context)
        await pages.start(self.context)
        with suppress(discord.HTTPException):
            await self.context.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    async def send_command_help(self, command):
        embed = discord.Embed(title=f"Help on Command `{command.name}`",
                              description=command.help or "No info available.",
                              colour=self.context.bot.embed_colour)
        embed.add_field(name="Signature:", value=f"{command.name} {command.signature}", inline=False)
        embed.add_field(name="Category:", value=f"{command.cog_name}", inline=False)
        try:
            can_run = await command.can_run(self.context)
            if can_run:
                can_run = self.context.bot.emoji_dict["green_tick"]
            else:
                can_run = self.context.bot.emoji_dict["red_tick"]
        except commands.CommandError:
            can_run = self.context.bot.emoji_dict["red_tick"]
        embed.add_field(name="Can Use:", value=can_run)
        embed.add_field(name="Aliases:", value="\n".join(command.aliases) or "None", inline=False)
        embed.set_thumbnail(url=self.context.bot.user.avatar_url)
        embed.set_footer(
            text=f"Type {self.context.clean_prefix}help (command) for more info on a command.\n"
            f"You can also type {self.context.clean_prefix}help (category) for more info on a category.")
        return await self.context.send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title=f"Help on Category `{cog.qualified_name}`",
                              description=cog.description or "No info available.",
                              colour=self.context.bot.embed_colour)
        embed.add_field(name="Commands in this Category:", value="\n".join(str(command) for command in cog.get_commands()) or "None")
        embed.set_thumbnail(url=self.context.bot.user.avatar_url)
        embed.set_footer(
            text=f"Type {self.context.clean_prefix}help (command) for more info on a command.\n"
            f"You can also type {self.context.clean_prefix}help (category) for more info on a category.")
        return await self.context.send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=f"Help on Command Group `{group.name}`",
                              description=group.help or "No info available.",
                              colour=self.context.bot.embed_colour)
        embed.add_field(name="Signature:", value=f"{group.name} {group.signature}", inline=False)
        embed.add_field(name="Category:", value=f"{group.cog_name}", inline=False)
        try:
            can_run = await group.can_run(self.context)
            if can_run:
                can_run = self.context.bot.emoji_dict["green_tick"]
            else:
                can_run = self.context.bot.emoji_dict["red_tick"]
        except commands.CommandError:
            can_run = self.context.bot.emoji_dict["red_tick"]
        embed.add_field(name="Can Use:", value=can_run)
        embed.add_field(name="Aliases:", value="\n".join(group.aliases) or "None", inline=False)
        embed.add_field(name="Commands in this Group:", value="\n".join(str(command) for command in group.walk_commands()) or "None")
        embed.set_thumbnail(url=self.context.bot.user.avatar_url)
        embed.set_footer(
            text=f"Type {self.context.clean_prefix}help (command) for more info on a command.\n"
            f"You can also type {self.context.clean_prefix}help (category) for more info on a category.")
        return await self.context.send(embed=embed)

    async def command_not_found(self, string):
        matches = difflib.get_close_matches(string, self.context.bot.command_list)
        if not matches:
            return f"Command '{string}' is not found."
        return f"Command '{string}' is not found. Did you mean `{matches[0]}`?"


def setup(bot):
    bot.help_command = CustomHelpCommand()


def teardown(bot):
    bot.help_command = None
