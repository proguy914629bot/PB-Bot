import discord
from discord.ext import commands, menus
import humanize
import datetime
from collections import Counter
import json


class Info(commands.Cog):
    """
    Information commands.
    """
    @commands.command(aliases=["av"])
    async def avatar(self, ctx, *, member: discord.Member = None):
        """
        Returns the avatar and avatar url of a member.

        `member` - The member whose avatar you would like to view. Defaults to you.
        """
        member = member or ctx.author
        embed = discord.Embed(title=f"{member}'s avatar", description=f"[Open original]({member.avatar_url})",
                              colour=ctx.bot.embed_colour)
        embed.set_image(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(aliases=["si", "gi", "server_info", "guild_info", "guildinfo"])
    async def serverinfo(self, ctx):
        """
        Displays information about this server.
        """
        animated_emojis = list(filter(lambda emoji: emoji.animated, ctx.guild.emojis))
        not_animated_emojis = list(filter(lambda emoji: not emoji.animated, ctx.guild.emojis))

        member_statuses = Counter([member.status for member in ctx.guild.members])

        try:
            bans = len(await ctx.guild.bans())
        except discord.Forbidden:
            bans = "I do not have the necessary permissions to access ban info."

        embed = discord.Embed(
            title=f"Server info for {ctx.guild}",
            description=
            f"**Description**: {ctx.guild.description or 'No description'}\n"
            f"**ID**: {ctx.guild.id}\n"
            f"**Owner**: {ctx.guild.owner}\n"
            f"**Owner ID**: {ctx.guild.owner.id}",
            colour=ctx.bot.embed_colour)

        embed.add_field(
            name="General",
            value=
            f"**Members**: {member_statuses[discord.Status.online]} {ctx.bot.emoji_dict['online']} {member_statuses[discord.Status.idle]} {ctx.bot.emoji_dict['idle']} {member_statuses[discord.Status.do_not_disturb]} {ctx.bot.emoji_dict['dnd']} {member_statuses[discord.Status.offline]} {ctx.bot.emoji_dict['offline']} ({len(ctx.guild.members)} total)\n"
            f"**Channels**: {len(ctx.guild.text_channels)} {ctx.bot.emoji_dict['text_channel']} {len(ctx.guild.voice_channels)} {ctx.bot.emoji_dict['voice_channel']} ({len(ctx.guild.channels)} total)\n"
            f"**Categories**: {len(ctx.guild.categories)}\n"
            f"**Region**: {ctx.guild.region}\n"
            f"**Verification Level**: {ctx.guild.verification_level}\n"
            f"**Roles**: {len(ctx.guild.roles)}\n"
            f"**Bans**: {bans}",
            inline=False)

        embed.add_field(
            name="Server Boost",
            value=
            f"Level {ctx.guild.premium_tier}\n"
            f"{ctx.guild.premium_subscription_count} boost(s)\n"
            f"{len(ctx.guild.premium_subscribers)} booster(s)",
            inline=False)

        embed.add_field(
            name="Emojis",
            value=
            f"**Total**: {len(ctx.guild.emojis)}/{ctx.guild.emoji_limit}\n"
            f"**Static**: {len(not_animated_emojis)}\n"
            f"**Animated**: {len(animated_emojis)}",
            inline=False)

        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.set_footer(text=f"Created {humanize.precisedelta(datetime.datetime.now() - ctx.guild.created_at)} ago")
        await ctx.send(embed=embed)

    @commands.command(aliases=["dstatus"], usage="[-h|--history]")
    async def discordstatus(self, ctx, *flags):
        """
        View the current status of discord. Source: https://discordstatus.com

        **Flags:**
        `-h|--history` - If this flag is provided, historical data will be shown instead.
        """
        async with ctx.typing():
            if "-h" in flags or "--history" in flags:
                async with ctx.bot.session.get("https://srhpyqt94yxb.statuspage.io/api/v2/incidents.json") as r:
                    incidents = (await r.json())["incidents"]
                return await menus.MenuPages(ctx.bot.utils.HistorySource(incidents, per_page=1), clear_reactions_after=True).start(ctx)

            async with ctx.bot.session.get("https://srhpyqt94yxb.statuspage.io/api/v2/summary.json") as r:
                summary = await r.json()

            # embed 1
            embed1 = discord.Embed(
                title="Discord Status\nCurrent Status for Discord",
                description="```yaml\n"
                            f"Message: {summary['status']['description']}\n"
                            f"Impact: {summary['status']['indicator'].title()}\n"
                            "```",
                colour=ctx.bot.embed_colour
            )

            # embed 2
            embed2 = discord.Embed(title="Discord Status\nCurrent Incidents", colour=ctx.bot.embed_colour)
            if not summary["incidents"]:
                embed2.description = "```yaml\nThere are no issues with discord as of yet.```"
            else:
                embed2.description = "```yaml\n" + "\n\n".join(
                    f"Name: {incident.get('name', None)}\n"
                    f"Message: {incident.get('message', None)}\n"
                    f"Status: {incident.get('status', None).title()}\n"
                    f"Impact: {incident.get('impact', None).title()}" for incident in summary["incidents"]
                ) + "```"

            # embed 3
            components = {c["name"]: c["status"].title().replace("_", " ") for c in summary["components"]}
            embed3 = discord.Embed(
                title="Discord Status\nComponents",
                description="```yaml\n" + "\n".join(f"{k.rjust(len(max(components.keys(), key=len)))}: {v}" for k, v in components.items()) + "```",
                colour=ctx.bot.embed_colour)

            await menus.MenuPages(ctx.bot.utils.DiscordStatusSource([embed1, embed2, embed3], per_page=1), clear_reactions_after=True).start(ctx)

    @commands.guild_only()
    @commands.command(aliases=["perms"])
    async def permissions(self, ctx, *, member: discord.Member = None):
        """
        Display the permissions of a member.

        `member` - The member whose permissions you would like to view. Defaults to you.
        """
        member = member or ctx.author
        perms = list(member.permissions_in(ctx.channel))
        split_perms = [perms[x:x+12] for x in range(0, len(perms), 12)]
        embed = discord.Embed(title=f"Permissions for `{member}` in `{ctx.channel}`", colour=ctx.bot.embed_colour)
        for li in split_perms:
            field_perms = []
            for perm, value in li:
                v = f"{ctx.bot.emoji_dict['xoff']}{ctx.bot.emoji_dict['tickon']}" \
                    if value else f"{ctx.bot.emoji_dict['xon']}{ctx.bot.emoji_dict['tickoff']}"
                field_perms.append(f"{v} {perm.replace('_', ' ').replace('guild', 'server')}")
            embed.add_field(name="\u200b", value="\n".join(field_perms))
        await ctx.send(embed=embed)

    @commands.command()
    async def define(self, ctx, *, word):
        """
        Search up the definition of a word. Source: https://dictionaryapi.dev/

        `word` - The word to search up.
        """
        async with ctx.typing():
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            async with ctx.bot.session.get(url) as r:
                response = await r.json()
            if isinstance(response, dict):
                return await ctx.send("Sorry pal, I couldn't find definitions for the word you were looking for.")
            await menus.MenuPages(ctx.bot.utils.DefineSource(response[0]["meanings"], response[0]), clear_reactions_after=True).start(ctx)

    @commands.command(aliases=["ui"])
    async def userinfo(self, ctx, *, member: discord.Member = None):
        """
        Get the userinfo for a member.

        `member` - The member. Defaults to you.
        """
        member = member or ctx.author
        embed = discord.Embed(title=f"Userinfo for {member}", colour=member.colour)
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(
            name="General",
            value=
            f"**Full Name:** {member}\n"
            f"**ID:** {member.id}\n"
            f"**Nickname:** {member.nick}\n"
            f"**Display Name:** {member.display_name}\n"
            f"**Bot:** {ctx.bot.emoji_dict['green_tick'] if member.bot else ctx.bot.emoji_dict['red_tick']}",
            inline=False)
        activity = f"{str(member.activity.type).split('.')[1].title()} {member.activity.name}" if member.activity else "None"
        embed.add_field(
            name="Presence Info",
            value=
            f"**Status:** {ctx.bot.emoji_dict[member.raw_status]}\n"
            f"**Activity:** {activity}", inline=False)
        embed.add_field(
            name="Guild Info",
            value=
            f"**Joined:** {humanize.naturaldate(member.joined_at)} ({humanize.precisedelta(datetime.datetime.now() - member.joined_at)} ago)\n"
            f"**Top Role:** {member.top_role.mention}\n"
            f"**Roles:** {ctx.bot.utils.humanize_list([role.mention for role in member.roles[1:]]) or 'None'}",
            inline=False)
        embed.set_footer(text=f"Created {humanize.precisedelta(datetime.datetime.now() - member.created_at)} ago")
        await ctx.send(embed=embed)

    @commands.command(aliases=["rawmessage", "rawmsg"])
    async def raw_message(self, ctx, *, message: discord.Message = None):
        """
        Get the raw info for a message.

        `message` - The message.
        """
        message = message or ctx.message

        try:
            msg = await ctx.bot.http.get_message(ctx.channel.id, message.id)
        except discord.NotFound:
            return await ctx.send("Sorry, I couldn't find that message.")

        raw = json.dumps(msg, indent=4)
        if len(raw) > 1989:
            return await ctx.send(f"Content was too long: {await ctx.bot.mystbin(raw)}")
        await ctx.send(f"```json\n{raw}```")


def setup(bot):
    bot.add_cog(Info())
