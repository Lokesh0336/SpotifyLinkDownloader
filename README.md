SpotifyLinkDownloader - Telegram Bot 🎧
A Python-based Telegram bot that downloads songs directly from Spotify using track, playlist, or album links. Users send Spotify URLs to the bot, choose their preferred audio format, and receive the music files or zipped albums/playlists seamlessly within Telegram.

🚀 Key Features
⬇️ Direct Download: Downloads songs, playlists, or albums via Spotify URLs only.

🎵 Format Selection: Supports multiple audio formats (mp3, m4a, flac, opus).

✅ Batch Downloads: Large playlists/albums are zipped before sending.

🤖 Telegram Bot: Easy-to-use chat interface for music download requests.

💻 Technologies Used
Python: Core programming language.

python-telegram-bot: Handles Telegram bot commands and interactions.

spotdl: For downloading music from Spotify links via subprocess.

asyncio: To manage asynchronous Telegram bot operations.

python-dotenv: (Optional) For managing environment variables securely.

▶️ Getting Started
Prerequisites
Python 3.8+

A Telegram Bot Token from @BotFather

Installation
Clone the repository:

bash
git clone https://github.com/Lokesh0336/SpotifyLinkDownloader.git
cd SpotifyLinkDownloader
Create a virtual environment (recommended):

bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
Install dependencies:

bash
pip install python-telegram-bot spotdl
Set your bot token in your script or environment:

In your script, set the BOT_TOKEN variable or use environment variables.

Run the bot:

bash
python bot.py
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

🌐 Contact
Created with ❤️ by Lokesh Ragutla

GitHub: https://github.com/Lokesh0336/SpotifyLinkDownloader

LinkedIn: https://www.linkedin.com/in/lokesh-ragutla-a8352724a