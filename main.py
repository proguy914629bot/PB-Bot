from dependencies import PB_Bot
from config import config


if __name__ == "__main__":
    bot = PB_Bot()
    bot.run(config["token"])
