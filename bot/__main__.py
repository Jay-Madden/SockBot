import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import discord

import bot.bot_secrets as bot_secrets
from bot.sock_bot import SockBot as SockBot
from bot.messaging.messenger import Messenger
from bot.utils.scheduler import Scheduler


def setup_logger() -> None:
    handlers = []
    handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                        level=logging.INFO, handlers=handlers)


async def main():
    if not os.path.exists('Logs'):
        os.makedirs('Logs')
    # sets up the logging for discord.py
    disc_log = logging.getLogger('discord')
    disc_log.setLevel(logging.DEBUG)
    disc_log_name = Path(f'Logs/{datetime.now().strftime("%Y-%m-%d-%H.%M.%S")}_discord.log')
    handler = logging.FileHandler(filename=disc_log_name, encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    disc_log.addHandler(handler)

    # creates the logger for the Bot Itself
    setup_logger()
    bot_log = logging.getLogger('bot')
    bot_log_name = Path(f'Logs/{datetime.now().strftime("%Y-%m-%d-%H.%M.%S")}_bot.log')
    bot_file_handle = logging.FileHandler(filename=bot_log_name, encoding='utf-8', mode='w')
    bot_file_handle.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    bot_log.addHandler(bot_file_handle)

    # check if this is a prod or a dev instance
    if bool(os.environ.get("PROD")):
        bot_log.info("Production env var found, loading production environment")
        bot_secrets.secrets.load_production_secrets()
    else:
        try:
            bot_log.info(f"Attempting to load BotSecrets.json from {os.getcwd()}")
            with open("BotSecrets.json") as f:
                bot_secrets.secrets.load_development_secrets(f.read())
        except FileNotFoundError as e:
            bot_log.fatal(f"{e}: The bot could not find your BotSecrets Json File")
            sys.exit(0)
        except KeyError as e:
            bot_log.fatal(f"{e} is not a valid key in BotSecrets")
            sys.exit(0)
        except Exception as e:
            bot_log.fatal(e)
            sys.exit(0)

    # get the default prefix for the bot instance
    prefix = bot_secrets.secrets.bot_prefix


    # Initialize the messenger here and inject it into the base bot class,
    # this is so it can be reused later on
    # if we decide to add something not related to the bot
    # E.G a website frontend
    messenger = Messenger(name='primary_bot_messenger')

    # enable privileged member gateway intents
    intents = discord.Intents.default()  # pylint: disable=assigning-non-slot
    intents.members = True  # pylint: disable=assigning-non-slot
    intents.message_content = True  # pylint: disable=assigning-non-slot

    # Create the scheduler for injection into the bot instance
    scheduler = Scheduler()

    # set allowed mentions
    mentions = discord.AllowedMentions(everyone=False, roles=False)

    bot_log.info('Bot Starting Up')
    client = SockBot(
        messenger=messenger,
        scheduler=scheduler,
        command_prefix=bot_secrets.secrets.bot_prefix,  # noqa: E126
        help_command=None,
        activity=discord.Game(name='Run ?help'),
        case_insensitive=True,
        max_messages=50000,
        allowed_mentions=mentions,
        intents=intents
    )

    async with client:
        bot_log.info("Bot starting up")
        await client.start(bot_secrets.secrets.bot_token)


if __name__ == "__main__":
    asyncio.run(main())
