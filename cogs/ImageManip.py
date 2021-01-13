import discord
from discord.ext import commands
import polaroid
from io import BytesIO
import typing
import time


class ImageManip(commands.Cog):
    """
    Image manipulation commands.
    """
    @commands.command()
    async def solarize(self, ctx, image: typing.Union[discord.Emoji, discord.Member] = None):
        """
        Solarize an image.

        `image` - The image to solarize. Can be a user (for their avatar), an emoji or an attachment.
        """
        async with ctx.typing():
            start = time.perf_counter()
            if isinstance(image, discord.Emoji):
                img = polaroid.Image(await image.url.read())
            elif isinstance(image, discord.Member):
                img = polaroid.Image(await image.avatar_url_as(format="png").read())
            else:
                if not ctx.message.attachments:
                    return await ctx.send("No image provided.")
                img = polaroid.Image(await ctx.message.attachments[0].read())
            img.solarize()
            end = time.perf_counter()
            file = discord.File(fp=BytesIO(img.save_bytes()), filename="solarize.png")
            embed = discord.Embed(colour=ctx.bot.embed_colour)
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            embed.set_image(url="attachment://solarize.png")
            embed.set_footer(text=f"Finished in {end - start:.3f} seconds")
            await ctx.send(embed=embed, file=file)


def setup(bot):
    bot.add_cog(ImageManip())
