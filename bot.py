import os
import re
import logging
from datetime import datetime
from telegram.ext import Application, MessageHandler, filters
from telegram import Update, MessageEntity
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BinanceRedPacketBot:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.source_channel_ids = list(map(int, os.getenv('SOURCE_CHANNEL_IDS').split(',')))
        self.target_channel_id = int(os.getenv('TARGET_CHANNEL_ID'))
        self.admin_user_ids = list(map(int, os.getenv('ADMIN_USER_IDS').split(',')))
        
        # Regex pattern for Binance Red Packet codes (8 alphanumeric chars)
        self.red_packet_pattern = re.compile(r'\b[A-Z0-9]{8}\b')
        
        # Stats tracking
        self.codes_forwarded = 0

    def extract_red_packet_codes(self, text):
        """Extract all valid Binance Red Packet codes from text."""
        return [code for code in self.red_packet_pattern.findall(text) if self.is_valid_code(code)]

    def is_valid_code(self, code):
        """Validate if the code matches Binance Red Packet format."""
        # Basic validation - 8 alphanumeric chars, at least 1 letter and 1 number
        return (len(code) == 8 and 
                any(c.isalpha() for c in code) and 
                any(c.isdigit() for c in code))

    def format_codes_message(self, codes, source_message):
        """Format the codes for forwarding with monospace and header."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_codes = '\n'.join(f'`{code}`' for code in codes)
        
        return (
            f"🎉 *Binance Red Packet Codes* 🎉\n"
            f"📅 *Time:* {timestamp}\n"
            f"🔗 *Source:* [Original Message]({source_message.link})\n\n"
            f"{formatted_codes}\n\n"
            "_Tap on code to copy_"
        )

    async def copy_message(self, update: Update, context):
        """Process messages and forward only red packet codes."""
        try:
            message = update.effective_message
            
            # Skip if message is from target channel or doesn't have text
            if not message or not message.text or message.chat.id == self.target_channel_id:
                return
                
            # Skip messages with media, links, or other entities
            if (message.photo or message.video or message.document or 
                message.entities and any(e.type in (MessageEntity.URL, MessageEntity.TEXT_LINK) 
                for e in message.entities)):
                return
                
            # Extract all potential codes from message
            text = message.text.upper()
            codes = self.extract_red_packet_codes(text)
            
            if not codes:
                return  # No valid codes found
                
            logger.info(f"Found {len(codes)} codes in message from {message.chat.id}")
            
            # Format and send the message
            formatted_message = self.format_codes_message(codes, message)
            await context.bot.send_message(
                chat_id=self.target_channel_id,
                text=formatted_message,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )
            
            self.codes_forwarded += len(codes)
            logger.info(f"Forwarded {len(codes)} codes to {self.target_channel_id} (Total: {self.codes_forwarded})")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def handle_commands(self, update: Update, context):
        """Handle admin commands."""
        command = update.message.text.split()[0].lower()
        
        if command == '/start':
            await update.message.reply_text(
                "Binance Red Packet Bot is running!\n"
                f"📡 Monitoring {len(self.source_channel_ids)} channels\n"
                f"🎯 Target channel: {self.target_channel_id}\n"
                f"📦 Total codes forwarded: {self.codes_forwarded}"
            )
        elif command == '/help':
            await update.message.reply_text(
                "Available commands:\n"
                "/start - Check bot status\n"
                "/help - Show this help message\n\n"
                "This bot only forwards Binance Red Packet codes (8-character alphanumeric) "
                "and ignores all other messages with links, media, or usernames."
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
        application.add_handler(MessageHandler(
            filters.COMMAND & filters.User(self.admin_user_ids), 
            self.handle_commands
        ))
        
        # Error handler
        application.add_error_handler(self.error_handler)
        
        logger.info("Bot started and running...")
        application.run_polling()

if __name__ == '__main__':
    bot = BinanceRedPacketBot()
    bot.run()
