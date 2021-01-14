import discord
from discord.ext import commands
import polaroid
from io import BytesIO
import typing


class ImageManip(commands.Cog):
    """
    Image manipulation commands. Powered by [polaroid](https://github.com/Daggy1234/polaroid).
    """
    @staticmethod
    async def get_img(ctx, img: typing.Union[discord.PartialEmoji, discord.Member, None]):
        """
        Helper function to get the image.
        """
        if ctx.message.attachments:
            return polaroid.Image(await ctx.message.attachments[0].read())
        elif isinstance(img, discord.PartialEmoji):
            return polaroid.Image(await img.url.read())
        else:
            img = img or ctx.author
            return polaroid.Image(await img.avatar_url_as(format="png").read())

    @staticmethod
    def build_embed(ctx, img: polaroid.Image, *, time_taken: float, filename: str):
        """
        Helper function to build the embed.
        """
        file = discord.File(fp=BytesIO(img.save_bytes()), filename=f"{filename}.png")
        embed = discord.Embed(colour=ctx.bot.embed_colour)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        embed.set_image(url=f"attachment://{filename}.png")
        embed.set_footer(text=f"Finished in {time_taken:.3f} seconds")
        return embed, file

    @commands.command()
    async def solarize(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Solarize an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.solarize()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="solarize")
            await ctx.send(embed=embed, file=file)

    @commands.command()
    async def greyscale(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Greyscale an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.grayscale()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="greyscale")
            await ctx.send(embed=embed, file=file)

    @commands.command(aliases=["colorize"])
    async def colourize(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Enhances the colour in an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.colorize()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="colourize")
            await ctx.send(embed=embed, file=file)

    @commands.command()
    async def noise(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Adds noise to an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.add_noise_rand()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="noise")
            await ctx.send(embed=embed, file=file)

    @commands.command()
    async def rainbow(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Adds colour to an image and makes it more vibrant.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.apply_gradient()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="rainbow")
            await ctx.send(embed=embed, file=file)

    @commands.command()
    async def desaturate(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Desaturates an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.desaturate()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="desaturate")
            await ctx.send(embed=embed, file=file)

    @commands.command(aliases=["enhanceedges", "enhance-edges", "enhance-e"])
    async def enhance_edges(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Enhances the edges in an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.edge_detection()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="enhance-edges")
            await ctx.send(embed=embed, file=file)

    @commands.command()
    async def emboss(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Adds an emboss-like effect to an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.emboss()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="emboss")
            await ctx.send(embed=embed, file=file)

    @commands.command()
    async def invert(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Inverts the colours in an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.invert()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="invert")
            await ctx.send(embed=embed, file=file)

    @commands.command(aliases=["pinknoise", "pink-noise"])
    async def pink_noise(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Adds pink noise to an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.pink_noise()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="pink-noise")
            await ctx.send(embed=embed, file=file)

    @commands.command()
    async def sepia(self, ctx, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Adds a brown tint to an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                img = await self.get_img(ctx, image)
                img.sepia()
            embed, file = self.build_embed(ctx, img, time_taken=sw.elapsed, filename="sepia")
            await ctx.send(embed=embed, file=file)


def setup(bot):
    bot.add_cog(ImageManip())
