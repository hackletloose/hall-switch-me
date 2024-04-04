
### DISCORD SWITCH ME BOT

---

# Discord SWITCH ME-BOT

This application is a Discord bot designed to interact with users on Discord, manage user data, and integrate with an external API and a SQLite database. It offers multilingual support and handles gaming-related functionalities.

## Key Features

- **Discord Bot Integration**: Interacts with users on a specified Discord channel.
- **External API Integration**: Connects to the CRCON API to switch players who have previously registered in the respective channel.
- **Database Support**: Uses SQLite for storing and managing user data.
- **Multilingual Support**: Offers translations for messages in multiple languages.
- **User and Gaming Management**: Associates Discord users with gaming identities (e.g., Steam IDs).

## Configuration

Set up the application by renaming the `default.env` file to `.env` and configuring it. The key environment variables include:

- `DISCORD_BOT_TOKEN`: Your Discord bot token.
- `API_BASE_URL`: Base URL of the external API.
- `USERNAME` & `PASSWORD`: Credentials for the API.
- `API_TOKEN`: Additional API token.
- `ALLOWED_CHANNEL_ID`: Discord channel ID where the bot operates.
- `DB_FILE`: Path to your SQLite database file.
- `COMMAND_SWITCH` & `COMMAND_REG`: Command keywords for bot operations.
- `LANGUAGE`: Preferred language (default is English).

## Files Overview

- **api_client.py**: Manages API interactions.
- **bot.py**: Main script for the Discord bot.
- **database.py**: Handles database operations.
- **utils.py**: Contains utility functions like Steam ID validation.
- **translations.json**: Stores message translations for multilingual support.

## Usage

Run `bot.py` to start the Discord bot. Ensure that all configuration settings in `default.env` are correctly set. The bot will listen for commands on the specified Discord channel and interact with users according to the implemented functionalities.

## Dependencies

- Discord.py library
- Requests library for API calls
- SQLite3 for database management
- Dotenv for environment variable management

---

This README provides a general overview of the application. For detailed instructions and a deeper understanding of each component, refer to the comments and documentation within each script.
