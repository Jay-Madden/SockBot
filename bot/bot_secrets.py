import json
import os
import logging

from bot.errors import ConfigAccessError

log = logging.getLogger(__name__)


class BotSecrets:
    def __init__(self) -> None:
        self._bot_token: str | None = None
        self._bot_prefix: str | None = None
        self._gifMe_token: str | None = None
        self._github_url: str | None = None
        self._merriam_key: str | None = None
        self._weather_key: str | None = None
        self._geocode_key: str | None = None
        self._azure_translate_key: str | None = None
        self._startup_log_channel_ids: list[int] | None = None
        self._error_log_channel_ids: list[int] | None = None
        self._class_archive_category_ids: list[int] | None = None

    @property
    def bot_token(self) -> str:
        """
        The discord api token defined in your discord developer page

        Raises:
            ConfigAccessError: Raised if the token has not been set

        Returns:
            str: The api Token
        """
        if not self._bot_token:
            raise ConfigAccessError("bot_token has not been initialized")
        return self._bot_token

    @bot_token.setter
    def bot_token(self, value: str | None) -> None:
        if self._bot_token:
            raise ConfigAccessError("bot_token has already been initialized")
        self._bot_token = value

    @property
    def bot_prefix(self) -> str:
        if not self._bot_prefix:
            return "!"
        return self._bot_prefix

    @bot_prefix.setter
    def bot_prefix(self, value: str | None) -> None:
        if self._bot_prefix:
            raise ConfigAccessError("bot_prefix has already been initialized")
        self._bot_prefix = value

    @property
    def gif_me_token(self) -> str:
        if not self._gifMe_token:
            raise ConfigAccessError("gif_me has not been initialized")
        return self._gifMe_token

    @gif_me_token.setter
    def gif_me_token(self, value: str | None) -> None:
        if self._gifMe_token:
            raise ConfigAccessError("gif_me_token has already been initialized")
        self._gifMe_token = value

    @property
    def github_url(self) -> str:
        if not self._github_url:
            return "https://github.com/Jay-Madden/SockBot"
        return self._github_url

    @github_url.setter
    def github_url(self, value: str | None) -> None:
        if self._github_url:
            raise ConfigAccessError("github_url has already been initialized")
        self._github_url = value

    @property
    def merriam_key(self) -> str:
        if not self._merriam_key:
            raise ConfigAccessError("merriam_key has not been intialized")
        return self._merriam_key

    @merriam_key.setter
    def merriam_key(self, value: str | None) -> None:
        if self._merriam_key:
            raise ConfigAccessError("merriam_key has already been initialized")
        self._merriam_key = value

    @property
    def weather_key(self) -> str:
        if not self._weather_key:
            raise ConfigAccessError("weather_key has not been initialized")
        return self._weather_key

    @weather_key.setter
    def weather_key(self, value: str | None) -> None:
        if self._weather_key:
            raise ConfigAccessError("weather_key has already been initialized")
        self._weather_key = value

    @property
    def startup_log_channel_ids(self) -> list[int]:
        if not self._startup_log_channel_ids:
            raise ConfigAccessError("startup_log_channel_ids has not been initialized")
        return self._startup_log_channel_ids

    @startup_log_channel_ids.setter
    def startup_log_channel_ids(self, value: list[int]) -> None:
        if self._startup_log_channel_ids:
            raise ConfigAccessError("startup_log_channel_ids has already been initialized")
        self._startup_log_channel_ids = value

    @property
    def error_log_channel_ids(self) -> list[int]:
        if not self._error_log_channel_ids:
            raise ConfigAccessError("error_log_channel_ids has not been initialized")
        return self._error_log_channel_ids

    @error_log_channel_ids.setter
    def error_log_channel_ids(self, value: list[int]) -> None:
        if self._error_log_channel_ids:
            raise ConfigAccessError("error_log_channel_ids has already been initialized")
        self._error_log_channel_ids = value

    @property
    def geocode_key(self) -> str:
        if not self._geocode_key:
            raise ConfigAccessError("geocode_key has not been initialized")
        return self._geocode_key

    @geocode_key.setter
    def geocode_key(self, value: str | None) -> None:
        if self._geocode_key:
            raise ConfigAccessError("geocode_key has already been initialized")
        self._geocode_key = value

    @property
    def azure_translate_key(self) -> str:
        if not self._azure_translate_key:
            raise ConfigAccessError("azure_translate_key has not been initialized")
        return self._azure_translate_key

    @azure_translate_key.setter
    def azure_translate_key(self, value: str | None) -> None:
        if self._azure_translate_key:
            raise ConfigAccessError("azure_translate_key has already been initialized")
        self._azure_translate_key = value

    @property
    def class_archive_category_ids(self) -> list[int]:
        if not self._class_archive_category_ids:
            raise ConfigAccessError("class_archive_category_ids has not been initialized")
        return self._class_archive_category_ids

    @class_archive_category_ids.setter
    def class_archive_category_ids(self, value: list[int] | None) -> None:
        if self._class_archive_category_ids:
            raise ConfigAccessError("class_archive_category_ids has already been initialized")
        self._class_archive_category_ids = value

    def load_development_secrets(self, lines: str) -> None:
        secrets = json.loads(lines)

        self.bot_token = secrets["BotToken"]
        self.bot_prefix = secrets["BotPrefix"]
        self.startup_log_channel_ids = secrets["StartupLogChannelIds"]
        self.error_log_channel_ids = secrets["ErrorLogChannelIds"]
        self.gif_me_token = secrets["GifMeToken"]
        self.github_url = secrets["GithubSourceUrl"]
        self.merriam_key = secrets["MerriamKey"]
        self.weather_key = secrets["WeatherKey"]
        self.geocode_key = secrets["GeocodeKey"]
        self.azure_translate_key = secrets["AzureTranslateKey"]
        self.class_archive_category_ids = secrets["ClassArchiveCategoryIds"]

        log.info("Bot Secrets Loaded")

    def load_production_secrets(self) -> None:

        # Ignore these type errors, mypy doesn't know how to handle properties that return narrower types then they are assigned too
        self.bot_token = os.environ.get("BOT_TOKEN")  # type: ignore
        self.bot_prefix = os.environ.get("BOT_PREFIX")  # type: ignore
        self.startup_log_channel_ids = [
            int(n) for n in os.environ.get("STARTUP_LOG_CHANNEL_IDS").split(",")  # type: ignore
        ]
        self.error_log_channel_ids = [
            int(n) for n in os.environ.get("ERROR_LOG_CHANNEL_IDS").split(",")  # type: ignore
        ]
        self.gif_me_token = os.environ.get("GIF_ME_TOKEN")  # type: ignore
        self.github_url = os.environ.get("GITHUB_URL")  # type: ignore
        self.merriam_key = os.environ.get("MERRIAM_KEY")  # type: ignore
        self.weather_key = os.environ.get("WEATHER_KEY")  # type: ignore
        self.geocode_key = os.environ.get("GEOCODE_KEY")  # type: ignore
        self.azure_translate_key = os.environ.get("AZURE_TRANSLATE_KEY")  # type: ignore
        self.class_archive_category_ids = [
            int(n) for n in os.environ.get("CLASS_ARCHIVE_CATEGORY_IDS").split(",")  # type: ignore
        ]
        log.info("Production keys loaded")


secrets = BotSecrets()
