import discord
from discord.ext import commands, menus
import humanize
import datetime
from collections import Counter

from dependencies import bot


class DiscordStatusSource(menus.ListPageSource):
    def __init__(self, summary, response):
        super().__init__(range(6), per_page=1)
        self.summary = summary
        self.response = response

    important_components = ("API", "Media Proxy", "Push Notifications", "Search", "Voice", "Third-party", "CloudFlare")

    def format_page(self, menu: menus.MenuPages, page):
        # 0: general
        # 1: component overview
        # 2: most recent incident
        # 3-5: month incidents
        # 6+: maintenance info?
        if menu.current_page == 0:  # general (n/n systems operational)
            all_components = [component for component in self.summary["components"] if component['name'] in DiscordStatusSource.important_components]
            operational = [component for component in all_components if component["status"] == "operational"]
            embed = discord.Embed(title="Discord Status\nCurrent Status for Discord",
                                  description=f"**{self.summary['status']['description']}**\n" \
                                            f"**Impact**: `{self.summary['status']['indicator'].title()}`\n" \
                                            f"**Components Operational**: `{len(operational)}/{len(all_components)}`")
        elif menu.current_page == 1:  # most recent incident
            embed = discord.Embed(title="Discord Status\nCurrent Incidents",)
            if not self.summary["incidents"]:
                embed.description = "There are no issues with discord as of yet."
            else:
                for incident in self.summary['incidents']:
                    embed.add_field(name=incident["name"], value=f"{incident['message']}\n**Impact**: `{incident['impact']}`")
        elif menu.current_page == 2:  # component overview
            embed = discord.Embed(title="Discord Status\nComponent Overview")
            for component in self.summary["components"]:
                if component['name'] in DiscordStatusSource.important_components:
                    embed.add_field(name=component['name'],
                                    value=f"{component['description'] if component['description'] else 'No Description'}\n**Status**: `{component['status'].title()}`",
                                    inline=False)
        elif menu.current_page in (3, 4, 5):
            month_data = self.response["months"][menu.current_page - 3]
            embed = discord.Embed(title=f"Discord Status\nIncidents for {month_data['name']} {month_data['year']}")
            if len(month_data['incidents']) == 0:
                embed.description = "There are no incidents this month."
            else:
                for incident in month_data['incidents']:
                    embed.add_field(name=incident["name"], value=f"{incident['message']}\n**Impact**: `{incident['impact']}`")
        embed.colour = bot.embed_colour
        embed.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")
        return embed
        # todo maintenance info?


class Info(commands.Cog):
    @commands.command(
        aliases=["av"]
    )
    async def avatar(self, ctx, *, member: discord.Member = None):
        """
        Returns the avatar and avatar url of a member.

        `member` - The member whose avatar you would like to view. Defaults to you.
        """
        member = member or ctx.author
        embed = discord.Embed(title=f"{member}'s avatar", description=f"[Open original]({member.avatar_url})",
                              colour=bot.embed_colour)
        embed.set_image(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(
        aliases=["si", "gi", "server_info", "guild_info", "guildinfo"]
    )
    async def serverinfo(self, ctx):
        """
        Displays information about the current server.
        """
        animated_emojis = [emoji for emoji in ctx.guild.emojis if emoji.animated]
        not_animated_emojis = [emoji for emoji in ctx.guild.emojis if not emoji.animated]

        member_statuses = Counter([member.status for member in ctx.guild.members])

        try:
            bans = len(await ctx.guild.bans())
        except discord.Forbidden:
            bans = "I do not have the necessary permissions to access ban info."

        embed = discord.Embed(title=f"Server info for {ctx.guild}",
        description= \
        f"**Description**: {ctx.guild.description or 'No description'}\n"
        f"**ID**: {ctx.guild.id}\n"
        f"**Owner**: {ctx.guild.owner}\n"
        f"**Owner ID**: {ctx.guild.owner.id}", colour=bot.embed_colour)

        embed.add_field(name="General", value= \
        f"**Members**: {member_statuses[discord.Status.online]} <:online:787461591968645130> {member_statuses[discord.Status.idle]} <:idle:787461645038256149> {member_statuses[discord.Status.do_not_disturb]} <:dnd:787461694455808070> {member_statuses[discord.Status.offline]} <:offline:787461784318902303> ({len(ctx.guild.members)} total)\n"
        f"**Channels**: {len(ctx.guild.text_channels)} <:text_channel:787461133963231263> {len(ctx.guild.voice_channels)} <:voice_channel:787460989409951757> ({len(ctx.guild.channels)} total)\n"
        f"**Categories**: {len(ctx.guild.categories)}\n"
        f"**Region**: {ctx.guild.region}\n"
        f"**Verification Level**: {ctx.guild.verification_level}\n"
        f"**Roles**: {len(ctx.guild.roles)}\n"
        f"**Bans**: {bans}"
        , inline=False)

        embed.add_field(name="Server Boost", value= \
        f"Level {ctx.guild.premium_tier}\n"
        f"{ctx.guild.premium_subscription_count} boost(s)\n"
        f"{len(ctx.guild.premium_subscribers)} booster(s)"
        ,  inline=False)

        embed.add_field(name="Emojis", value= \
        f"**Total**: {len(ctx.guild.emojis)}/{ctx.guild.emoji_limit}\n"
        f"**Static**: {len(not_animated_emojis)}\n"
        f"**Animated**: {len(animated_emojis)}"
        ,  inline=False)

        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.set_footer(text=f"Created {humanize.precisedelta(datetime.datetime.now() - ctx.guild.created_at)} ago")
        await ctx.send(embed=embed)

    @commands.command(aliases=["discord_status", "dstatus"])
    async def discordstatus(self, ctx):
        """
        View the current status of discord. Source: https://discordstatus.com
        """
        async with ctx.typing():
            async with bot.session.get("https://srhpyqt94yxb.statuspage.io/api/v2/summary.json") as response:
                summary = await response.json()
            async with bot.session.get("https://discordstatus.com/history.json") as response:
                response = await response.json()
            await menus.MenuPages(DiscordStatusSource(summary, response), clear_reactions_after=True).start(ctx)

    @commands.guild_only()
    @commands.command(aliases=["perms"])
    async def permissions(self, ctx, *, member: discord.Member=None):
        """
        Display the permissions of a member.

        `member` - The member whose permissions you would like to view. Defaults to you.
        """
        member = member or ctx.author
        perms = []
        for perm, value in member.permissions_in(ctx.channel):
            value = "<:green_tick:795827014300598272>" if value else "<:red_tick:795827295541133372>"
            perms.append(f"{value} {perm.replace('_', ' ').replace('guild', 'server')}")
        embed = discord.Embed(title=f"Permissions for {member} in {ctx.channel}", description="\n".join(perms), colour=bot.embed_colour)
        await ctx.send(embed=embed)

    @commands.command()
    async def define(self, ctx, *, word):
        """
        Search up the definition of a word. Source: https://dictionaryapi.dev/

        `word` - The word to search up.
        """
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        async with bot.session.get(url) as r:
            response = await r.json()
        if isinstance(response, dict):
            return await ctx.send("Sorry pal, I couldn't find definitions for the word you were looking for.")
        await menus.MenuPages(self.DefineSource(response[0]["meanings"], response[0]), clear_reactions_after=True).start(ctx)

    class DefineSource(menus.ListPageSource):
        def __init__(self, data, response):
            super().__init__(data, per_page=1)
            self.response = response

        async def format_page(self, menu, page):
            embed = discord.Embed(title=f"Definitions for word `{self.response['word']}`",
                        description= \
                        f"{self.response['phonetics'][0]['text']}\n"
                        f"[audio]({self.response['phonetics'][0]['audio']})",
                        colour=bot.embed_colour)
            defs = []
            for definition in page["definitions"]:
                defs.append(f"**Definition:** {definition['definition']}\n**Example:** {definition.get('example', 'None')}")
            embed.add_field(name=f"`{page['partOfSpeech']}`", value="\n\n".join(defs))
            return embed


def setup(_):
    bot.add_cog(Info())
