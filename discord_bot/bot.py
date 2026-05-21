import logging

import discord
from discord.ext import commands
from pydantic_settings import BaseSettings

from cogs._http import close_http_client

logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    DISCORD_TOKEN: str
    DISCORD_GUILD_ID: str | None = None  # empty string from compose treated as None
    API_URL: str = "http://backend:8000/api"
    INGEST_TOKEN: str

    @property
    def guild_id(self) -> int | None:
        return int(self.DISCORD_GUILD_ID) if self.DISCORD_GUILD_ID else None


settings = Settings()


class PriceBot(commands.Bot):
    def __init__(self, api_url: str, ingest_token: str) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.api_url = api_url
        self.ingest_token = ingest_token

    async def setup_hook(self) -> None:
        await self.load_extension("cogs.prices")
        if settings.guild_id:
            guild = discord.Object(id=settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logging.info("Slash commands synced to guild %s", settings.guild_id)
        else:
            await self.tree.sync()
            logging.info("Slash commands synced globally")

    async def on_ready(self) -> None:
        logging.info("Logged in as %s (id=%s)", self.user, self.user.id)

    async def close(self) -> None:
        await close_http_client()
        await super().close()


bot = PriceBot(api_url=settings.API_URL, ingest_token=settings.INGEST_TOKEN)


if __name__ == "__main__":
    bot.run(settings.DISCORD_TOKEN)
