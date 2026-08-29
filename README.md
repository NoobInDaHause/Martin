# Martin

A feature-rich Discord bot/app written in Python using discord.py. Martin is designed to be extensible through a cog-based architecture, making it easy to add new functionality.

---

## ✨ Features

- **Cog-based Architecture**: Easily extensible with modular commands organized by cogs
- **Discord.py 2.0+**: Built on the latest discord.py version with async/await support
- **Database Support**: SQLite database integration for persistent data storage
- **Custom Help Command**: Formatted help embeds with command categories
- **Admin Commands**: Owner-only commands for bot management (restart, shutdown, cog management)
- **Customizable**: Simple configuration system via `config.json`
- **Multi-prefix Support**: Guild-specific and global prefix support
- **User Blacklist**: Ability to blacklist users from using the bot
- **Prefix Commands**: Simple and intuitive text-based commands
- **Unfinished**: Many more updates to come

---

## 📋 Requirements

- **Python 3.10+** (check with `python --version`)
- **Git** (optional, for cloning the repository)

**That's it!** All Python dependencies are automatically installed by the startup scripts.

### Dependencies Included
The startup scripts will install:
- `discord.py[voice]` - Discord bot framework
- `aiosqlite` - Async SQLite database
- `aiohttp` - Async HTTP client
- `packaging` - Version comparison utilities
- `python-dotenv` - Environment variable management

See `requirements.txt` for the complete list.

---

## 🚀 Quick Start

The fastest way to get Martin running is to use the startup scripts—they automatically handle everything:

### Windows
```bash
.\start_bot.bat
```

### Linux/macOS
```bash
bash start_bot.sh
```

**That's it!** The scripts will:
- ✅ Create a virtual environment (if needed)
- ✅ Install/update dependencies automatically
- ✅ Run the bot
- ✅ Auto-restart if exit code is 26

---

## 📦 Installation & Setup

### 1. Download the Bot
Download the latest release from [GitHub Releases](https://github.com/NoobInDaHause/Martin/releases):

1. Go to the [Releases page](https://github.com/NoobInDaHause/Martin/releases)
2. Download the latest version (`.zip` file)
3. Extract the folder to your desired location
4. Open a terminal/command prompt in the extracted folder

**Alternatively, using Git (for developers):**
```bash
git clone https://github.com/NoobInDaHause/Martin.git
cd Martin
```

### 2. Create Environment Variables
Rename `.env.example` into `.env` and open and replace `<your_bot_token_here>` with your actual bot token.
```env
TOKEN=your_bot_token_here
```

**How to get a bot token:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to the "Bot" tab and click "Add Bot"
4. Under TOKEN, click "Copy"
5. Paste it in your `.env` file

### 3. Configure Bot Settings
Rename `config.json.example` to `config.json` and customize as needed:

```json
{
  "default_prefixes": ["m!", "m."],
  "guild_prefixes": {}, `<- DO NOT MODIFY`
  "global_hex_colour": "#276a8a",
  "blacklisted_user_ids": [] `<- DO NOT MODIFY`
}
```

### 4. Run the Bot
Use the startup script for your OS (see Quick Start above)

---

## 🛠️ How the Startup Scripts Work

Both `start_bot.bat` (Windows) and `start_bot.sh` (Linux/macOS) are intelligent:

- **Virtual Environment**: Creates `.venv` automatically on first run
- **Smart Dependency Caching**: Uses SHA256 hash of `requirements.txt` to detect changes
  - Only reinstalls dependencies if `requirements.txt` has been modified
  - Saves time on subsequent runs
- **Auto-Restart**: Exit code 26 triggers automatic bot restart
- **Error Handling**: Notifies you if setup fails

No manual virtual environment creation or pip install needed!

---

## 📁 Project Structure

```
Martin/
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── config.json            # Bot configuration (copy from config.json.example)
├── config.json.example    # Configuration template
├── version.txt            # Version tracking
├── README.md              # This file
│
├── Martin/                # Main bot package
│   ├── bot.py             # Main bot class
│   ├── context.py         # Custom command context
│   ├── interaction.py     # Discord interaction utilities
│   ├── help_command.py    # Custom help command
│   ├── settings.py        # Settings/configuration
│   └── __init__.py        # Package exports
│
├── Cogs/                  # Bot cogs (feature modules)
│   ├── General/           # General commands
│   │   ├── general.py
│   │   ├── general_data_manager.py
│   │   └── __init__.py
│   └── Owner/             # Owner-only commands
│       ├── owner.py
│       └── __init__.py
│
├── Utilities/             # Utility modules
│   ├── data_manager.py    # Database operations
│   ├── exceptions.py      # Custom exceptions
│   ├── formatting.py      # Text formatting utilities
│   └── views.py           # Discord UI components
│
├── cogs_data/             # Database storage (auto-created)
│   └── *.db              # SQLite database files
│
├── start_bot.bat          # Windows startup script
└── start_bot.sh           # Linux/macOS startup script
```

---

## 🧩 Available Cogs

### General
General-purpose commands for all users.

**Commands:**
- `[p]uptime` - Check how long the bot has been running
- `[p]ping` - Check bot latency
- `[p]info` or `[p]botinfo` - View bot information
- `[p]invite` - Get the bot invite link

**Owner-only:**
- `[p]custominfo [text]` - Add custom info to bot info command (leave blank to clear)

### Owner
Administrative commands for bot owners only.

**Commands:**
- `[p]checkforupdates` - Check if a newer version is available on GitHub
- `[p]restart` - Restart the bot process
- `[p]shutdown` - Shutdown the bot
- `[p]cog list` - Show loaded/unloaded cogs
- `[p]cog load <cog_names>` - Load cog(s)
- `[p]cog unload <cog_names>` - Unload cog(s)
- `[p]cog reload <cog_names>` - Reload cog(s)
- `[p]testerror`, `[p]plzerror`, `[p]givemeerror` - Test error handling (development)

---

## 🔧 Creating Custom Cogs

Cogs are organized in the `Cogs/` directory. Create a new folder with the cog name:

```
Cogs/
├── YourCog/
│   ├── your_cog.py       # Main cog file
│   ├── data_manager.py   # Optional: cog-specific database
│   └── __init__.py       # Setup function
```

**Example Cog Structure:**

```python
# Cogs/YourCog/your_cog.py
import discord
from discord.ext import commands
from Martin import Martin, MartinContext

class YourCog(commands.Cog):
    """Your cog description."""
    
    def __init__(self, bot: Martin):
        self.bot = bot
    
    @commands.command(name="hello")
    async def hello_command(self, ctx: MartinContext) -> None:
        """Say hello!"""
        await ctx.send(f"Hello, {ctx.author.mention}!")

async def setup(bot: Martin) -> None:
    await bot.add_cog(YourCog(bot))
```

```python
# Cogs/YourCog/__init__.py
from Martin import Martin
from .your_cog import YourCog

async def setup(bot: Martin) -> None:
    await bot.add_cog(YourCog(bot))
```

The bot will automatically discover and load cogs from the `Cogs/` directory on startup.

---

## 📚 Utilities Reference

### DataManager
Handles database operations for cogs using SQLite.

```python
from Utilities.data_manager import DataManager

db = DataManager("CogName")

# Execute query
await db.execute("CREATE TABLE my_table (...)")

# Fetch data
result = await db.execute("SELECT * FROM my_table", select=True)

# Insert/Update
await db.execute("INSERT INTO my_table VALUES (...)", (value1, value2))
```

### Formatting
Text formatting utilities.

```python
from Utilities.formatting import format_list, format_time, pagify

# Format a list
text = format_list(["item1", "item2", "item3"], style="and")
# Output: "item1, item2 and item3"

# Format time in seconds
text = format_time(3661)  # Returns: "1 hour and 1 minute"

# Split text into pages
pages = pagify("Long text...", page_length=2000)
```

### Views
Discord UI components.

```python
from Utilities.views import ConfirmationView

view = ConfirmationView(ctx, confirmed_content="Action confirmed!")
await view.start(content="Are you sure?")
await view.wait()

if view.value:  # User clicked confirm
    print("Confirmed!")
```

---

## ⚙️ Configuration Guide

### default_prefixes
List of command prefixes that work globally.
```json
"default_prefixes": ["m!", "m.", "martin "]
```

### guild_prefixes
Override prefixes for specific guilds (servers).
```json
"guild_prefixes": {
  "123456789": ["prefix!"],
  "987654321": ["custom!"]
}
```

### global_hex_colour
Default embed color for the bot's messages (hex format).
```json
"global_hex_colour": "#2B2D31"
```

### blacklisted_user_ids
User IDs that cannot use the bot's commands.
```json
"blacklisted_user_ids": [123456789, 987654321]
```

---

## 🐛 Troubleshooting

**Bot won't start:**
- Ensure Python 3.10+ is installed: `python --version`
- Check `.env` file exists and contains valid TOKEN
- Verify `config.json` exists (copy from `config.json.example`)
- Startup scripts will auto-install dependencies if missing
- Check console output for detailed error messages

**Startup script fails:**
- Windows: Ensure you're in the project directory, run as administrator if needed
- Linux/macOS: Ensure execute permission: `chmod +x start_bot.sh`
- Check Python version: `python --version` (need 3.10+)
- Manual install: `python -m pip install -r requirements.txt`

**Bot token not working:**
- Ensure the token is correct in `.env` (no extra spaces)
- Don't share your token with anyone
- If compromised, regenerate it in Discord Developer Portal
- Bot token should look like: `MTA4Ng.G-xxxxx.xxxxx-xxxxxx`

**Cogs not loading:**
- Check that the cog folder has `__init__.py` file
- Verify the cog's `setup(bot)` function exists
- Check console output for error messages during startup

**Permission errors:**
- Ensure the bot has proper Discord permissions
- Move the bot role above other roles in server settings
- Bot needs "Send Messages", "Embed Links", and other relevant permissions

---

## 📝 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs and issues
- Suggest new features
- Create pull requests with improvements
- Improve documentation

---

## 📞 Support

For issues, questions, or suggestions, please open an issue on the repository.

---

**Happy coding! 🚀**
