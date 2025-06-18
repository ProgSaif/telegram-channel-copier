import os
import re
import logging
from telegram.ext import Application, MessageHandler, filters
from telegram import Update, MessageEntity
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Enhanced logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG if os.getenv('DEBUG') else logging.INFO
)
logger = logging.getLogger(__name__)

class BinanceRedPacketBot:
    def __init__(self):
        self.validate_environment()
        self.red_packet_pattern = re.compile(r'(?<!\S)[A-Z0-9]{8}(?!\S)')
        self.codes_forwarded = 0
        logger.info("Bot initialized successfully")

    def validate_environment(self):
        """Validate all required environment variables"""
        env_vars = {
            'BOT_TOKEN': os.getenv('BOT_TOKEN'),
            'SOURCE_CHANNEL_IDS': os.getenv('SOURCE_CHANNEL_IDS'),
            'TARGET_CHANNEL_ID': os.getenv('TARGET_CHANNEL_ID')
        }
        
        for name, value in env_vars.items():
            if not value:
                raise ValueError(f"Missing environment variable: {name}")
            
        try:
            self.bot_token = env_vars['BOT_TOKEN']
            self.source_channel_ids = [int(x.strip()) for x in env_vars['SOURCE_CHANNEL_IDS'].split(',')]
            self.target_channel_id = int(env_vars['TARGET_CHANNEL_ID'])
            self.admin_user_ids = [int(x) for x in os.getenv('ADMIN_USER_IDS', '').split(',') if x.strip()]
        except Exception as e:
            raise ValueError(f"Invalid environment variable format: {e}")

    async def copy_message(self, update: Update, context):
        try:
            message = update.effective_message
            if not message:
                logger.debug("Empty message received")
                return

            logger.debug(f"Processing message from chat {message.chat.id}")

            # Skip if from target channel or no text
            if message.chat.id == self.target_channel_id:
                return

            # Skip media and links
            if self.has_media_or_links(message):
                logger.debug("Skipping message with media/links")
                return

            text = (message.text or message.caption or "").upper()
            codes = self.extract_valid_codes(text)
            
            if codes:
                await self.forward_codes(codes, context)
                
        except Exception as e:
            logger.error(f"Error in copy_message: {str(e)}", exc_info=True)

    def has_media_or_links(self, message):
        return (message.photo or message.video or message.document or
                (message.entities and any(e.type in (MessageEntity.URL, MessageEntity.TEXT_LINK) 
                 for e in message.entities)))

    def extract_valid_codes(self, text):
        potential_codes = self.red_packet_pattern.findall(text)
        return [code for code in potential_codes 
               if any(c.isdigit() for c in code) and any(c.isalpha() for c in code)]

    async def forward_codes(self, codes, context):
        formatted_codes = "\n".join(f"`{code}`" for code in codes)
        message_text = (
            "🎉 Binance Red Packet Codes 🎉\n\n"
            f"{formatted_codes}\n\n"
            "_Tap on code to copy_"
        )
        
        try:
            await context.bot.send_message(
                chat_id=self.target_channel_id,
                text=message_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            self.codes_forwarded += len(codes)
            logger.info(f"Successfully forwarded {len(codes)} codes")
        except Exception as e:
            logger.error(f"Failed to forward codes: {str(e)}")

    def run(self):
        try:
            application = Application.builder().token(self.bot_token).build()
            
            # Add handlers
            application.add_handler(MessageHandler(
                filters.Chat(self.source_channel_ids) & ~filters.COMMAND,
                self.copy_message
            ))
            
            application.add_error_handler(self.error_handler)
            
            if os.getenv('RAILWAY_ENVIRONMENT'):
                logger.info("Starting webhook for Railway deployment")
                application.run_webhook(
                    listen="0.0.0.0",
                    port=int(os.getenv('PORT', 8000)),
                    webhook_url=os.getenv('WEBHOOK_URL'),
                    secret_token=os.getenv('WEBHOOK_SECRET')
                )
            else:
                logger.info("Starting polling for local development")
                application.run_polling()
                
        except Exception as e:
            logger.critical(f"Failed to start bot: {str(e)}", exc_info=True)
            raise

if __name__ == '__main__':
    try:
        load_dotenv()
        bot = BinanceRedPacketBot()
        bot.run()
    except Exception as e:
        logger.critical(f"Bot crashed during startup: {str(e)}", exc_info=True)
