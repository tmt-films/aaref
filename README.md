# VJ Auto Approve Bot

**👾 Hey I'll Accept New Telegram Channel Or Group Join Request. Easy To Use And Simple.**

**For Old Pending All Join Request Use This Repo [Click Here](https://github.com/VJBots/VJ-Join-Request-Acceptor-Bot)**

## 🚀 Demo Bot
- [Demo Bot](https://youtube.com/@TechVJ)

## How To Deploy [Video Tutorial](https://youtu.be/M76T4pKm6ks)

Before deploying or running locally, ensure you have all necessary dependencies installed:

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone https://github.com/VJBots/VJ-Auto-Approve-Bot.git
    cd VJ-Auto-Approve-Bot
    ```
2.  **Install dependencies:**
    Install the required Python packages using:
    ```bash
    pip install -r requirements.txt
    ```

Now, follow the video tutorial for deployment on platforms like Heroku, or set up environment variables for local execution.

## 🏷 Environment Variables

This project uses environment variables for configuration. A file named `sample.env` is included in the root of the repository, which lists all necessary variables.

**To set up your configuration for local development:**

1.  Make a copy of `sample.env` and rename it to `.env`.
    ```bash
    cp sample.env .env
    ```
    This project uses the `python-dotenv` library to automatically load variables from the `.env` file into the environment when the bot starts. This is convenient for local development.

2.  Open the `.env` file with a text editor.
3.  Fill in your actual values for each variable listed. Comments in the `sample.env` file explain what each variable is for.
4.  **Important (for local development):** The `.env` file contains your secret credentials. It is included in the `.gitignore` file to prevent accidental commitment to your repository. Do not share this file or commit it if it contains your live secrets.

(If you are deploying on a platform like Heroku or Railway, you will typically set these environment variables directly in the platform's dashboard settings instead of using a `.env` file.)

The required variables are:
  - `API_ID` - Your Telegram API ID.Get it [Here](my.telegram.org)
  - `API_HASH` - Your Telegram API HASH.Get it [Here](my.telegram.org)
  - `BOT_TOKEN` - Your Bot Token. Get it from [Here](https://t.me/BotFather)
  - `CHID` - Your Force subscribe channel id , And Make Bot Admin Here
  - `SUDO` - bot owners Id/ ids ( for broadcast and stats cmds). for multiple use space between each.
  - `MONGO_URI` - Mongodb database here, Watch [Video Tutorial](https://youtu.be/DAHRmFdw99o)

**Note on Configuration:** Ensure all required variables are set correctly either in your `.env` file (for local development) or in your deployment environment's settings. The bot now includes checks and will provide specific error messages at startup if critical variables like `API_ID`, `BOT_TOKEN`, `CHID`, or `MONGO_URI` are missing or improperly formatted.

## Invite System

This feature allows group/channel owners to require users to invite a certain number of new members before they are automatically approved to join. It's a great way to organically grow your community!

### For Group Admins

1.  **Bot Permissions:**
    *   The bot must be an admin in your group or channel.
    *   It needs the "Add Members" permission (or "Invite Users via Link" / "Manage Join Requests") to approve users and manage join requests.

2.  **Enabling & Configuring:**
    *   Use the `/referralsettings <number>` command in your group/channel (the bot needs to be a member to see the command).
    *   `<number>` is the number of successful invites a user needs to make to get approved.
    *   **Example:** `/referralsettings 5` - Sets the requirement to 5 invites.
    *   **To disable:** `/referralsettings 0` - Turns off the invite system for the chat, and new users will be approved directly (if the bot's main auto-approval function is active).

3.  **Important Note for Users:**
    *   The bot interacts with users via Private Message (PM) to give them their personal invite link and updates. Encourage your users to start a chat with the bot (`/start` command) if they haven't already, especially if they encounter issues receiving messages.

### For Users

1.  **Joining Process:**
    *   If you attempt to join a group/channel that has the invite system enabled, your join request will be marked as pending.
    *   The bot will send you a private message. This message will explain the invite requirement and provide:
        *   Your unique personal invite link (often in a separate message for easy copying).
        *   The number of friends you need to invite using this link.
    *   The bot uses interactive inline buttons to help you understand the process (e.g., "How Invites Work") and manage your invites.
    *   Share your unique personal invite link with friends. When a friend clicks your link and starts the bot, they will be associated with your invite.

2.  **Tracking Progress & Approval:**
    *   **For your referrer (the person whose link you used):** When you use someone's invite link to start the bot, their invite count is updated. If they reach their target, they get approved for the chat.
    *   **For you (the new user):** After you've used an invite link, the bot will tell you if *you* also need to invite others to join that specific chat.
        *   If the chat requires further invites from you, you'll get your own unique invite link and target number of invites.
        *   If the chat *doesn't* require further invites from you at that point (e.g., invites are off for new members, or you used an invite link for a chat that doesn't cascade the requirement), you will be instructed on how to join (usually by trying to join the chat directly if you haven't already).
    *   When you successfully invite the required number of friends (if applicable to you), the bot will automatically approve your join request for the group/channel.

3.  **Check Your Status:**
    *   Use the `/myreferralstatus` command in a private chat with the bot.
    *   The bot will show you all your active invite tasks (if any), your progress for each, and provides interactive buttons to get your unique invite links or refresh the status.

4.  **Reminders:**
    *   If your invite task is still pending, the bot will send you a reminder message approximately every 24 hours with your progress and invite link. Reminder messages also include quick action buttons, like checking your full status.
  
## 💫 Credits
 
 - <b>[Tech VJ](https://youtube.com/@Tech_VJ)</b>
