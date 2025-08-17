import os
import subprocess
import shutil
import logging
import zipfile
from io import BytesIO
import asyncio

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
from telegram.error import BadRequest

# --- Load Environment Variables ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Token is now loaded from .env

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Supported Formats ---
SUPPORTED_FORMATS = ["mp3", "m4a", "flac", "opus"]

# Pending user downloads
pending_downloads = {}


def run_spotdl(url: str, audio_format: str, download_dir: str) -> list:
    """Run spotdl to download tracks and return downloaded file paths."""
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    command = [
        "spotdl",
        url,
        "--output", download_dir,
        "--overwrite", "skip",
        "--format", audio_format,
    ]

    logger.info(f"Running spotdl command: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        logger.error("spotdl exceeded timeout. Killing process.")
        return []

    if result.returncode != 0:
        logger.error(f"spotdl failed with error:\n{result.stderr}")
        return []

    # Collect downloaded files
    downloaded_files = []
    for root, _, files in os.walk(download_dir):
        for file in files:
            if file.endswith(f".{audio_format}"):
                downloaded_files.append(os.path.join(root, file))

    logger.info(f"Downloaded {len(downloaded_files)} file(s) in format {audio_format}.")
    return downloaded_files


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("Help", callback_data="help"),
        InlineKeyboardButton("Status", callback_data="status"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_msg = (
        "🎧 *Welcome to the Spotify Downloader Bot!*\n\n"
        "Send me a Spotify track, playlist, or album link, "
        "and you'll be able to choose the audio format for download.\n\n"
        "Created with ❤️ by Lokesh.R"
    )
    await update.message.reply_markdown(welcome_msg, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📌 *How to use this bot:*\n\n"
        "1️⃣ Send a Spotify track, playlist, or album URL.\n"
        "2️⃣ Choose your preferred audio format from the options.\n"
        "3️⃣ Wait while I download your music and send it to you.\n\n"
        "🔹 Supported formats: mp3, m4a, flac, opus\n"
        "🔹 Large playlists/albums are zipped for convenience.\n\n"
        "Commands:\n"
        "/start - Welcome message\n"
        "/help - Help message\n"
        "/status - Check bot status"
    )
    await update.message.reply_markdown(help_text)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is online and ready to download your Spotify music!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message.text.strip()
    logger.info(f"User({user_id}) sent message: {message}")

    valid_prefixes = (
        "https://open.spotify.com/track/",
        "https://open.spotify.com/playlist/",
        "https://open.spotify.com/album/",
        "spotify:track:",
        "spotify:playlist:",
        "spotify:album:",
    )

    if any(message.startswith(prefix) for prefix in valid_prefixes):
        pending_downloads[user_id] = {"url": message}
        keyboard = [[
            InlineKeyboardButton(fmt.upper(), callback_data=f"format_{fmt}")
            for fmt in SUPPORTED_FORMATS
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎵 *Choose your preferred audio format:*",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("❗ Please send a valid Spotify track, playlist, or album URL.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    async def safe_edit_text(message_text, parse_mode=None):
        try:
            await query.edit_message_text(message_text, parse_mode=parse_mode)
        except BadRequest as e:
            if 'Message is not modified' in str(e):
                logger.debug("Ignored duplicate edit attempt.")
            else:
                raise

    if data == "help":
        await safe_edit_text(
            "*Help Menu*\n\nSend a Spotify link to download music.\n"
            "After sending, choose your format.\nUse /status to check bot status.",
            parse_mode="Markdown",
        )

    elif data == "status":
        await safe_edit_text("✅ Bot is operational and ready to download Spotify music.")

    elif data.startswith("format_"):
        if user_id not in pending_downloads:
            await safe_edit_text("⚠️ No pending downloads. Send a Spotify link first.")
            return

        selected_format = data.split("_", 1)[1]
        if selected_format not in SUPPORTED_FORMATS:
            await safe_edit_text("❌ Invalid format selected.")
            return

        url = pending_downloads[user_id]["url"]

        await safe_edit_text(
            f"⏬ Downloading in *{selected_format.upper()}* format. Please wait...",
            parse_mode="Markdown",
        )

        loop = asyncio.get_running_loop()
        downloaded_files = await loop.run_in_executor(None, run_spotdl, url, selected_format, "downloads")

        if not downloaded_files:
            await safe_edit_text("❌ Failed to download. Try again later.")
            pending_downloads.pop(user_id, None)
            if os.path.exists("downloads"):
                shutil.rmtree("downloads")
            return

        try:
            if len(downloaded_files) > 1:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zipf:
                    for filepath in downloaded_files:
                        arcname = os.path.relpath(filepath, "downloads")
                        zipf.write(filepath, arcname)
                zip_buffer.seek(0)

                await query.message.reply_document(
                    document=InputFile(zip_buffer, filename=f"spotify_download.{selected_format}.zip"),
                    caption=f"✅ Downloaded {len(downloaded_files)} tracks in *{selected_format.upper()}* format.",
                    parse_mode="Markdown",
                )
            else:
                file_path = downloaded_files[0]
                with open(file_path, "rb") as audio_file:
                    await query.message.reply_audio(
                        audio=audio_file,
                        caption=f"✅ Here's your track in *{selected_format.upper()}* format!",
                        parse_mode="Markdown",
                    )
        except Exception as e:
            logger.error(f"Error sending file(s): {e}")
            await query.message.reply_text("❌ Failed to send file(s). Try again.")
        finally:
            pending_downloads.pop(user_id, None)
            if os.path.exists("downloads"):
                shutil.rmtree("downloads")
    else:
        await query.answer("Unknown action.", show_alert=True)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot started. Listening for updates...")
    app.run_polling()


if __name__ == "__main__":
    main()
