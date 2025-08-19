import logging
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = '7907410427:AAEuOiI8lyaMl7OWnXMRIpYqzCHoaDtphNk'
CHANNEL_ID = -1002771464366
CHANNEL_LINK = 'https://t.me/dailyb1ns'
OWNER_ID = 6994528708
OWNER_USERNAME = '@its_soloz'

# Database file
DB_FILE = 'users.json'
STATS_FILE = 'bot_stats.json'

# Initialize database if it doesn't exist
if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w') as f:
        json.dump({}, f)

if not os.path.exists(STATS_FILE):
    with open(STATS_FILE, 'w') as f:
        json.dump({
            'total_users': 0,
            'total_referrals': 0,
            'total_withdrawals': 0,
            'bot_started': datetime.now().isoformat()
        }, f)

# Helper functions
def load_users():
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f'Error loading users: {e}')
        return {}

def save_users(users):
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        logger.error(f'Error saving users: {e}')

def load_stats():
    try:
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f'Error loading stats: {e}')
        return {}

def save_stats(stats):
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        logger.error(f'Error saving stats: {e}')

def get_user(user_id):
    users = load_users()
    user_key = str(user_id)
    
    # Create new user if doesn't exist
    if user_key not in users:
        users[user_key] = {
            'id': user_id,
            'username': '',
            'first_name': '',
            'referredBy': None,
            'referrals': [],
            'points': 0,
            'joinedChannel': False,
            'joinDate': datetime.now().isoformat(),
            'lastActive': datetime.now().isoformat(),
            'totalWithdrawals': 0
        }
        save_users(users)
        
        # Update total users count
        stats = load_stats()
        stats['total_users'] = len(users)
        save_stats(stats)
    else:
        # Migrate existing user data to new format
        user = users[user_key]
        updated = False
        
        # Add missing fields with default values
        default_fields = {
            'username': '',
            'first_name': '',
            'referredBy': None,
            'referrals': [],
            'points': 0,
            'joinedChannel': False,
            'joinDate': datetime.now().isoformat(),
            'lastActive': datetime.now().isoformat(),
            'totalWithdrawals': 0
        }
        
        for field, default_value in default_fields.items():
            if field not in user:
                user[field] = default_value
                updated = True
        
        # Ensure referrals is always a list
        if not isinstance(user.get('referrals'), list):
            user['referrals'] = []
            updated = True
            
        # Ensure points is a number
        if not isinstance(user.get('points'), (int, float)):
            user['points'] = 0
            updated = True
        
        if updated:
            users[user_key] = user
            save_users(users)
    
    return users[user_key]

def update_user(user_id, updates):
    users = load_users()
    if str(user_id) in users:
        users[str(user_id)].update(updates)
        users[str(user_id)]['lastActive'] = datetime.now().isoformat()
        save_users(users)
        return users[str(user_id)]
    return None

async def check_membership(context, user_id):
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        is_member = chat_member.status in ['creator', 'administrator', 'member']
        update_user(user_id, {'joinedChannel': is_member})
        return is_member
    except Exception as e:
        logger.error(f'Error checking membership: {e}')
        return False

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("👥 Refer Friends"), KeyboardButton("🔢 My Stats")],
        [KeyboardButton("💰 Withdraw Reward"), KeyboardButton("🏆 Leaderboard")],
        [KeyboardButton("ℹ️ Help"), KeyboardButton("👤 Profile")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton("📊 Bot Stats"), KeyboardButton("📢 Broadcast")],
        [KeyboardButton("👥 User List"), KeyboardButton("🔄 Backup Data")],
        [KeyboardButton("🚫 Ban User"), KeyboardButton("✅ Unban User")],
        [KeyboardButton("🔙 Back to Main")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # Update user info
    update_user(user_id, {
        'username': update.effective_user.username or '',
        'first_name': update.effective_user.first_name or ''
    })
    
    # Check for referral code
    if context.args and len(context.args) > 0:
        referrer_id = context.args[0]
        try:
            referrer_id = int(referrer_id)
            if referrer_id != user_id and not user['referredBy']:
                referrer = get_user(referrer_id)
                if referrer:
                    update_user(user_id, {'referredBy': referrer_id})
        except ValueError:
            pass
    
    # Welcome message
    welcome_text = f"""
🎉 <b>Welcome to Daily Bins Referral Bot!</b> 🎉

Hello {update.effective_user.first_name}! 👋

🌟 <b>What you can earn:</b>
• 1 Point = 1 Successful Referral
• 3 Points = Surfshark VPN Login
• More rewards coming soon!

🔰 <b>How it works:</b>
1️⃣ Join our channel
2️⃣ Share your referral link
3️⃣ Earn points when friends join
4️⃣ Withdraw amazing rewards!

<b>Owner:</b> {OWNER_USERNAME}
<b>Channel:</b> @dailyb1ns
"""
    
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    is_member = await check_membership(context, user_id)
    
    if is_member:
        user = get_user(user_id)
        
        # Handle referral credit - with safe access to referredBy
        referrer_id = user.get('referredBy')
        if referrer_id:
            try:
                referrer = get_user(referrer_id)
                # Ensure referrals is a list
                if not isinstance(referrer.get('referrals'), list):
                    referrer['referrals'] = []
                
                # Only add if not already in the list
                if user_id not in referrer['referrals']:
                    referrer['referrals'].append(user_id)
                    referrer['points'] = referrer.get('points', 0) + 1
                    update_user(referrer_id, {
                        'referrals': referrer['referrals'],
                        'points': referrer['points']
                    })
                    
                    # Update stats
                    stats = load_stats()
                    stats['total_referrals'] = stats.get('total_referrals', 0) + 1
                    save_stats(stats)
                    
                    # Notify referrer
                    try:
                        referrer_name = query.from_user.first_name or "Someone"
                        await context.bot.send_message(
                            referrer_id,
                            f"🎁 <b>New Referral!</b>\n\n"
                            f"<b>{referrer_name}</b> joined through your link!\n"
                            f"💰 You earned 1 point!\n"
                            f"🔢 Total points: {referrer['points']}\n\n"
                            f"Keep sharing to earn more! 🚀",
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        logger.error(f'Error notifying referrer: {e}')
            except Exception as e:
                logger.error(f'Error processing referral: {e}')
        
        success_text = f"""
✅ <b>Membership Confirmed!</b>

Welcome to our community! 🎊

🌟 You can now:
• Generate your referral link
• Check your stats and points
• View the leaderboard
• Withdraw rewards when eligible

Use the menu below to get started! 👇
"""
        
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.HTML
        )
        
        await context.bot.send_message(
            user_id,
            "🎯 <b>Choose an option:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_keyboard()
        )
    else:
        await query.edit_message_text(
            f"❌ <b>Not a Member Yet!</b>\n\n"
            f"Please join our channel first:\n"
            f"{CHANNEL_LINK}\n\n"
            f"After joining, click '✅ Check Membership' again.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")]
            ])
        )

async def refer_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_membership(context, user_id):
        await membership_required_message(update, context)
        return
    
    user = get_user(user_id)
    bot_info = await context.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    # Safe access to user data
    points = user.get('points', 0)
    referrals = user.get('referrals', [])
    
    progress_bar = "🟩" * points + "⬜" * (3 - points)
    
    referral_text = f"""
🔗 <b>Your Referral Link</b> 🔗

<code>{referral_link}</code>

📊 <b>Your Progress:</b>
{progress_bar} ({points}/3)

👥 <b>Referrals:</b> {len(referrals)}
💰 <b>Points:</b> {points}

🎯 <b>How to earn:</b>
1️⃣ Share your link with friends
2️⃣ Friends must join the channel
3️⃣ You get 1 point per referral
4️⃣ Withdraw rewards at 3 points!

💡 <b>Pro Tips:</b>
• Share in groups and social media
• Tell friends about our amazing content
• More referrals = better rewards!
"""
    
    keyboard = [
        [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing Telegram channel and earn rewards!")],
        [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{user_id}")]
    ]
    
    await update.message.reply_text(
        referral_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_membership(context, user_id):
        await membership_required_message(update, context)
        return
    
    user = get_user(user_id)
    
    # Safe access to user data
    join_date = user.get('joinDate', datetime.now().isoformat())
    points = user.get('points', 0)
    referrals = user.get('referrals', [])
    first_name = user.get('first_name', 'User')
    total_withdrawals = user.get('totalWithdrawals', 0)
    
    try:
        join_date_formatted = datetime.fromisoformat(join_date).strftime("%B %d, %Y")
    except:
        join_date_formatted = "Unknown"
    
    # Calculate rank
    users = load_users()
    user_points = [(uid, udata.get('points', 0)) for uid, udata in users.items()]
    user_points.sort(key=lambda x: x[1], reverse=True)
    rank = next((i+1 for i, (uid, _) in enumerate(user_points) if uid == str(user_id)), "N/A")
    
    stats_text = f"""
📊 <b>Your Statistics</b> 📊

👤 <b>Profile:</b>
• Name: {first_name}
• User ID: <code>{user_id}</code>
• Joined: {join_date_formatted}

🏆 <b>Performance:</b>
• Rank: #{rank}
• Points: {points} 💰
• Referrals: {len(referrals)} 👥
• Withdrawals: {total_withdrawals} 🎁

📈 <b>Progress:</b>
{"🟩" * points}{"⬜" * (3 - points)} ({points}/3)

{f"✅ <b>You can withdraw your reward!</b>" if points >= 3 else f"🔄 <b>Need {3 - points} more points to withdraw</b>"}
"""
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

async def withdraw_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_membership(context, user_id):
        await membership_required_message(update, context)
        return
    
    user = get_user(user_id)
    points = user.get('points', 0)
    
    if points >= 3:
        # Update user stats
        new_points = points - 3
        new_withdrawals = user.get('totalWithdrawals', 0) + 1
        
        update_user(user_id, {
            'points': new_points,
            'totalWithdrawals': new_withdrawals
        })
        
        # Update global stats
        stats = load_stats()
        stats['total_withdrawals'] = stats.get('total_withdrawals', 0) + 1
        save_stats(stats)
        
        # Notify owner
        try:
            first_name = user.get('first_name', 'Unknown')
            username = user.get('username', 'No username')
            
            await context.bot.send_message(
                OWNER_ID,
                f"🎁 <b>New Withdrawal Request!</b>\n\n"
                f"User: {first_name} (@{username})\n"
                f"ID: <code>{user_id}</code>\n"
                f"Reward: Surfshark VPN Login\n"
                f"Total Withdrawals: {new_withdrawals}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f'Error notifying owner: {e}')
        
        success_text = f"""
🎉 <b>Withdrawal Successful!</b> 🎉

Congratulations! Your reward has been processed.

🎁 <b>Reward:</b> Surfshark VPN Login
💰 <b>Points Used:</b> 3
🔢 <b>Remaining Points:</b> {new_points}

📩 <b>Next Steps:</b>
Please contact {OWNER_USERNAME} to receive your reward.

🔄 <b>Continue Earning:</b>
Keep referring friends to earn more rewards!
Your journey doesn't end here! 🚀
"""
        
        await update.message.reply_text(success_text, parse_mode=ParseMode.HTML)
    else:
        insufficient_text = f"""
❌ <b>Insufficient Points</b>

💰 Current Points: {points}
🎯 Required Points: 3
📊 Need: {3 - points} more points

🚀 <b>How to earn more:</b>
• Share your referral link
• Invite more friends
• Each successful referral = 1 point

Keep going! You're almost there! 💪
"""
        
        await update.message.reply_text(insufficient_text, parse_mode=ParseMode.HTML)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_membership(context, user_id):
        await membership_required_message(update, context)
        return
    
    users = load_users()
    user_points = [(uid, udata) for uid, udata in users.items() if udata['points'] > 0]
    user_points.sort(key=lambda x: x[1]['points'], reverse=True)
    
    leaderboard_text = "🏆 <b>Top Referrers Leaderboard</b> 🏆\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, udata) in enumerate(user_points[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = udata['first_name'] or f"User {uid[:8]}"
        points = udata['points']
        referrals = len(udata['referrals'])
        
        if str(uid) == str(user_id):
            leaderboard_text += f"{medal} <b>{name}</b> - {points}💰 ({referrals}👥) ⭐\n"
        else:
            leaderboard_text += f"{medal} {name} - {points}💰 ({referrals}👥)\n"
    
    if not user_points:
        leaderboard_text += "No active referrers yet. Be the first! 🚀"
    else:
        # Show user's rank if not in top 10
        user_rank = next((i+1 for i, (uid, _) in enumerate(user_points) if uid == str(user_id)), None)
        if user_rank and user_rank > 10:
            leaderboard_text += f"\n...\n{user_rank}. <b>You</b> - {get_user(user_id)['points']}💰"
    
    await update.message.reply_text(leaderboard_text, parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = f"""
ℹ️ <b>Help & Information</b> ℹ️

🤖 <b>Bot Commands:</b>
• /start - Start the bot
• 👥 Refer Friends - Get your referral link
• 🔢 My Stats - View your statistics
• 💰 Withdraw Reward - Claim your rewards
• 🏆 Leaderboard - Top referrers
• 👤 Profile - Your profile info

🎯 <b>How to Earn:</b>
1️⃣ Share your unique referral link
2️⃣ Friends join through your link
3️⃣ They must join our channel
4️⃣ You earn 1 point per referral
5️⃣ Withdraw rewards at 3 points

🎁 <b>Rewards:</b>
• 3 Points = Surfshark VPN Login
• More rewards coming soon!

💡 <b>Tips:</b>
• Share in social media groups
• Tell friends about channel benefits
• Stay active for bonus opportunities

📞 <b>Support:</b>
Contact: {OWNER_USERNAME}
Channel: @dailyb1ns

Happy earning! 🚀
"""
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    join_date = datetime.fromisoformat(user['joinDate']).strftime("%B %d, %Y")
    last_active = datetime.fromisoformat(user['lastActive']).strftime("%B %d, %Y at %H:%M")
    
    profile_text = f"""
👤 <b>Your Profile</b> 👤

🆔 <b>Basic Info:</b>
• Name: {user['first_name'] or 'Not Set'}
• Username: @{user['username'] or 'Not Set'}
• User ID: <code>{user_id}</code>

📅 <b>Activity:</b>
• Member Since: {join_date}
• Last Active: {last_active}
• Channel Member: {"✅ Yes" if user['joinedChannel'] else "❌ No"}

📊 <b>Statistics:</b>
• Total Points: {user['points']} 💰
• Total Referrals: {len(user['referrals'])} 👥
• Total Withdrawals: {user.get('totalWithdrawals', 0)} 🎁

🔗 <b>Referral Info:</b>
• Referred By: {"Yes" if user['referredBy'] else "No"}
• Status: {"🌟 Active Referrer" if user['points'] > 0 else "🔰 Getting Started"}
"""
    
    await update.message.reply_text(profile_text, parse_mode=ParseMode.HTML)

# Admin commands
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ This command is only for the bot owner.")
        return
    
    users = load_users()
    stats = load_stats()
    
    total_users = len(users)
    active_users = sum(1 for u in users.values() if u['joinedChannel'])
    total_points = sum(u['points'] for u in users.values())
    total_referrals = sum(len(u['referrals']) for u in users.values())
    
    # Recent activity (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    recent_users = sum(1 for u in users.values() 
                      if datetime.fromisoformat(u['lastActive']) > yesterday)
    
    stats_text = f"""
📊 <b>Bot Statistics</b> 📊

👥 <b>Users:</b>
• Total Users: {total_users}
• Active Members: {active_users}
• Recent Activity (24h): {recent_users}

💰 <b>Points & Referrals:</b>
• Total Points: {total_points}
• Total Referrals: {total_referrals}
• Total Withdrawals: {stats.get('total_withdrawals', 0)}

📈 <b>Performance:</b>
• Avg Points per User: {total_points/total_users if total_users > 0 else 0:.2f}
• Conversion Rate: {(active_users/total_users*100) if total_users > 0 else 0:.1f}%

🤖 <b>Bot Info:</b>
• Started: {datetime.fromisoformat(stats['bot_started']).strftime('%B %d, %Y')}
• Database Size: {total_users} records
"""
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ This command is only for the bot owner.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 <b>Broadcast Message</b>\n\n"
            "Usage: /broadcast <your message>\n\n"
            "Example: /broadcast Hello everyone! 🎉",
            parse_mode=ParseMode.HTML
        )
        return
    
    message = ' '.join(context.args)
    users = load_users()
    
    sent_count = 0
    failed_count = 0
    
    status_msg = await update.message.reply_text("📤 Starting broadcast...")
    
    for uid in users:
        try:
            await context.bot.send_message(int(uid), message, parse_mode=ParseMode.HTML)
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f'Failed to send broadcast to {uid}: {e}')
    
    await status_msg.edit_text(
        f"📢 <b>Broadcast Complete!</b>\n\n"
        f"✅ Sent: {sent_count}\n"
        f"❌ Failed: {failed_count}\n"
        f"📊 Total: {sent_count + failed_count}",
        parse_mode=ParseMode.HTML
    )

async def membership_required_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")]
    ]
    
    await update.message.reply_text(
        f"❌ <b>Channel Membership Required</b>\n\n"
        f"Please join our channel first:\n"
        f"{CHANNEL_LINK}\n\n"
        f"After joining, click '✅ Check Membership'.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Message handler for button presses
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "👥 Refer Friends":
        await refer_friends(update, context)
    elif text == "🔢 My Stats":
        await my_stats(update, context)
    elif text == "💰 Withdraw Reward":
        await withdraw_reward(update, context)
    elif text == "🏆 Leaderboard":
        await leaderboard(update, context)
    elif text == "ℹ️ Help":
        await help_command(update, context)
    elif text == "👤 Profile":
        await profile(update, context)
    elif text == "📊 Bot Stats" and user_id == OWNER_ID:
        await admin_stats(update, context)
    elif text == "🔙 Back to Main":
        await update.message.reply_text(
            "🔙 Back to main menu",
            reply_markup=get_main_keyboard()
        )

def main():
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(check_membership_callback, pattern="check_membership"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    print("🤖 Bot started successfully!")
    application.run_polling()

if __name__ == '__main__':
    main()