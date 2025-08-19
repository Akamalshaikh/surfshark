import logging
import json
import os
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from telegram.constants import ChatMemberStatus

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = "7907410427:AAEuOiI8lyaMl7OWnXMRIpYqzCHoaDtphNk"  # Replace with your bot token
CHANNEL_ID = -1002771464366
CHANNEL_LINK = "https://t.me/dailyb1ns"
OWNER_ID = 6994528708
OWNER_USERNAME = "@its_soloz"

# Database file
DB_FILE = 'users.json'
STATS_FILE = 'bot_stats.json'

class ReferralBot:
    def __init__(self):
        self.application = None
        self.init_database()
    
    def init_database(self):
        """Initialize database files if they don't exist"""
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, 'w') as f:
                json.dump({}, f)
        
        if not os.path.exists(STATS_FILE):
            stats = {
                'total_users': 0,
                'total_referrals': 0,
                'rewards_withdrawn': 0,
                'bot_started': datetime.now().isoformat(),
                'daily_stats': {}
            }
            with open(STATS_FILE, 'w') as f:
                json.dump(stats, f, indent=2)

    def load_users(self) -> Dict[str, Any]:
        """Load users from database"""
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return {}

    def save_users(self, users: Dict[str, Any]):
        """Save users to database"""
        try:
            with open(DB_FILE, 'w') as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving users: {e}")

    def load_stats(self) -> Dict[str, Any]:
        """Load bot statistics"""
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading stats: {e}")
            return {}

    def save_stats(self, stats: Dict[str, Any]):
        """Save bot statistics"""
        try:
            with open(STATS_FILE, 'w') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving stats: {e}")

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user data, create if doesn't exist"""
        users = self.load_users()
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            users[user_id_str] = {
                'id': user_id,
                'username': '',
                'first_name': '',
                'referred_by': None,
                'referrals': [],
                'points': 0,
                'joined_channel': False,
                'join_date': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat(),
                'rewards_withdrawn': 0,
                'total_earned_points': 0
            }
            self.save_users(users)
            
            # Update total users count
            stats = self.load_stats()
            stats['total_users'] += 1
            today = datetime.now().strftime('%Y-%m-%d')
            if today not in stats['daily_stats']:
                stats['daily_stats'][today] = {'new_users': 0, 'referrals': 0}
            stats['daily_stats'][today]['new_users'] += 1
            self.save_stats(stats)
        
        return users[user_id_str]

    def update_user(self, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user data"""
        users = self.load_users()
        user_id_str = str(user_id)
        
        if user_id_str in users:
            users[user_id_str].update(updates)
            users[user_id_str]['last_activity'] = datetime.now().isoformat()
            self.save_users(users)
            return users[user_id_str]
        return {}

    async def check_membership(self, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
        """Check if user is a member of the channel"""
        try:
            chat_member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
            is_member = chat_member.status in [
                ChatMemberStatus.CREATOR,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.MEMBER
            ]
            
            self.update_user(user_id, {'joined_channel': is_member})
            return is_member
            
        except TelegramError as e:
            logger.error(f"Error checking membership for {user_id}: {e}")
            return False

    def get_main_keyboard(self):
        """Get main menu keyboard"""
        keyboard = [
            [KeyboardButton("👥 Refer Friends"), KeyboardButton("📊 My Stats")],
            [KeyboardButton("💰 Withdraw Reward"), KeyboardButton("🏆 Leaderboard")],
            [KeyboardButton("ℹ️ Help"), KeyboardButton("📞 Support")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    def get_join_keyboard(self):
        """Get join channel keyboard"""
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id
        user_data = self.get_user(user_id)
        
        # Update user info
        self.update_user(user_id, {
            'username': user.username or '',
            'first_name': user.first_name or ''
        })
        
        # Handle referral code
        if context.args and len(context.args) > 0:
            referrer_id = context.args[0]
            try:
                referrer_id = int(referrer_id)
                if referrer_id != user_id and not user_data['referred_by']:
                    referrer = self.get_user(referrer_id)
                    if referrer:
                        self.update_user(user_id, {'referred_by': referrer_id})
            except ValueError:
                pass

        welcome_text = (
            f"🎉 <b>Welcome to the Daily Bins Refer & Earn Bot!</b> 🎉\n\n"
            f"👋 Hello {user.first_name}!\n\n"
            f"🎯 <b>How it works:</b>\n"
            f"• Join our channel first\n"
            f"• Share your referral link with friends\n"
            f"• Earn 1 point per successful referral\n"
            f"• Get amazing rewards after 3 referrals!\n\n"
            f"📢 <b>Step 1:</b> Join our channel to continue:"
        )

        await update.message.reply_html(
            welcome_text,
            reply_markup=self.get_join_keyboard()
        )

    async def check_membership_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle membership check callback"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        is_member = await self.check_membership(context, user_id)
        
        if is_member:
            user_data = self.get_user(user_id)
            
            # Process referral if exists
            if user_data['referred_by'] and not any(user_id in self.get_user(user_data['referred_by'])['referrals']):
                referrer = self.get_user(user_data['referred_by'])
                referrer['referrals'].append(user_id)
                referrer['points'] += 1
                referrer['total_earned_points'] += 1
                
                self.update_user(user_data['referred_by'], referrer)
                
                # Update stats
                stats = self.load_stats()
                stats['total_referrals'] += 1
                today = datetime.now().strftime('%Y-%m-%d')
                if today not in stats['daily_stats']:
                    stats['daily_stats'][today] = {'new_users': 0, 'referrals': 0}
                stats['daily_stats'][today]['referrals'] += 1
                self.save_stats(stats)
                
                # Notify referrer
                try:
                    await context.bot.send_message(
                        user_data['referred_by'],
                        f"🎁 <b>New Referral!</b>\n\n"
                        f"✅ {query.from_user.first_name} joined through your link!\n"
                        f"💎 You earned 1 point\n"
                        f"📊 Total points: {referrer['points']}\n\n"
                        f"🎯 Keep sharing to earn more rewards!",
                        parse_mode='HTML'
                    )
                except TelegramError as e:
                    logger.error(f"Error notifying referrer: {e}")

            success_text = (
                f"✅ <b>Membership Confirmed!</b>\n\n"
                f"🎉 Welcome to Daily Bins Refer & Earn!\n\n"
                f"🎯 <b>Your Mission:</b>\n"
                f"Refer 3 friends to unlock premium rewards!\n\n"
                f"📱 Use the menu below to get started:"
            )

            await query.edit_message_text(success_text, parse_mode='HTML')
            await context.bot.send_message(
                user_id,
                "🏠 <b>Main Menu</b>\n\nChoose an option from the menu below:",
                parse_mode='HTML',
                reply_markup=self.get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ <b>Not a member yet!</b>\n\n"
                f"Please join our channel first, then click 'Check Membership' again.\n\n"
                f"📢 Channel: {CHANNEL_LINK}",
                parse_mode='HTML',
                reply_markup=self.get_join_keyboard()
            )

    async def refer_friends(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle refer friends button"""
        user_id = update.effective_user.id
        
        if not await self.check_membership(context, user_id):
            await update.message.reply_html(
                f"❌ <b>Channel membership required!</b>\n\n"
                f"Please join our channel first:",
                reply_markup=self.get_join_keyboard()
            )
            return

        user_data = self.get_user(user_id)
        bot_info = await context.bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        progress_bar = "🟩" * user_data['points'] + "⬜" * (3 - user_data['points'])
        
        refer_text = (
            f"🔗 <b>Your Referral Link</b>\n\n"
            f"📋 <code>{referral_link}</code>\n\n"
            f"📊 <b>Your Progress:</b>\n"
            f"{progress_bar} {user_data['points']}/3\n\n"
            f"👥 Total Referrals: {len(user_data['referrals'])}\n"
            f"💎 Points Earned: {user_data['points']}\n\n"
            f"🎯 <b>How to earn:</b>\n"
            f"• Share your link with friends\n"
            f"• They must join our channel\n"
            f"• You get 1 point per referral\n"
            f"• Withdraw rewards after 3 points!\n\n"
            f"💡 <b>Tip:</b> Share in groups, social media, or with friends directly!"
        )

        keyboard = [
            [InlineKeyboardButton("📤 Share Link", switch_inline_query=f"Join Daily Bins and earn rewards! {referral_link}")]
        ]
        
        await update.message.reply_html(
            refer_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle my stats button"""
        user_id = update.effective_user.id
        
        if not await self.check_membership(context, user_id):
            await update.message.reply_html(
                f"❌ <b>Channel membership required!</b>\n\n"
                f"Please join our channel first:",
                reply_markup=self.get_join_keyboard()
            )
            return

        user_data = self.get_user(user_id)
        join_date = datetime.fromisoformat(user_data['join_date']).strftime('%d %b %Y')
        
        status = "🔓 Ready to withdraw!" if user_data['points'] >= 3 else f"🔒 Need {3 - user_data['points']} more points"
        
        stats_text = (
            f"📊 <b>Your Statistics</b>\n\n"
            f"👤 Name: {update.effective_user.first_name}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📅 Joined: {join_date}\n\n"
            f"💎 Current Points: <b>{user_data['points']}</b>\n"
            f"👥 Total Referrals: <b>{len(user_data['referrals'])}</b>\n"
            f"🏆 Total Points Earned: <b>{user_data['total_earned_points']}</b>\n"
            f"💰 Rewards Withdrawn: <b>{user_data['rewards_withdrawn']}</b>\n\n"
            f"🎯 Status: {status}\n\n"
            f"📈 Keep referring friends to earn more points!"
        )

        await update.message.reply_html(stats_text)

    async def withdraw_reward(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdraw reward button"""
        user_id = update.effective_user.id
        
        if not await self.check_membership(context, user_id):
            await update.message.reply_html(
                f"❌ <b>Channel membership required!</b>\n\n"
                f"Please join our channel first:",
                reply_markup=self.get_join_keyboard()
            )
            return

        user_data = self.get_user(user_id)

        if user_data['points'] >= 3:
            # Reset points and update withdrawal count
            self.update_user(user_id, {
                'points': 0,
                'rewards_withdrawn': user_data['rewards_withdrawn'] + 1
            })
            
            # Update global stats
            stats = self.load_stats()
            stats['rewards_withdrawn'] += 1
            self.save_stats(stats)

            success_text = (
                f"🎉 <b>Congratulations!</b> 🎉\n\n"
                f"✅ Reward withdrawal successful!\n\n"
                f"📞 <b>Next Steps:</b>\n"
                f"Please contact our admin to claim your reward:\n"
                f"👤 {OWNER_USERNAME}\n\n"
                f"🔄 Your points have been reset to 0\n"
                f"🎯 Continue referring to earn more rewards!\n\n"
                f"🚀 Thank you for being part of Daily Bins!"
            )

            keyboard = [
                [InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]
            ]

            await update.message.reply_html(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            insufficient_text = (
                f"❌ <b>Insufficient Points!</b>\n\n"
                f"💎 Current Points: {user_data['points']}\n"
                f"🎯 Required Points: 3\n"
                f"📊 You need {3 - user_data['points']} more points\n\n"
                f"🚀 Keep referring friends to earn more points!\n"
                f"💡 Share your referral link to reach the goal faster."
            )

            await update.message.reply_html(insufficient_text)

    async def leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show leaderboard"""
        if not await self.check_membership(context, update.effective_user.id):
            await update.message.reply_html(
                f"❌ <b>Channel membership required!</b>\n\n"
                f"Please join our channel first:",
                reply_markup=self.get_join_keyboard()
            )
            return

        users = self.load_users()
        
        # Sort users by total earned points
        sorted_users = sorted(
            users.values(),
            key=lambda x: x.get('total_earned_points', 0),
            reverse=True
        )[:10]

        leaderboard_text = "🏆 <b>Top Referrers Leaderboard</b>\n\n"
        
        if not sorted_users:
            leaderboard_text += "No users yet! Be the first to refer friends! 🚀"
        else:
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            
            for i, user in enumerate(sorted_users):
                if i < 10:
                    name = user.get('first_name', 'Unknown')[:15]
                    points = user.get('total_earned_points', 0)
                    referrals = len(user.get('referrals', []))
                    
                    leaderboard_text += f"{medals[i]} <b>{name}</b>\n"
                    leaderboard_text += f"   💎 {points} points • 👥 {referrals} referrals\n\n"

        await update.message.reply_html(leaderboard_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        help_text = (
            f"ℹ️ <b>How to use Daily Bins Bot</b>\n\n"
            f"🎯 <b>Goal:</b> Refer 3 friends to earn rewards!\n\n"
            f"📋 <b>Steps:</b>\n"
            f"1️⃣ Join our channel\n"
            f"2️⃣ Get your referral link\n"
            f"3️⃣ Share with friends\n"
            f"4️⃣ Earn points when they join\n"
            f"5️⃣ Withdraw rewards after 3 points!\n\n"
            f"🎁 <b>Rewards:</b>\n"
            f"• Premium accounts\n"
            f"• Exclusive content access\n"
            f"• Special perks and more!\n\n"
            f"💡 <b>Tips:</b>\n"
            f"• Share in multiple groups\n"
            f"• Use social media\n"
            f"• Tell friends about benefits\n\n"
            f"❓ Need help? Contact {OWNER_USERNAME}"
        )

        await update.message.reply_html(help_text)

    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show support information"""
        support_text = (
            f"📞 <b>Support & Contact</b>\n\n"
            f"Need help or have questions?\n\n"
            f"👤 <b>Admin:</b> {OWNER_USERNAME}\n"
            f"📢 <b>Channel:</b> {CHANNEL_LINK}\n\n"
            f"💬 <b>Common Issues:</b>\n"
            f"• Not getting points? Make sure friends joined the channel\n"
            f"• Referral not working? Check the link format\n"
            f"• Can't withdraw? You need 3 points minimum\n\n"
            f"🕐 <b>Support Hours:</b> 24/7\n"
            f"⚡ <b>Response Time:</b> Usually within 1-2 hours"
        )

        keyboard = [
            [InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]
        ]

        await update.message.reply_html(
            support_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Admin Commands
    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin statistics"""
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("❌ This command is only available to the bot owner.")
            return

        users = self.load_users()
        stats = self.load_stats()
        
        total_users = len(users)
        total_referrals = sum(len(user.get('referrals', [])) for user in users.values())
        total_points = sum(user.get('total_earned_points', 0) for user in users.values())
        active_today = sum(1 for user in users.values() 
                          if datetime.fromisoformat(user.get('last_activity', '2020-01-01')).date() == datetime.now().date())

        # Get top referrer
        top_referrer = max(users.values(), key=lambda x: x.get('total_earned_points', 0), default=None)
        top_referrer_name = top_referrer.get('first_name', 'None') if top_referrer else 'None'
        top_referrer_points = top_referrer.get('total_earned_points', 0) if top_referrer else 0

        admin_stats_text = (
            f"📊 <b>Bot Statistics</b>\n\n"
            f"👥 Total Users: <b>{total_users}</b>\n"
            f"🔗 Total Referrals: <b>{total_referrals}</b>\n"
            f"💎 Total Points Earned: <b>{total_points}</b>\n"
            f"💰 Rewards Withdrawn: <b>{stats.get('rewards_withdrawn', 0)}</b>\n"
            f"📱 Active Today: <b>{active_today}</b>\n\n"
            f"🏆 <b>Top Referrer:</b>\n"
            f"👤 {top_referrer_name} ({top_referrer_points} points)\n\n"
            f"📈 <b>Bot Started:</b> {stats.get('bot_started', 'Unknown')[:10]}"
        )

        await update.message.reply_html(admin_stats_text)

    async def admin_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast message to all users"""
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("❌ This command is only available to the bot owner.")
            return

        if not context.args:
            await update.message.reply_html(
                "📢 <b>Usage:</b> <code>/broadcast [message]</code>\n\n"
                "Example: <code>/broadcast Hello everyone! 🎉</code>"
            )
            return

        message_text = ' '.join(context.args)
        users = self.load_users()
        
        sent_count = 0
        failed_count = 0
        
        await update.message.reply_text("📤 Starting broadcast...")

        for user_id in users.keys():
            try:
                await context.bot.send_message(
                    int(user_id),
                    message_text,
                    parse_mode='HTML'
                )
                sent_count += 1
                await asyncio.sleep(0.05)  # Rate limiting
            except TelegramError as e:
                failed_count += 1
                logger.error(f"Failed to send broadcast to {user_id}: {e}")

        result_text = (
            f"📢 <b>Broadcast Complete!</b>\n\n"
            f"✅ Successfully sent: <b>{sent_count}</b>\n"
            f"❌ Failed to send: <b>{failed_count}</b>\n"
            f"📊 Total users: <b>{len(users)}</b>"
        )

        await update.message.reply_html(result_text)

    async def admin_user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user information"""
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("❌ This command is only available to the bot owner.")
            return

        if not context.args:
            await update.message.reply_html(
                "👤 <b>Usage:</b> <code>/userinfo [user_id]</code>\n\n"
                "Example: <code>/userinfo 123456789</code>"
            )
            return

        try:
            target_user_id = int(context.args[0])
            user_data = self.get_user(target_user_id)
            
            if not user_data:
                await update.message.reply_text("❌ User not found!")
                return

            join_date = datetime.fromisoformat(user_data['join_date']).strftime('%d %b %Y %H:%M')
            last_activity = datetime.fromisoformat(user_data.get('last_activity', user_data['join_date'])).strftime('%d %b %Y %H:%M')

            user_info_text = (
                f"👤 <b>User Information</b>\n\n"
                f"🆔 ID: <code>{user_data['id']}</code>\n"
                f"👤 Name: {user_data.get('first_name', 'Unknown')}\n"
                f"🔗 Username: @{user_data.get('username', 'None')}\n"
                f"📅 Joined: {join_date}\n"
                f"🕐 Last Activity: {last_activity}\n\n"
                f"💎 Current Points: <b>{user_data['points']}</b>\n"
                f"🏆 Total Points Earned: <b>{user_data.get('total_earned_points', 0)}</b>\n"
                f"👥 Referrals: <b>{len(user_data.get('referrals', []))}</b>\n"
                f"💰 Rewards Withdrawn: <b>{user_data.get('rewards_withdrawn', 0)}</b>\n"
                f"📢 Channel Member: {'✅' if user_data.get('joined_channel') else '❌'}\n"
                f"🔗 Referred By: {user_data.get('referred_by', 'None')}"
            )

            await update.message.reply_html(user_info_text)

        except ValueError:
            await update.message.reply_text("❌ Invalid user ID! Please provide a valid number.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        text = update.message.text
        
        if text == "👥 Refer Friends":
            await self.refer_friends(update, context)
        elif text == "📊 My Stats":
            await self.my_stats(update, context)
        elif text == "💰 Withdraw Reward":
            await self.withdraw_reward(update, context)
        elif text == "🏆 Leaderboard":
            await self.leaderboard(update, context)
        elif text == "ℹ️ Help":
            await self.help_command(update, context)
        elif text == "📞 Support":
            await self.support_command(update, context)
        else:
            # For any other message, check membership first
            if not await self.check_membership(context, update.effective_user.id):
                await update.message.reply_html(
                    f"❌ <b>Channel membership required!</b>\n\n"
                    f"Please join our channel first to use this bot:",
                    reply_markup=self.get_join_keyboard()
                )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "🔧 Sorry, something went wrong. Please try again later.\n\n"
                    f"If the problem persists, contact {OWNER_USERNAME}"
                )
            except TelegramError:
                pass

    def run(self):
        """Run the bot"""
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()

        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("stats", self.admin_stats))
        self.application.add_handler(CommandHandler("broadcast", self.admin_broadcast))
        self.application.add_handler(CommandHandler("userinfo", self.admin_user_info))
        self.application.add_handler(CallbackQueryHandler(self.check_membership_callback, pattern="^check_membership$"))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Add error handler
        self.application.add_error_handler(self.error_handler)

        # Start the bot
        logger.info("Starting bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = ReferralBot()
    bot.run()