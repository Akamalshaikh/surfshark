const { Telegraf, Markup } = require('telegraf');
const fs = require('fs').promises;
const path = require('path');
const { DateTime } = require('luxon');

// Bot configuration
const BOT_TOKEN = '7907410427:AAEuOiI8lyaMl7OWnXMRIpYqzCHoaDtphNk';
const CHANNEL_ID = -1002771464366;
const CHANNEL_LINK = 'https://t.me/dailyb1ns';
const OWNER_ID = 6994528708;
const OWNER_USERNAME = '@its_soloz';

// Database files
const DB_FILE = path.join(__dirname, 'data', 'users.json');
const STATS_FILE = path.join(__dirname, 'data', 'bot_stats.json');

// --- Helper Functions for Data Persistence ---

async function loadData(filePath, defaultContent) {
    try {
        const data = await fs.readFile(filePath, 'utf8');
        // Handle case where file is empty but exists
        if (data.trim() === '') {
            console.log(`Database file at ${filePath} is empty, using default content.`);
            await fs.writeFile(filePath, JSON.stringify(defaultContent, null, 2));
            return defaultContent;
        }
        return JSON.parse(data);
    } catch (error) {
        // Handle both ENOENT (file not found) and SyntaxError (malformed JSON)
        if (error.code === 'ENOENT' || error instanceof SyntaxError) {
            console.error(`Error with database file at ${filePath}. Creating/resetting with default content.`, error.message);
            await fs.writeFile(filePath, JSON.stringify(defaultContent, null, 2));
            return defaultContent;
        }
        console.error(`Unexpected error loading data from ${filePath}:`, error);
        return defaultContent;
    }
}

async function saveData(filePath, data) {
    try {
        await fs.writeFile(filePath, JSON.stringify(data, null, 2));
    } catch (error) {
        console.error(`Error saving data to ${filePath}:`, error);
    }
}

async function loadUsers() {
    return loadData(DB_FILE, {});
}

async function saveUsers(users) {
    return saveData(DB_FILE, users);
}

async function loadStats() {
    const defaultStats = {
        total_users: 0,
        total_referrals: 0,
        total_withdrawals: 0,
        'bot_started': DateTime.now().toISO()
    };
    const stats = await loadData(STATS_FILE, defaultStats);
    if (!stats.bot_started) {
        stats.bot_started = defaultStats.bot_started;
        await saveStats(stats);
    }
    return stats;
}

async function saveStats(stats) {
    return saveData(STATS_FILE, stats);
}

// --- User Management Functions ---

async function getUser(userId) {
    const users = await loadUsers();
    const userKey = String(userId);

    if (!users[userKey]) {
        users[userKey] = {
            id: userId,
            username: '',
            first_name: '',
            referredBy: null,
            referrals: [],
            points: 0,
            joinedChannel: false,
            joinDate: DateTime.now().toISO(),
            lastActive: DateTime.now().toISO(),
            totalWithdrawals: 0
        };
        await saveUsers(users);

        const stats = await loadStats();
        stats.total_users = Object.keys(users).length;
        await saveStats(stats);
    } else {
        // Migration logic for existing users
        const user = users[userKey];
        const defaultFields = {
            username: '',
            first_name: '',
            referredBy: null,
            referrals: [],
            points: 0,
            joinedChannel: false,
            joinDate: DateTime.now().toISO(),
            lastActive: DateTime.now().toISO(),
            totalWithdrawals: 0
        };

        let updated = false;
        for (const field in defaultFields) {
            if (user[field] === undefined) {
                user[field] = defaultFields[field];
                updated = true;
            }
        }
        if (!Array.isArray(user.referrals)) {
            user.referrals = [];
            updated = true;
        }
        if (typeof user.points !== 'number') {
            user.points = 0;
            updated = true;
        }

        if (updated) {
            users[userKey] = user;
            await saveUsers(users);
        }
    }

    return users[userKey];
}

async function updateUser(userId, updates) {
    const users = await loadUsers();
    const userKey = String(userId);
    if (users[userKey]) {
        Object.assign(users[userKey], updates);
        users[userKey].lastActive = DateTime.now().toISO();
        await saveUsers(users);
        return users[userKey];
    }
    return null;
}

// --- Utility Functions ---

async function checkMembership(ctx, userId) {
    try {
        const chatMember = await ctx.telegram.getChatMember(CHANNEL_ID, userId);
        const isMember = ['creator', 'administrator', 'member'].includes(chatMember.status);
        await updateUser(userId, { joinedChannel: isMember });
        return isMember;
    } catch (e) {
        console.error('Error checking membership:', e);
        return false;
    }
}

function getMainMenuKeyboard() {
    return Markup.keyboard([
        ['👥 Refer Friends', '🔢 My Stats'],
        ['💰 Withdraw Reward', '🏆 Leaderboard'],
        ['ℹ️ Help', '👤 Profile']
    ]).resize();
}

function getAdminMenuKeyboard() {
    return Markup.keyboard([
        ['📊 Bot Stats', '📢 Broadcast'],
        ['👥 User List', '🔄 Backup Data'],
        ['🚫 Ban User', '✅ Unban User'],
        ['🔙 Back to Main']
    ]).resize();
}

// --- Bot Handlers ---

const bot = new Telegraf(BOT_TOKEN);

bot.start(async (ctx) => {
    const userId = ctx.from.id;
    await getUser(userId); // Ensure user exists

    // Update user info
    await updateUser(userId, {
        username: ctx.from.username || '',
        first_name: ctx.from.first_name || ''
    });

    // Check for referral code
    const referrerId = ctx.startPayload;
    if (referrerId && !isNaN(parseInt(referrerId)) && parseInt(referrerId) !== userId) {
        const user = await getUser(userId);
        if (!user.referredBy) {
            const referrer = await getUser(parseInt(referrerId));
            if (referrer) {
                await updateUser(userId, { referredBy: parseInt(referrerId) });
            }
        }
    }

    const welcomeText = `
🎉 <b>Welcome to Daily Bins Referral Bot!</b> 🎉

Hello ${ctx.from.first_name}! 👋

🌟 <b>What you can earn:</b>
• 1 Point = 1 Successful Referral
• 3 Points = Surfshark VPN Login
• More rewards coming soon!

🔰 <b>How it works:</b>
1️⃣ Join our channel
2️⃣ Share your referral link
3️⃣ Earn points when friends join
4️⃣ Withdraw amazing rewards!

<b>Owner:</b> ${OWNER_USERNAME}
<b>Channel:</b> @dailyb1ns
    `;

    const keyboard = Markup.inlineKeyboard([
        Markup.button.url("📢 Join Channel", CHANNEL_LINK),
        Markup.button.callback("✅ Check Membership", "check_membership")
    ]);

    await ctx.replyWithHTML(welcomeText, keyboard);
});

bot.action('check_membership', async (ctx) => {
    await ctx.answerCbQuery();
    const userId = ctx.from.id;
    const isMember = await checkMembership(ctx, userId);

    if (isMember) {
        const user = await getUser(userId);
        const referrerId = user.referredBy;

        if (referrerId) {
            const referrer = await getUser(referrerId);
            if (!referrer.referrals.includes(userId)) {
                referrer.referrals.push(userId);
                referrer.points = (referrer.points || 0) + 1;
                await updateUser(referrerId, { referrals: referrer.referrals, points: referrer.points });

                const stats = await loadStats();
                stats.total_referrals = (stats.total_referrals || 0) + 1;
                await saveStats(stats);

                try {
                    await ctx.telegram.sendMessage(
                        referrerId,
                        `🎁 <b>New Referral!</b>\n\n` +
                        `<b>${ctx.from.first_name}</b> joined through your link!\n` +
                        `💰 You earned 1 point!\n` +
                        `🔢 Total points: ${referrer.points}\n\n` +
                        `Keep sharing to earn more! 🚀`,
                        { parse_mode: 'HTML' }
                    );
                } catch (e) {
                    console.error('Error notifying referrer:', e);
                }
            }
        }

        const successText = `
✅ <b>Membership Confirmed!</b>

Welcome to our community! 🎊

🌟 You can now:
• Generate your referral link
• Check your stats and points
• View the leaderboard
• Withdraw rewards when eligible

Use the menu below to get started! 👇
        `;

        await ctx.editMessageText(successText, { parse_mode: 'HTML' });
        await ctx.replyWithHTML("🎯 <b>Choose an option:</b>", getMainMenuKeyboard());

    } else {
        const text = `
❌ <b>Not a Member Yet!</b>

Please join our channel first:
${CHANNEL_LINK}

After joining, click '✅ Check Membership' again.
        `;
        const keyboard = Markup.inlineKeyboard([
            Markup.button.url("📢 Join Channel", CHANNEL_LINK),
            Markup.button.callback("✅ Check Membership", "check_membership")
        ]);
        await ctx.editMessageText(text, { parse_mode: 'HTML', reply_markup: keyboard });
    }
});

bot.hears('👥 Refer Friends', async (ctx) => {
    const userId = ctx.from.id;
    if (!await checkMembership(ctx, userId)) {
        return membershipRequiredMessage(ctx);
    }
    const user = await getUser(userId);
    const botInfo = await ctx.telegram.getMe();
    const referralLink = `https://t.me/${botInfo.username}?start=${userId}`;

    const points = user.points || 0;
    const referrals = user.referrals || [];
    const progressBar = "�".repeat(points) + "⬜".repeat(3 - points);

    const referralText = `
🔗 <b>Your Referral Link</b> 🔗

<code>${referralLink}</code>

📊 <b>Your Progress:</b>
${progressBar} (${points}/3)

👥 <b>Referrals:</b> ${referrals.length}
💰 <b>Points:</b> ${points}

🎯 <b>How to earn:</b>
1️⃣ Share your link with friends
2️⃣ Friends must join the channel
3️⃣ You get 1 point per referral
4️⃣ Withdraw rewards at 3 points!

💡 <b>Pro Tips:</b>
• Share in groups and social media
• Tell friends about our amazing content
• More referrals = better rewards!
    `;

    const keyboard = Markup.inlineKeyboard([
        Markup.button.url("📤 Share Link", `https://t.me/share/url?url=${encodeURIComponent(referralLink)}&text=${encodeURIComponent('Join this amazing Telegram channel and earn rewards!')}`),
        Markup.button.callback("📋 Copy Link", `copy_${userId}`)
    ]);

    await ctx.replyWithHTML(referralText, { reply_markup: keyboard });
});

bot.hears('🔢 My Stats', async (ctx) => {
    const userId = ctx.from.id;
    if (!await checkMembership(ctx, userId)) {
        return membershipRequiredMessage(ctx);
    }

    const user = await getUser(userId);
    const joinDateFormatted = DateTime.fromISO(user.joinDate).toFormat('MMMM dd, yyyy');
    const points = user.points || 0;
    const referrals = user.referrals || [];
    const firstName = user.first_name || 'User';
    const totalWithdrawals = user.totalWithdrawals || 0;

    const allUsers = await loadUsers();
    const userPoints = Object.values(allUsers).map(u => ({ id: u.id, points: u.points || 0 }));
    userPoints.sort((a, b) => b.points - a.points);
    const rank = userPoints.findIndex(u => u.id === userId) + 1;

    const statsText = `
📊 <b>Your Statistics</b> 📊

👤 <b>Profile:</b>
• Name: ${firstName}
• User ID: <code>${userId}</code>
• Joined: ${joinDateFormatted}

🏆 <b>Performance:</b>
• Rank: ${rank !== 0 ? '#' + rank : 'N/A'}
• Points: ${points} 💰
• Referrals: ${referrals.length} 👥
• Withdrawals: ${totalWithdrawals} 🎁

📈 <b>Progress:</b>
${"🟩".repeat(points)}${"⬜".repeat(3 - points)} (${points}/3)

${points >= 3 ? "✅ <b>You can withdraw your reward!</b>" : `🔄 <b>Need ${3 - points} more points to withdraw</b>`}
    `;
    await ctx.replyWithHTML(statsText);
});

bot.hears('💰 Withdraw Reward', async (ctx) => {
    const userId = ctx.from.id;
    if (!await checkMembership(ctx, userId)) {
        return membershipRequiredMessage(ctx);
    }
    const user = await getUser(userId);
    const points = user.points || 0;

    if (points >= 3) {
        const newPoints = points - 3;
        const newWithdrawals = (user.totalWithdrawals || 0) + 1;
        await updateUser(userId, { points: newPoints, totalWithdrawals: newWithdrawals });

        const stats = await loadStats();
        stats.total_withdrawals = (stats.total_withdrawals || 0) + 1;
        await saveStats(stats);

        try {
            const firstName = user.first_name || 'Unknown';
            const username = user.username || 'No username';
            await ctx.telegram.sendMessage(
                OWNER_ID,
                `🎁 <b>New Withdrawal Request!</b>\n\n` +
                `User: ${firstName} (@${username})\n` +
                `ID: <code>${userId}</code>\n` +
                `Reward: Surfshark VPN Login\n` +
                `Total Withdrawals: ${newWithdrawals}`,
                { parse_mode: 'HTML' }
            );
        } catch (e) {
            console.error('Error notifying owner:', e);
        }

        const successText = `
🎉 <b>Withdrawal Successful!</b> 🎉

Congratulations! Your reward has been processed.

🎁 <b>Reward:</b> Surfshark VPN Login
💰 <b>Points Used:</b> 3
🔢 <b>Remaining Points:</b> ${newPoints}

📩 <b>Next Steps:</b>
Please contact ${OWNER_USERNAME} to receive your reward.

🔄 <b>Continue Earning:</b>
Keep referring friends to earn more rewards!
Your journey doesn't end here! 🚀
        `;
        await ctx.replyWithHTML(successText);
    } else {
        const insufficientText = `
❌ <b>Insufficient Points</b>

💰 Current Points: ${points}
🎯 Required Points: 3
📊 Need: ${3 - points} more points

🚀 <b>How to earn more:</b>
• Share your referral link
• Invite more friends
• Each successful referral = 1 point

Keep going! You're almost there! 💪
        `;
        await ctx.replyWithHTML(insufficientText);
    }
});

bot.hears('🏆 Leaderboard', async (ctx) => {
    const userId = ctx.from.id;
    if (!await checkMembership(ctx, userId)) {
        return membershipRequiredMessage(ctx);
    }

    const users = await loadUsers();
    const userPoints = Object.values(users).filter(u => (u.points || 0) > 0);
    userPoints.sort((a, b) => (b.points || 0) - (a.points || 0));

    let leaderboardText = "🏆 <b>Top Referrers Leaderboard</b> 🏆\n\n";
    const medals = ["🥇", "🥈", "🥉"];

    for (let i = 0; i < Math.min(10, userPoints.length); i++) {
        const user = userPoints[i];
        const medal = medals[i] || `${i + 1}.`;
        const name = user.first_name || `User ${String(user.id).slice(0, 8)}`;
        const points = user.points || 0;
        const referrals = (user.referrals || []).length;
        if (user.id === userId) {
            leaderboardText += `${medal} <b>${name}</b> - ${points}💰 (${referrals}👥) ⭐\n`;
        } else {
            leaderboardText += `${medal} ${name} - ${points}💰 (${referrals}👥)\n`;
        }
    }

    if (userPoints.length === 0) {
        leaderboardText += "No active referrers yet. Be the first! 🚀";
    } else {
        const userRank = userPoints.findIndex(u => u.id === userId) + 1;
        if (userRank > 10) {
            leaderboardText += `\n...\n${userRank}. <b>You</b> - ${(await getUser(userId)).points}💰`;
        }
    }

    await ctx.replyWithHTML(leaderboardText);
});

bot.hears('ℹ️ Help', async (ctx) => {
    const helpText = `
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
Contact: ${OWNER_USERNAME}
Channel: @dailyb1ns

Happy earning! 🚀
    `;
    await ctx.replyWithHTML(helpText);
});

bot.hears('👤 Profile', async (ctx) => {
    const userId = ctx.from.id;
    const user = await getUser(userId);
    const joinDate = DateTime.fromISO(user.joinDate).toFormat("MMMM dd, yyyy");
    const lastActive = DateTime.fromISO(user.lastActive).toFormat("MMMM dd, yyyy 'at' HH:mm");

    const profileText = `
👤 <b>Your Profile</b> 👤

🆔 <b>Basic Info:</b>
• Name: ${user.first_name || 'Not Set'}
• Username: @${user.username || 'Not Set'}
• User ID: <code>${userId}</code>

📅 <b>Activity:</b>
• Member Since: ${joinDate}
• Last Active: ${lastActive}
• Channel Member: ${user.joinedChannel ? "✅ Yes" : "❌ No"}

📊 <b>Statistics:</b>
• Total Points: ${user.points || 0} 💰
• Total Referrals: ${(user.referrals || []).length} 👥
• Total Withdrawals: ${user.totalWithdrawals || 0} 🎁

🔗 <b>Referral Info:</b>
• Referred By: ${user.referredBy ? "Yes" : "No"}
• Status: ${user.points > 0 ? "🌟 Active Referrer" : "🔰 Getting Started"}
    `;
    await ctx.replyWithHTML(profileText);
});

// Admin command handlers
bot.hears('📊 Bot Stats', async (ctx) => {
    const userId = ctx.from.id;
    if (userId !== OWNER_ID) {
        return ctx.reply("❌ This command is only for the bot owner.");
    }
    const users = await loadUsers();
    const stats = await loadStats();
    
    const totalUsers = Object.keys(users).length;
    const activeUsers = Object.values(users).filter(u => u.joinedChannel).length;
    const totalPoints = Object.values(users).reduce((sum, u) => sum + (u.points || 0), 0);
    const totalReferrals = Object.values(users).reduce((sum, u) => sum + (u.referrals || []).length, 0);

    const yesterday = DateTime.now().minus({ days: 1 });
    const recentUsers = Object.values(users).filter(u => DateTime.fromISO(u.lastActive) > yesterday).length;

    const statsText = `
📊 <b>Bot Statistics</b> 📊

👥 <b>Users:</b>
• Total Users: ${totalUsers}
• Active Members: ${activeUsers}
• Recent Activity (24h): ${recentUsers}

💰 <b>Points & Referrals:</b>
• Total Points: ${totalPoints}
• Total Referrals: ${totalReferrals}
• Total Withdrawals: ${stats.total_withdrawals || 0}

📈 <b>Performance:</b>
• Avg Points per User: ${totalUsers > 0 ? (totalPoints / totalUsers).toFixed(2) : 0}
• Conversion Rate: ${totalUsers > 0 ? (activeUsers / totalUsers * 100).toFixed(1) : 0}%

🤖 <b>Bot Info:</b>
• Started: ${DateTime.fromISO(stats.bot_started).toFormat('MMMM dd, yyyy')}
• Database Size: ${totalUsers} records
    `;
    await ctx.replyWithHTML(statsText);
});

bot.command('broadcast', async (ctx) => {
    const userId = ctx.from.id;
    if (userId !== OWNER_ID) {
        return ctx.reply("❌ This command is only for the bot owner.");
    }
    const message = ctx.message.text.substring(ctx.message.text.indexOf(' ') + 1);
    if (!message) {
        return ctx.replyWithHTML(
            "📢 <b>Broadcast Message</b>\n\n" +
            "Usage: /broadcast &lt;your message&gt;\n\n" +
            "Example: /broadcast Hello everyone! 🎉"
        );
    }
    const users = await loadUsers();
    let sentCount = 0;
    let failedCount = 0;
    
    // Reply with a message that can be edited later
    const statusMsg = await ctx.replyWithHTML("📤 Starting broadcast...");

    for (const uid in users) {
        try {
            await ctx.telegram.sendMessage(Number(uid), message, { parse_mode: 'HTML' });
            sentCount++;
        } catch (e) {
            failedCount++;
            console.error(`Failed to send broadcast to ${uid}:`, e);
            // Check for the "bot was blocked by the user" error and continue
            if (e.response && e.response.error_code === 403 && e.response.description === 'Forbidden: bot was blocked by the user') {
                console.log(`User ${uid} has blocked the bot. Skipping...`);
                continue;
            }
        }
    }

    // Edit the initial status message with the final summary
    await ctx.telegram.editMessageText(
        statusMsg.chat.id,
        statusMsg.message_id,
        null, // inline_message_id is not used here
        `📢 <b>Broadcast Complete!</b>\n\n` +
        `✅ Sent: ${sentCount}\n` +
        `❌ Failed: ${failedCount}\n` +
        `📊 Total: ${sentCount + failedCount}`,
        { parse_mode: 'HTML' }
    );
});


// Fallback message for membership check
async function membershipRequiredMessage(ctx) {
    const keyboard = Markup.inlineKeyboard([
        Markup.button.url("📢 Join Channel", CHANNEL_LINK),
        Markup.button.callback("✅ Check Membership", "check_membership")
    ]);
    await ctx.replyWithHTML(
        `❌ <b>Channel Membership Required</b>\n\n` +
        `Please join our channel first:\n` +
        `${CHANNEL_LINK}\n\n` +
        `After joining, click '✅ Check Membership'.`,
        keyboard
    );
}

// Start the bot
async function startBot() {
    try {
        await loadStats(); // Initialize stats file
        bot.launch();
        console.log("🤖 Bot started successfully!");
    } catch (e) {
        console.error("Failed to start the bot:", e);
    }
}

startBot();
