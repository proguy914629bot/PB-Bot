import discord
from discord.ext import commands, menus
import wavelink
import humanize
import datetime
from contextlib import suppress

from dependencies import CustomContext
from config import config


class Track(wavelink.Track):
    """
    Custom track object with a requester attribute.
    """
    __slots__ = ("requester",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requester = kwargs.get("requester")


class Player(wavelink.Player):
    """
    Custom player class.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.now_playing = None
        self.session_started = False
        self.session_chan = None

        self.queue = []
        self.menus = []
        self.volume = 40
        self.queue_position = 0

    async def start(self, ctx):
        self.session_chan = ctx.channel
        await ctx.invoke(ctx.bot.get_command("connect"))
        self.session_started = True
        await self.do_next()

    async def do_next(self):
        with suppress((discord.Forbidden, discord.HTTPException, AttributeError)):
            await self.now_playing.delete()

        try:
            song = self.queue[self.queue_position]
        except IndexError:  # There are no more songs in the queue.
            await self.destroy()
            return

        self.queue_position += 1

        embed = discord.Embed(title="Now Playing:", description=f"{song}", colour=self.bot.embed_colour)
        embed.set_footer(text=f"Requested by {song.requester}")
        self.now_playing = await self.session_chan.send(embed=embed)
        await self.play(song)

    async def do_previous(self):
        self.queue_position -= 2
        await self.stop()

    async def destroy(self):
        with suppress((discord.Forbidden, discord.HTTPException, AttributeError)):
            await self.now_playing.delete()

        menus_ = self.menus.copy()
        for menu in menus_:
            menu.stop()

        await super().destroy()


# def dj_check():
#     async def predicate(ctx):
#         if ctx.controller.current_dj is None:  # no dj yet
#             ctx.controller.current_dj = ctx.author
#             return True
#         if ctx.controller.current_dj == ctx.author:
#             return True
#         await ctx.send(f"Only the current DJ ({ctx.controller.current_dj}) can control the current guild's player.")
#         return False
#     return commands.check(predicate)


def is_playing():
    async def predicate(ctx):
        if not ctx.player.is_playing:
            await ctx.send("I am not currently playing anything.")
            return False
        return True
    return commands.check(predicate)

# Controls:

# skip/previous
# play/pause
# volume up/down
# songqueue add/remove
# fastforward
# rewind


class Music(commands.Cog):
    """
    Music commands.
    """
    def __init__(self, bot):
        @property
        def get_player(ctx):
            return bot.wavelink.get_player(ctx.guild.id, cls=Player)

        CustomContext.player = get_player
        self.bot = bot
        bot.loop.create_task(self.start_nodes())

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage
        if not ctx.bot.wavelink.nodes:
            await ctx.send("Music commands aren't ready yet. Try again in a bit.")
            return False
        if not ctx.player.is_connected:  # anyone can use commands if the bot isn't connected to a voice channel
            return True
        if not ctx.author.voice:  # not in a voice channel
            await ctx.send("You must be in a voice channel to use this command.")
            return False
        if ctx.author.voice.channel.id != ctx.player.channel_id:  # in a voice channel, but not in the same one as the bot
            await ctx.send("You must be in the same voice channel as me to use this command.")
            return False
        return True

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        if self.bot.wavelink.nodes:
            previous_nodes = self.bot.wavelink.nodes.copy()
            for node in previous_nodes.values():
                await node.destroy()

        node = await self.bot.wavelink.initiate_node(**config["wavelink_node"])
        node.set_hook(self.on_node_event)

    async def on_node_event(self, event):
        if isinstance(event, (wavelink.TrackEnd, wavelink.TrackException)):
            await event.player.do_next()

    # @commands.Cog.listener()
    # async def on_voice_state_update(self, member, before, after):
    #     if before.channel and not after.channel:  # the member was in a vc and the member left the vc
    #         try:
    #             controller = bot.controllers[member.guild.id]
    #         except KeyError:  # there is no controller for the guild. Therefore there is no dj to check for.
    #             return
    #         if controller.current_dj == member:  # the member was the current dj for the controller for that guild
    #             controller.current_dj = None

    @commands.command()
    async def connect(self, ctx, *, voice_channel: discord.VoiceChannel = None):
        """
        Connects the bot to a voice channel.

        `voice_channel` - The voice channel to connect to. If no voice channel is provided, the bot will try to connect to the voice channel the user is currently in.
        """
        if not voice_channel:
            try:
                voice_channel = ctx.author.voice.channel
            except AttributeError:
                return await ctx.send("Couldn't find a channel to join. Please specify a valid channel or join one.")
        await ctx.player.connect(voice_channel.id)
        await ctx.send(f"Connected to **`{voice_channel.name}`**.")

    @is_playing()
    @commands.command()
    async def player(self, ctx):
        """
        Opens up the player menu.
        """
        await ctx.bot.utils.PlayerMenu(delete_message_after=True).start(ctx)

    @commands.group(invoke_without_command=True, aliases=["sq"])
    async def songqueue(self, ctx, limit: int = None):
        """
        View the songqueue.

        `limit` - The amount of songs to get from the queue. Fetches all songs if this is not provided.
        """
        if limit is None:
            source = [(number, track) for number, track in enumerate(ctx.player.queue, start=1)]
        else:
            source = [(number, track) for number, track in enumerate(ctx.player.queue[:limit], start=1)]
        await menus.MenuPages(ctx.bot.utils.QueueSource(source, ctx.player)).start(ctx)

    @songqueue.command()
    async def add(self, ctx, *, query: str):
        """
        Alias to `play`.
        """
        await ctx.invoke(ctx.bot.get_command("play"), query=query)

    @songqueue.command()
    async def remove(self, ctx, *, query: str):
        """
        Removes a song from the queue.

        `query` - The song to remove from the queue.
        """
        query_results = await ctx.bot.wavelink.get_tracks(f"ytsearch:{query}")
        if not query_results:
            return await ctx.send(f"Could not find any songs with that query.")
        track = Track(query_results[0].id, query_results[0].info, requester=ctx.author)
        for track_, position in enumerate(ctx.player.queue):
            if str(track_) == str(track):
                ctx.player.queue.remove(track_)
                if position < ctx.player.queue_position:
                    ctx.player.queue_position -= 1
        await ctx.send(f"Removed all songs with the name `{track}` from the queue. Queue length: `{len(ctx.player.queue)}`")

    @commands.command()
    async def play(self, ctx, *, query: str):
        """
        Adds a song to the queue.

        `query` - The song to add to the queue.
        """
        if len(ctx.player.queue) >= 100:
            return await ctx.send("Sorry, only `100` songs can be in the queue at a time.")

        query_results = await ctx.bot.wavelink.get_tracks(f"ytsearch:{query}")
        if not query_results:
            return await ctx.send(f"Could not find any songs with that query.")

        if isinstance(query_results, wavelink.TrackPlaylist):
            for track in query_results.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                ctx.player.queue.append(track)
            await ctx.send(f"Added playlist `{query_results.data['playlistInfo']['name']}` with `{len(query_results.tracks)}` songs to the queue. Queue length: `{len(ctx.player.queue)}`")
        else:
            track = Track(query_results[0].id, query_results[0].info, requester=ctx.author)
            ctx.player.queue.append(track)
            await ctx.send(f"Added `{track}` to the queue. Queue length: `{len(ctx.player.queue)}`")

        if not ctx.player.session_started:
            await ctx.player.start(ctx)

    @is_playing()
    @commands.command()
    async def resume(self, ctx):
        """
        Resumes the player.
        """
        if not ctx.player.is_paused:
            return await ctx.send("I am already playing!")
        await ctx.player.set_pause(False)
        await ctx.send("Resuming...")

    @is_playing()
    @commands.command()
    async def pause(self, ctx):
        """
        Pauses the player.
        """
        if ctx.player.is_paused:
            return await ctx.send("I am already paused!")
        await ctx.player.set_pause(True)
        await ctx.send("Paused the player.")

    @is_playing()
    @commands.command()
    async def skip(self, ctx):
        """
        Skips the currently playing song.
        """
        await ctx.player.stop()
        await ctx.message.add_reaction("✅")

    @is_playing()
    @commands.command()
    async def previous(self, ctx):
        """
        Stops the currently playing song and plays the previous one.
        """
        await ctx.player.do_previous()
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def volume(self, ctx, volume: int = None):
        """
        Adjusts the players volume.

        `volume` - The new volume.
        """
        if volume is None:
            return await ctx.bot.utils.VolumeMenu(delete_message_after=True).start(ctx)
        volume = max(min(volume, 1000), 0)
        await ctx.player.set_volume(volume)
        await ctx.send(f"Set the volume to `{volume}`.")

    @is_playing()
    @commands.command(aliases=["eq", "setequalizer", "seteq"])
    async def equalizer(self, ctx, *, equalizer: str):
        """
        Change the players equalizer.

        `equalizer` - The new equalizer. Available equalizers:

        `flat` - Resets the equalizer to flat.
        `boost` - Boost equalizer. This equalizer emphasizes punchy bass and crisp mid-high tones. Not suitable for tracks with deep/low bass.
        `metal` - Experimental metal/rock equalizer. Expect clipping on bassy songs.
        `piano` - Piano equalizer. Suitable for piano tracks, or tacks with an emphasis on female vocals. Could also be used as a bass cutoff.
        **Source:** https://wavelink.readthedocs.io/en/latest/wavelink.html#equalizer
        """
        equalizers = {
            "flat": wavelink.Equalizer.flat(),
            "boost": wavelink.Equalizer.boost(),
            "metal": wavelink.Equalizer.metal(),
            "piano": wavelink.Equalizer.piano()
        }
        equalizer = equalizer.lower()
        try:
            eq = equalizers[equalizer]
        except KeyError:
            eqs = "\n".join(equalizers)
            return await ctx.send(f"Invalid equalizer provided. Available equalizers:\n\n{eqs}")
        await ctx.player.set_eq(eq)
        await ctx.send(f"Set the equalizer to `{equalizer}`.")

    @is_playing()
    @commands.command(aliases=["fastfwd"])
    async def fastforward(self, ctx, seconds: int):
        """
        Fast forward `x` seconds into the current song.

        `seconds` - The amount of seconds to fast forward.
        """
        seek_position = ctx.player.position + (seconds * 1000)
        await ctx.player.seek(seek_position)
        await ctx.send(f"Fast forwarded `{seconds}` seconds. Current position: `{humanize.precisedelta(datetime.timedelta(milliseconds=seek_position))}`")

    @is_playing()
    @commands.command()
    async def rewind(self, ctx, seconds: int):
        """
        Rewind `n` seconds.

        `seconds` - The amount of seconds to rewind.
        """
        seek_position = ctx.player.position - (seconds * 1000)
        await ctx.player.seek(seek_position)
        await ctx.send(f"Rewinded `{seconds}` seconds. Current position: `{humanize.precisedelta(datetime.timedelta(milliseconds=seek_position))}`")

    @commands.command(aliases=["dc"])
    async def disconnect(self, ctx):
        """
        Disconnects the bot from the voice channel and stops the player.
        """
        channel = ctx.guild.get_channel(ctx.player.channel_id)
        await ctx.player.destroy()
        await ctx.send(f"Disconnected from **`{channel}`**.")


def setup(bot):
    bot.add_cog(Music(bot)) #add cog
