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
    async def do_img_manip(ctx, image, *, method: str, filename: str, method_args: list = None, method_kwargs: dict = None):
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                # get the image
                if ctx.message.attachments:
                    img = polaroid.Image(await ctx.message.attachments[0].read())
                elif isinstance(image, discord.PartialEmoji):
                    img = polaroid.Image(await image.url.read())
                else:
                    img = image or ctx.author
                    img = polaroid.Image(await img.avatar_url_as(format="png").read())
                # manipulate the image
                if method_args is None:
                    method_args = []
                if method_kwargs is None:
                    method_kwargs = {}
                method = getattr(img, method)
                method(*method_args, **method_kwargs)
            # build and send the embed
            file = discord.File(BytesIO(img.save_bytes()), filename=f"{filename}.png")
            embed = discord.Embed(colour=ctx.bot.embed_colour)
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            embed.set_image(url=f"attachment://{filename}.png")
            embed.set_footer(text=f"Finished in {sw.elapsed:.3f} seconds")
            await ctx.send(embed=embed, file=file)

    @commands.command()
    async def solarize(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Solarize an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="solarize", filename="solarize")

    @commands.command()
    async def greyscale(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Greyscale an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="grayscale", filename="greyscale")

    @commands.command(aliases=["colorize"])
    async def colourize(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Enhances the colour in an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="colorize", filename="colourize")

    @commands.command()
    async def noise(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Adds noise to an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="add_noise_rand", filename="noise")

    @commands.command()
    async def rainbow(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        🌈

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="apply_gradient", filename="rainbow")

    @commands.command()
    async def desaturate(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Desaturates an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="desaturate", filename="desaturate")

    @commands.command(aliases=["enhanceedges", "enhance-edges", "enhance-e"])
    async def enhance_edges(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Enhances the edges in an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="edge_detection", filename="enhance-edges")

    @commands.command()
    async def emboss(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Adds an emboss-like effect to an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="emboss", filename="emboss")

    @commands.command()
    async def invert(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Inverts the colours in an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="invert", filename="invert")

    @commands.command(aliases=["pinknoise", "pink-noise"])
    async def pink_noise(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Adds pink noise to an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="pink_noise", filename="pink-noise")

    @commands.command()
    async def sepia(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member] = None):
        """
        Adds a brown tint to an image.

        `image` - The image. Can be a user (for their avatar), an emoji or an attachment. Defaults to your avatar.
        """
        await self.do_img_manip(ctx, image, method="sepia", filename="sepia")


def setup(bot):
    bot.add_cog(ImageManip())
