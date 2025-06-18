import os
import logging
from telegram.ext import Application, MessageHandler, filters
from telegram import Update
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ChannelCopyBot:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.source_channel_ids = list(map(int, os.getenv('SOURCE_CHANNEL_IDS').split(',')))
        self.target_channel_id = int(os.getenv('TARGET_CHANNEL_ID'))
        self.admin_user_ids = list(map(int, os.getenv('ADMIN_USER_IDS').split(',')))

    async def copy_message(self, update: Update, context):
        """Copy messages from source channels to target channel."""
        try:
            message = update.effective_message
            
            if not message or message.chat.id == self.target_channel_id:
                return
                
            logger.info(f"Copying message from {message.chat.id} to {self.target_channel_id}")
            await message.copy(chat_id=self.target_channel_id)
            
        except Exception as e:
            logger.error(f"Error copying message: {e}")

    async def handle_commands(self, update: Update, context):
        """Handle admin commands."""
        command = update.message.text.split()[0].lower()
        
        if command == '/start':
            await update.message.reply_text(
                "Channel Copy Bot is running!\n"
                f"Copying from {len(self.source_channel_ids)} channels to {self.target_channel_id}"
            )
        elif command == '/help':
            await update.message.reply_text(
                "Available commands:\n"
                "/start - Check bot status\n"
                "/help - Show this help message"
            )

    async def error_handler(self, update, context):
        """Log errors."""
        logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)

    def run(self):
        """Run the bot."""
        application = Application.builder().token(self.bot_token).build()
        
        # Add handler for channel posts
        application.add_handler(MessageHandler(
            filters.Chat(self.source_channel_ids) & ~filters.COMMAND,
            self.copy_message
        ))
        
        # Add handler for commands
        application.add_handler(MessageHandler(filters.COMMAND & filters.User(self.admin_user_ids), self.handle_commands))
        
        # Error handler
        application.add_error_handler(self.error_handler)
        
        logger.info("Bot started and running...")
        application.run_polling()

if __name__ == '__main__':
    bot = ChannelCopyBot()
    bot.run()
