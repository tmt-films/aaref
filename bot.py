# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram import filters, Client, errors, enums
from pyrogram.errors import UserNotParticipant, UserIsBlocked, PeerIdInvalid
from pyrogram.errors.exceptions.flood_420 import FloodWait
from database import (
    add_user, add_group, all_users, all_groups, users, remove_user,
    update_referral_target, create_referral, get_referral_target_for_chat,
    get_referral_by_code, add_referred_user_to_record, increment_referral_count,
    mark_referral_approved, get_referral_status_for_user,
    get_pending_referrals, update_last_reminder_timestamp,
    get_all_pending_referrals_for_user
)
from configs import cfg
import random, asyncio
import uuid
from datetime import datetime, timedelta

# Helper function for referral link generation
def generate_referral_link(bot_username: str, chat_id: int) -> tuple[str, str]:
    """
    Generates a unique referral code and a deep-link for bot-based referrals.
    """
    referral_code = uuid.uuid4().hex[:8]
    # Ensure chat_id is string for consistent link formatting
    str_chat_id = str(chat_id).replace("-", "") # Remove hyphen for deep links if it's a group/channel ID like -100...
    referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}_{str_chat_id}"
    return referral_code, referral_link

app = Client(
    "approver",
    api_id=cfg.API_ID,
    api_hash=cfg.API_HASH,
    bot_token=cfg.BOT_TOKEN
)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Main process ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_chat_join_request(filters.group | filters.channel)
async def handle_chat_join_request(client: Client, m: Message):
    chat_id_str = str(m.chat.id)
    user_id_str = str(m.from_user.id)
    chat_title = m.chat.title
    user_mention = m.from_user.mention

    # Ensure group and user are in the database
    add_group(chat_id_str) # Initializes with referral_target = 0 if new
    add_user(user_id_str)

    try:
        bot_username = (await client.get_me()).username
        target_referrals = get_referral_target_for_chat(chat_id_str)

        if target_referrals > 0:
            # Referral needed
            referral_code, referral_link = generate_referral_link(bot_username, m.chat.id) # m.chat.id is int here

            # Create invite record in DB
            # generate_referral_link returns chat_id part of link without '-',
            # but DB create_referral should use original chat_id_str
            create_referral( # Internal function, 'referral_code' is DB key
                user_id=user_id_str,
                chat_id=chat_id_str, # Original chat_id with potential hyphen
                referral_code=referral_code,
                target_referrals=target_referrals
            )

            # User-facing message uses "invite"
            invite_link = referral_link

            pm_text_intro = (
                f"⏳ Your request to join **{chat_title}** is pending.\n\n"
                f"To be approved, you need to invite **{target_referrals}** friend(s) using your personal invite link."
            )
            pm_text_link_info = "Your invite link will be sent in the next message (for easy copying)."

            full_intro_message = f"{pm_text_intro}\n\n{pm_text_link_info}"

            try:
                await client.send_message(m.from_user.id, full_intro_message)

                # Send the invite link in a separate message
                await client.send_message(m.from_user.id, f"Your personal invite link for **{chat_title}**:\n{invite_link}")

                # Send message with buttons
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("❓ How Invites Work", callback_data=f"how_invites_work_{chat_id_str}")],
                    # [InlineKeyboardButton("🔗 Get My Invite Link", callback_data=f"copy_invite_link_{referral_code}")] # For later
                ])
                await client.send_message(m.from_user.id, "Use the button below for more info or to manage your invites:", reply_markup=keyboard)

            except (UserIsBlocked, PeerIdInvalid):
                print(f"Failed to send invite details PM to {user_id_str}: User blocked or not started bot.")
            except Exception as e:
                print(f"Error sending PM to {user_id_str}: {e}")

            # Optionally, notify admins (internal log, "referrals" is fine)
            # Example: await client.send_message(ADMIN_CHAT_ID, f"User {user_mention} ({user_id_str}) has a pending join request for {chat_title} requiring {target_referrals} invites.")

        else:
            # No invite needed or system disabled for this chat, approve directly
            await client.approve_chat_join_request(m.chat.id, m.from_user.id)
            welcome_message = f"**Hello {user_mention}!\nWelcome To {chat_title}\n\n__Powered By : @VJ_Botz __**"
            try:
                await client.send_message(m.from_user.id, welcome_message)
            except (UserIsBlocked, PeerIdInvalid):
                print(f"Failed to send welcome PM to {user_id_str} for {chat_title}: User blocked or not started bot.")
            except Exception as e:
                print(f"Error sending welcome PM to {user_id_str}: {e}")

    except Exception as err:
        print(f"Error in on_chat_join_request for chat {chat_id_str}, user {user_id_str}: {err}")
        # Fallback: Maybe try to approve if all else fails, or just log
        # For now, if there's an error in the main logic, it won't auto-approve to be safe.
 
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Start ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def handle_referral_start(client: Client, m: Message, start_payload: str, bot_username: str):
    new_user_id_str = str(m.from_user.id)
    new_user_mention = m.from_user.mention

    try:
        parts = start_payload.split("_")
        if len(parts) != 3 or parts[0] != "ref": # 'ref' in payload is an internal marker
            # Not a valid invite payload structure, fall back to normal start
            return False # Indicates fallback needed

        referral_code_from_link = parts[1] # This is the internal referral_code
        # chat_id_str_from_link = parts[2] # This is the modified one, not directly used for DB lookup of original chat_id

        referral_data = get_referral_by_code(referral_code_from_link) # Fetches DB record

        if not referral_data:
            await m.reply_text("Invalid or expired invite link. Proceeding with normal start.")
            return False # Fallback

        original_referrer_id_str = referral_data["user_id"] # Internal field name
        target_chat_id_for_referral = referral_data["chat_id"] # This is the original chat_id (e.g., -100xxxx)

        try:
            target_chat = await client.get_chat(target_chat_id_for_referral)
            target_chat_title = target_chat.title
        except Exception as e:
            print(f"Error fetching chat title for {target_chat_id_for_referral}: {e}")
            target_chat_title = "the target chat" # Fallback title

        if new_user_id_str == original_referrer_id_str:
            await m.reply_text(f"You cannot use your own invite link for {target_chat_title}.")
            # Even if self-referral, they might need their own link for this chat if not already having one.
            # This part will be handled by the subsequent "Process the New User" logic.

        else: # Not a self-invite, process the increment for the original referrer
            user_newly_added_to_record = add_referred_user_to_record(referral_code_from_link, new_user_id_str)

            if not user_newly_added_to_record:
                await m.reply_text(f"You have already been counted for this invite link for {target_chat_title}.")
                # Continue to process the new user for their own potential invite task for this chat.
            else:
                # New user successfully added to referrer's list, increment count for referrer
                increment_referral_count(referral_code_from_link, original_referrer_id_str)
                referrer_status = get_referral_status_for_user(original_referrer_id_str, target_chat_id_for_referral)

                if referrer_status:
                    try:
                        referrer_message_text = (
                            f"🎉 Good news! {new_user_mention} used your invite link for **{target_chat_title}**.\n"
                            f"Your progress: {referrer_status['referrals_count']}/{referrer_status['target_referrals']} invites."
                        )
                        referrer_keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("📊 Check My Full Status", callback_data="trigger_myreferralstatus")]
                        ])
                        await client.send_message(
                            original_referrer_id_str,
                            referrer_message_text,
                            reply_markup=referrer_keyboard
                        )
                    except (UserIsBlocked, PeerIdInvalid):
                        print(f"Failed to send invite progress to {original_referrer_id_str}: User blocked or not started bot.")
                    except Exception as e:
                        print(f"Error sending PM to original referrer {original_referrer_id_str}: {e}")

                    # Check for referrer's task completion
                    if referrer_status['referrals_count'] >= referrer_status['target_referrals'] and not referrer_status['is_approved']:
                        try:
                            await client.approve_chat_join_request(target_chat_id_for_referral, original_referrer_id_str)
                            mark_referral_approved(original_referrer_id_str, target_chat_id_for_referral)
                            # User already notified of progress, separate approval message is good
                            await client.send_message(
                                original_referrer_id_str,
                                f"✅ Congratulations! You've completed the invite task for **{target_chat_title}** and your join request has been approved."
                            )
                        except Exception as e:
                            print(f"Error approving/notifying referrer {original_referrer_id_str} for chat {target_chat_id_for_referral}: {e}")

        # --- Process the New User (m.from_user.id) for the target_chat_id_for_referral ---
        # The new user has expressed intent to join target_chat_id_for_referral by clicking the invite link.

        target_invites_for_new_user = get_referral_target_for_chat(target_chat_id_for_referral) # "target_invites"
        existing_invite_for_new_user = get_referral_status_for_user(new_user_id_str, target_chat_id_for_referral) # "existing_invite"

        if existing_invite_for_new_user and existing_invite_for_new_user['is_approved']:
            await m.reply_text(f"Welcome! It seems you are already approved for **{target_chat_title}**.")

        elif target_invites_for_new_user <= 0:
            # Chat does not require invites for new members currently.
            await m.reply_text(
                f"You used an invite link for **{target_chat_title}**. " # "invite link"
                f"This group does not currently require invites for joining. " # "invites"
                f"You can try joining it directly if you haven't already."
            )
            # No direct approval here as this /start command is in PM, not in group join request context.

        else: # Chat requires invites, and user is not yet approved.
            if existing_invite_for_new_user: # They have a pending invite
                invite_link_for_existing_user = f"https://t.me/{bot_username}?start=ref_{existing_invite_for_new_user['referral_code']}_{str(target_chat_id_for_referral).replace('-', '')}"
                await m.reply_text(
                    f"You are already working on an invite task for **{target_chat_title}**.\n" # "invite task"
                    f"Your personal invite link: {invite_link_for_existing_user}\n" # "invite link"
                    f"Your progress: {existing_invite_for_new_user['count']}/{existing_invite_for_new_user['target']} invites." # "invites"
                )
            else: # New user, needs a new invite task for this chat
                new_user_ref_code, new_user_invite_link = generate_referral_link(bot_username, int(target_chat_id_for_referral))
                create_referral( # Internal function, field names (referral_code, target_referrals) remain
                    user_id=new_user_id_str,
                    chat_id=target_chat_id_for_referral,
                    referral_code=new_user_ref_code,
                    target_referrals=target_invites_for_new_user,
                    referred_by=original_referrer_id_str # Track who referred this new user
                )
                await m.reply_text(
                    f"You've used an invite link for **{target_chat_title}**.\n" # "invite link"
                    f"To complete your entry, you also need to invite **{target_invites_for_new_user}** friend(s).\n"
                    f"Your personal invite link will be sent next."
                )
                await client.send_message(m.from_user.id, f"Your personal invite link for **{target_chat_title}**:\n{new_user_invite_link}")

                invite_task_buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("❓ How Invites Work", callback_data=f"how_invites_work_{target_chat_id_for_referral}")],
                    # [InlineKeyboardButton("🔗 Get My Invite Link", callback_data=f"copy_invite_link_{new_user_ref_code}")]
                ])
                await client.send_message(m.from_user.id, "Use the button below for more info:", reply_markup=invite_task_buttons)

        return True # Indicates invite flow handled

    except Exception as e:
        print(f"Error in handle_referral_start: {e}") # Internal log
        await m.reply_text("An error occurred while processing the invite. Please try again later.") # "invite"
        return True # Error occurred, but we don't want to fall back to normal start image in this case.


@app.on_message(filters.private & filters.command("start"))
async def op(client: Client, m :Message):
    add_user(str(m.from_user.id)) # Add user at the beginning

    # Force subscribe check
    if cfg.CHID: # Check if CHID is set
        try:
            await client.get_chat_member(cfg.CHID, m.from_user.id)
        except UserNotParticipant:
            try:
                invite_link = await client.create_chat_invite_link(int(cfg.CHID))
                key = InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("🍿 Join Update Channel 🍿", url=invite_link.invite_link),
                        InlineKeyboardButton("🍀 Check Again 🍀", callback_data="chk_start") # Use a different callback_data
                    ]]
                )
                await m.reply_text("**⚠️Access Denied!⚠️\n\nPlease Join My Update Channel To Use Me. If You Joined The Channel Then Click On Check Again Button To Confirm.**", reply_markup=key)
                return
            except Exception as e:
                print(f"Error during force sub generation: {e}")
                await m.reply_text("**Make Sure I Am Admin In Your Update Channel And The Channel ID Is Correct.**")
                return
        except Exception as e:
            print(f"Error checking chat member for force sub: {e}")
            # Could be bot not in CHID or other issues
            await m.reply_text("There was an issue verifying your channel membership. Please try again later.")
            return

    bot_username = (await client.get_me()).username
    start_payload = m.command[1] if len(m.command) > 1 else None
    referral_handled = False

    if start_payload and start_payload.startswith("ref_"): # "ref_" is an internal marker
        invite_handled = await handle_referral_start(client, m, start_payload, bot_username) # "invite_handled"

    if not invite_handled: # "invite_handled"
        # Normal start or fallback from invite processing
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("🗯 Channel", url="https://t.me/vj_botz"), # This is generic, no change needed
                InlineKeyboardButton("💬 Support", url="https://t.me/vj_bot_disscussion")
            ]]
        )
        await m.reply_photo("https://graph.org/file/d57d6f83abb6b8d0efb02.jpg", caption="**🦊 Hello {}!\nI'm an auto approve [Admin Join Requests]({}) Bot.\nI can approve users in Groups/Channels.Add me to your chat and promote me to admin with add members permission.\n\n__Powered By : @VJ_Botz __**".format(m.from_user.mention, "https://t.me/telegram/153"), reply_markup=keyboard)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ callback ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_callback_query(filters.regex("chk_start")) # Changed from "chk" to avoid conflict if original "chk" had other use
async def chk_start_callback(client: Client, cb : CallbackQuery): # Renamed client and cb
    if cfg.CHID:
        try:
            await client.get_chat_member(cfg.CHID, cb.from_user.id)
        except UserNotParticipant:
            await cb.answer("🙅‍♂️ You have not joined my update channel yet. Please join and then click 'Check Again'. 🙅‍♂️", show_alert=True)
            return
        except Exception as e:
            print(f"Error in chk_start_callback checking member: {e}")
            await cb.answer("An error occurred while checking your membership. Please try again.", show_alert=True)
            return

    # If check is successful (or CHID not set), effectively restart the start command logic for this user
    # This will re-evaluate if they have a payload, or show normal start.
    # To do this, we can re-call the 'op' function's logic, or simplify by just sending the normal start message.
    # For simplicity here, we just show the normal start message after successful check.
    # A more complex way would be to re-parse m.command if that context was available or stored.

    await cb.answer("✅ Thanks for joining! You can now use the bot.", show_alert=True)
    # Remove the force-sub message and show the main start message
    await cb.message.delete() # remove the "Access Denied" message with buttons

    # Send the normal start message
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🗯 Channel", url="https://t.me/vj_botz"),
            InlineKeyboardButton("💬 Support", url="https://t.me/vj_bot_disscussion")
        ]]
    )
    # cb.message.reply_photo(...) doesn't exist. Need to use client.send_photo to cb.message.chat.id
    await client.send_photo(
        chat_id=cb.message.chat.id,
        photo="https://graph.org/file/d57d6f83abb6b8d0efb02.jpg",
        caption="**🦊 Hello {}!\nI'm an auto approve [Admin Join Requests]({}) Bot.\nI can approve users in Groups/Channels.Add me to your chat and promote me to admin with add members permission.\n\n__Powered By : @VJ_Botz __**".format(cb.from_user.mention, "https://t.me/telegram/153"),
        reply_markup=keyboard
    )
    # Original chk had add_user(m.from_user.id) which is already at start of 'op'
    # Original chk had cb.edit_text - but we are deleting and sending new message.

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ info ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("users") & filters.user(cfg.SUDO))
async def dbtool(_, m : Message):
    xx = all_users()
    x = all_groups()
    tot = int(xx + x)
    await m.reply_text(text=f"""
🍀 Chats Stats 🍀
🙋‍♂️ Users : `{xx}`
👥 Groups : `{x}`
🚧 Total users & groups : `{tot}` """)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Broadcast ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("bcast") & filters.user(cfg.SUDO))
async def bcast(_, m : Message):
    allusers = users
    lel = await m.reply_text("`⚡️ Processing...`")
    success = 0
    failed = 0
    deactivated = 0
    blocked = 0
    for usrs in allusers.find():
        try:
            userid = usrs["user_id"]
            #print(int(userid))
            if m.command[0] == "bcast":
                await m.reply_to_message.copy(int(userid))
            success +=1
        except FloodWait as ex:
            await asyncio.sleep(ex.value)
            if m.command[0] == "bcast":
                await m.reply_to_message.copy(int(userid))
        except errors.InputUserDeactivated:
            deactivated +=1
            remove_user(userid)
        except errors.UserIsBlocked:
            blocked +=1
        except Exception as e:
            print(e)
            failed +=1

    await lel.edit(f"✅Successfull to `{success}` users.\n❌ Faild to `{failed}` users.\n👾 Found `{blocked}` Blocked users \n👻 Found `{deactivated}` Deactivated users.")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Broadcast Forward ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("fcast") & filters.user(cfg.SUDO))
async def fcast(_, m : Message):
    allusers = users
    lel = await m.reply_text("`⚡️ Processing...`")
    success = 0
    failed = 0
    deactivated = 0
    blocked = 0
    for usrs in allusers.find():
        try:
            userid = usrs["user_id"]
            #print(int(userid))
            if m.command[0] == "fcast":
                await m.reply_to_message.forward(int(userid))
            success +=1
        except FloodWait as ex:
            await asyncio.sleep(ex.value)
            if m.command[0] == "fcast":
                await m.reply_to_message.forward(int(userid))
        except errors.InputUserDeactivated:
            deactivated +=1
            remove_user(userid)
        except errors.UserIsBlocked:
            blocked +=1
        except Exception as e:
            print(e)
            failed +=1

    await lel.edit(f"✅Successfull to `{success}` users.\n❌ Faild to `{failed}` users.\n👾 Found `{blocked}` Blocked users \n👻 Found `{deactivated}` Deactivated users.")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Referral Settings ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("referralsettings") & (filters.group | filters.channel))
async def handle_referral_settings(client: Client, m: Message):
    chat_id = m.chat.id
    user_id = m.from_user.id

    try:
        member = await m.chat.get_member(user_id)
        if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            await m.reply_text("You need to be an admin or owner to use this command.")
            return
    except errors.UserNotParticipant:
        await m.reply_text("You are not a member of this chat.")
        return
    except Exception as e:
        await m.reply_text(f"Error checking your permissions: {e}")
        return

    try:
        bot_member = await m.chat.get_member(app.me.id)
        if bot_member.status != enums.ChatMemberStatus.ADMINISTRATOR:
            await m.reply_text("I need to be an admin in this chat to manage referral settings.")
            return
    except Exception as e:
        await m.reply_text(f"Error checking my permissions: {e}")
        return

    if len(m.command) < 2:
        await m.reply_text("Usage: /referralsettings <number_of_referrals>. Set to 0 to disable.")
        return

    try:
        target_count = int(m.command[1])
        if target_count < 0:
            await m.reply_text("Number of referrals cannot be negative. Set to 0 to disable.")
            return
    except ValueError:
        await m.reply_text("Invalid number. Usage: /referralsettings <number_of_referrals>. Set to 0 to disable.")
        return

    try:
        update_referral_target(str(chat_id), target_count)
        if target_count == 0:
            await m.reply_text("Invite system disabled for this chat.") # "Invite system"
        else:
            await m.reply_text(f"Invite system updated. Users will now need to invite {target_count} friends to join.") # "Invite system", "invite X friends"
    except Exception as e:
        await m.reply_text(f"An error occurred while updating invite system settings: {e}") # "invite system settings"


print("I'm Alive Now!")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Reminder System ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def send_referral_reminders(client: Client): # Pass client instance
    print("Reminder task started.")
    await asyncio.sleep(15) # Initial delay to allow bot to fully start before first query

    bot_username = ""
    try:
        me = await client.get_me()
        bot_username = me.username
    except Exception as e:
        print(f"Error getting bot username in reminder task: {e}. Will retry.")
        # Reminder task will loop and try again if this fails

    while True:
        if not bot_username: # Try to get username if failed initially
            try:
                me = await client.get_me()
                bot_username = me.username
                print(f"Successfully fetched bot username: {bot_username}")
            except Exception as e:
                print(f"Error getting bot username in reminder loop: {e}. Skipping this cycle.")
                await asyncio.sleep(3600) # Wait before retrying username fetch
                continue

        try:
            pending_referrals = get_pending_referrals() # This is a synchronous DB call
            now = datetime.now() # Use a consistent 'now' for this batch

            for referral_doc in pending_referrals:
                try:
                    user_id = int(referral_doc["user_id"]) # Ensure user_id is int for sending message
                    chat_id = int(referral_doc["chat_id"]) # Ensure chat_id is int for get_chat and generate_link
                    referral_code = referral_doc["referral_code"]
                    target_referrals = referral_doc["target_referrals"]
                    current_referrals = referral_doc["referrals_count"]

                    # Timestamp from DB is already ISO string
                    timestamp_str = referral_doc["timestamp"]
                    initial_request_time = datetime.fromisoformat(timestamp_str)

                    last_reminder_time_str = referral_doc.get("last_reminder_sent_timestamp")
                    last_reminder_time = None
                    if last_reminder_time_str:
                        last_reminder_time = datetime.fromisoformat(last_reminder_time_str)

                    # Determine the base time for checking the 24-hour rule
                    time_to_check_against = last_reminder_time or initial_request_time

                    # Reminder if 24 hours passed since last reminder or initial request
                    # And if invites are still pending
                    if (now - time_to_check_against).total_seconds() > 24 * 3600 and current_referrals < target_referrals : # internal vars target_referrals, current_referrals

                        chat_title = "the chat" # Default
                        try:
                            chat = await client.get_chat(chat_id)
                            chat_title = chat.title
                        except Exception as e:
                            print(f"Reminder: Error getting chat title for chat_id {chat_id}: {e}")
                            # Continue with default title, or skip if chat is critical

                        _, invite_link = generate_referral_link(bot_username, chat_id) # invite_link variable

                        remaining_invites = target_referrals - current_referrals # remaining_invites
                        reminder_intro = (
                            f"🔔 Reminder for **{chat_title}**!\n\n"
                            f"You still need to invite **{remaining_invites}** more friend(s) to reach your goal of {target_referrals} invites.\n"
                            f"Your personal invite link is in the next message."
                        )

                        try:
                            await client.send_message(user_id, reminder_intro)
                            await client.send_message(user_id, f"Your invite link for **{chat_title}**:\n{invite_link}")

                            reminder_keyboard = InlineKeyboardMarkup([
                                [InlineKeyboardButton("📊 Check My Full Status", callback_data="trigger_myreferralstatus")],
                                # [InlineKeyboardButton("🔗 Get My Invite Link", callback_data=f"copy_invite_link_{referral_code}")]
                            ])
                            await client.send_message(user_id, "What would you like to do?", reply_markup=reminder_keyboard)

                            update_last_reminder_timestamp(referral_code, now) # Update DB (sync call)
                            print(f"Sent invite reminder to {user_id} for chat {chat_id} ({chat_title})")
                        except (UserIsBlocked, PeerIdInvalid):
                            print(f"Reminder: User {user_id} blocked the bot or chat is invalid. Skipping.")
                        except Exception as e:
                            print(f"Reminder: Error sending PM to {user_id}: {e}")

                except Exception as e:
                    print(f"Error processing one referral/invite doc in reminder: {e}. Doc: {referral_doc}") # Internal log

            # print(f"Reminder cycle finished. Found {len(list(pending_referrals))} pending. Sleeping for 1 hour.") # Internal log
        except Exception as e:
            print(f"Major error in reminder task loop: {e}") # Internal log

        await asyncio.sleep(3600) # Check pending invites every hour


# Schedule the reminder task
if __name__ == "__main__":
    pass

async def main_with_reminder():
    await app.start()
    print("Bot started! Reminder task will run in background.")
    asyncio.create_task(send_referral_reminders(app))
    await app.idle()

if __name__ == '__main__':
    print("Starting bot with reminder system...")
    asyncio.run(main_with_reminder())
else:
    # Simplified scheduling for when bot.py is imported
    # Assumes app is initialized and event loop is running or will be soon
    # This part might need adjustment based on the actual entry point (e.g., app.py)
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(send_referral_reminders(app))
    else:
        # For Pyrogram v1 that uses app.run(), this is a common pattern:
        app.loop.create_task(send_referral_reminders(app))
        # However, the current template uses app.run() at the end, suggesting v1 style or a compatible run method.
        # The previous `loop = asyncio.get_event_loop(); loop.create_task(); app.run()` is generally more robust for v1.
        # For now, sticking to the last working version of this block.
        # The diff shows `loop.create_task()` then `app.run()` which is fine.

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ My Invite Status (Helper and Command) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _send_my_referral_status(client: Client, user_id: int):
    user_id_str = str(user_id)

    user_pending_invites = get_all_pending_referrals_for_user(user_id_str)

    if not user_pending_invites:
        no_tasks_message = "You have no active invite tasks pending."
        overall_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_myreferralstatus")]
        ])
        await client.send_message(user_id, no_tasks_message)
        await client.send_message(user_id, "You can refresh your status anytime using the button below.", reply_markup=overall_keyboard)
        return

    bot_username = ""
    try:
        me = await client.get_me()
        bot_username = me.username
    except Exception as e:
        print(f"Error getting bot username in /myreferralstatus: {e}")
        await message.reply_text("Could not retrieve necessary bot information. Please try again later.")
        return

    status_header = "**Here's the status of your pending invites:**\n"
    await client.send_message(user_id, status_header)

    for referral_doc in user_pending_invites:
        chat_id_str = referral_doc["chat_id"]
        chat_id_int = int(chat_id_str)

        referral_code = referral_doc["referral_code"]
        current_count = referral_doc["referrals_count"]
        target_count = referral_doc["target_referrals"]

        chat_display_name = f"Chat ID: {chat_id_str}"
        try:
            chat = await client.get_chat(chat_id_int)
            chat_display_name = f"**Chat:** {chat.title}"
        except Exception as e:
            print(f"Error fetching chat title for {chat_id_str} in _send_my_referral_status: {e}")

        task_text = (
            f"\n{chat_display_name}\n"
            f"**Progress:** {current_count}/{target_count} invites.\n"
            f"--------------------"
        )

        task_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🔗 My Invite Link for this Chat", callback_data=f"get_specific_link_{referral_code}")]
        ])

        try:
            await client.send_message(user_id, task_text, reply_markup=task_keyboard)
        except Exception as e:
            print(f"Error sending individual task status for {chat_id_str} to {user_id}: {e}")
            await client.send_message(user_id, f"Could not display status for {chat_display_name}. An error occurred.")

    overall_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh Full Status", callback_data="refresh_myreferralstatus")]
    ])
    await client.send_message(user_id, "You can refresh your full status using the button below.", reply_markup=overall_keyboard)

@app.on_message(filters.command("myreferralstatus") & filters.private)
async def my_referral_status_command_handler(client: Client, message: Message):
    await _send_my_referral_status(client, message.from_user.id)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Callback Query Handlers ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_callback_query(filters.regex(r"^how_invites_work_"))
async def handle_how_invites_work(client: Client, cb: CallbackQuery):
    chat_id_str = cb.data.split("_", maxsplit=3)[-1] # Extracts the original chat_id

    try:
        chat_id_int = int(chat_id_str)
        target_invites = get_referral_target_for_chat(chat_id_str) # DB function uses string chat_id
        chat = await client.get_chat(chat_id_int) # Pyrogram uses int or string like "-100..."
        chat_title = chat.title

        explanation = (
            f"**How Invites Work for {chat_title}:**\n\n"
            "1. When you try to join, your request is held by me (the bot).\n"
            "2. I give you a unique personal invite link.\n"
            f"3. You need to share this link with **{target_invites}** friend(s).\n"
            "4. When a friend clicks your link and starts a chat with me, they are counted as your invite.\n"
            "5. If this group requires invites for *everyone*, your friends will also get their own invite tasks.\n"
            f"6. Once you reach {target_invites} invites, I will automatically approve your original join request for {chat_title}!\n\n"
            "You can check your progress using the /myreferralstatus command or the status buttons."
        )
        await client.send_message(cb.from_user.id, explanation)
        await cb.answer()
    except Exception as e:
        print(f"Error in handle_how_invites_work for chat_id {chat_id_str}: {e}")
        await client.send_message(cb.from_user.id, "Sorry, I couldn't retrieve the details for that chat.")
        await cb.answer("Error processing request.", show_alert=True)

@app.on_callback_query(filters.regex(r"^get_specific_link_"))
async def handle_get_specific_link(client: Client, cb: CallbackQuery):
    referral_code = cb.data.split("_", maxsplit=3)[-1]

    try:
        referral_data = get_referral_by_code(referral_code)
        if referral_data:
            chat_id_str = referral_data["chat_id"]
            chat_id_int = int(chat_id_str)

            bot_username = (await client.get_me()).username
            _, invite_link = generate_referral_link(bot_username, chat_id_int)

            chat_title = f"Chat ID {chat_id_str}" # Default
            try:
                chat = await client.get_chat(chat_id_int)
                chat_title = chat.title
            except Exception: # Chat might not be accessible
                pass

            await client.send_message(cb.from_user.id, f"Your personal invite link for **{chat_title}**:\n{invite_link}")
            await cb.answer()
        else:
            await client.send_message(cb.from_user.id, "Sorry, I couldn't find that specific invite link. It might be outdated or completed.")
            await cb.answer("Link not found.", show_alert=True)
    except Exception as e:
        print(f"Error in handle_get_specific_link for code {referral_code}: {e}")
        await client.send_message(cb.from_user.id, "An error occurred while fetching your link.")
        await cb.answer("Error processing request.", show_alert=True)

@app.on_callback_query(filters.regex(r"^(refresh_myreferralstatus|trigger_myreferralstatus)$"))
async def handle_refresh_trigger_status(client: Client, cb: CallbackQuery):
    try:
        await _send_my_referral_status(client, cb.from_user.id)
        if cb.data == "refresh_myreferralstatus":
            await cb.answer("Status refreshed!")
        else:
            await cb.answer() # For trigger_myreferralstatus, no specific alert needed
    except Exception as e:
        print(f"Error in handle_refresh_trigger_status for user {cb.from_user.id}: {e}")
        await cb.answer("Could not refresh status.", show_alert=True)
