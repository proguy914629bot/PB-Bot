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
    async def get_image(ctx, image):
        if ctx.message.attachments:
            return polaroid.Image(await ctx.message.attachments[0].read())
        elif isinstance(image, discord.PartialEmoji):
            return polaroid.Image(await image.url.read())
        else:
            image = image or ctx.author
            return polaroid.Image(await image.avatar_url_as(format="png").read())

    @staticmethod
    def _do_image_manip(image, method, *args, **kwargs):
        method = getattr(image, method)
        method(*args, **kwargs)
        return image

    @staticmethod
    def build_embed(ctx, image, *, filename: str, elapsed: int):
        file = discord.File(BytesIO(image.save_bytes()), filename=f"{filename}.png")
        embed = discord.Embed(colour=ctx.bot.embed_colour)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        embed.set_image(url=f"attachment://{filename}.png")
        embed.set_footer(text=f"Finished in {elapsed:.3f} seconds")
        return embed, file

    async def do_img_manip(self, ctx, image, method: str, filename: str, *args, **kwargs):
        async with ctx.typing():
            with ctx.bot.utils.StopWatch() as sw:
                image = await self.get_image(ctx, image)
                image = await ctx.bot.loop.run_in_executor(None, self._do_image_manip, image, method, *args, **kwargs)
            embed, file = self.build_embed(ctx, image, filename=filename, elapsed=sw.elapsed)
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
