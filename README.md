
### DISCORD SWITCH ME BOT

---

# Discord SWITCH ME-BOT

This Discord bot is designed to streamline the gaming experience for users on Discord servers, particularly for those playing team-based games like Hell Let Loose. The bot allows players to switch teams effortlessly without the need to manually request an admin for assistance. It provides a simple, automated solution for players to manage their team affiliation directly through Discord commands.

## How It Works

The bot's functionality revolves around two simple commands:

1. **Registration with SteamID**: Users start by registering their SteamID on the Discord server. This is done using the `!regiser <SteamID>` command. For example: `!register 76561198036680000` (replace this with your own SteamID). This process links the user's Steam account to their Discord account and stores it in our database. Registration is a one-time process.

2. **Team Switching in Game**: Once registered, players who wish to switch teams in-game can simply type the `!switch` command in the designated Discord channel. This triggers the bot to switch the player to the opposite team in the game server.

### Key Features

- **Automated Team Switching**: With the `!switch` command, players can change teams without admin intervention.
- **Persistent Linking of Accounts**: Registering the SteamID with the bot links the Discord and Steam accounts, making future switches seamless.
- **Dedicated Commands**: `!register` for registration and `!switch` for team switching, ensuring simple and intuitive usage.
- **Exclusive Channel Operation**: The bot's commands are restricted to a specific channel for organized and efficient operation.

## Additional Notes

- The bot's switching functionality is personal; each player must register their own SteamID.
- Commands `!switch` and `!register` are operational only within the specified Discord channel.
- This bot enhances the gaming experience by offering a quick and easy solution to a common gaming challenge.

---

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
- `USERNAME` & `PASSWORD`: Credentials for the CRCON API.
- `API_TOKEN`: CRCON API token.
- `ALLOWED_CHANNEL_ID`: Discord channel ID where the bot operates.
- `DB_FILE`: Path to your SQLite database file. Do not rename this file!
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