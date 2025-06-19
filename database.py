# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

from pymongo import MongoClient
from configs import cfg
import datetime

client = MongoClient(cfg.MONGO_URI)

users = client['main']['users']
groups = client['main']['groups']
referrals = client['main']['referrals']

def already_db(user_id):
        user = users.find_one({"user_id" : str(user_id)})
        if not user:
            return False
        return True

def already_dbg(chat_id):
        group = groups.find_one({"chat_id" : str(chat_id)})
        if not group:
            return False
        return True

def add_user(user_id):
    in_db = already_db(user_id)
    if in_db:
        return
    return users.insert_one({"user_id": str(user_id)}) 

def remove_user(user_id):
    in_db = already_db(user_id)
    if not in_db:
        return 
    return users.delete_one({"user_id": str(user_id)})
    
def add_group(chat_id):
    in_db = already_dbg(chat_id)
    if in_db:
        return
    return groups.insert_one({"chat_id": str(chat_id), "referral_target": 0})

def update_referral_target(chat_id, target_count):
    return groups.update_one({"chat_id": str(chat_id)}, {"$set": {"referral_target": int(target_count)}})

def all_users():
    user = users.find({})
    usrs = len(list(user))
    return usrs

def all_groups():
    group = groups.find({})
    grps = len(list(group))
    return grps

# Referral functions
def create_referral(user_id, chat_id, referral_code, target_referrals, referred_by=None):
    # Check if a non-approved referral exists
    existing_referral = referrals.find_one({
        "user_id": str(user_id),
        "chat_id": str(chat_id),
        "is_approved": False
    })
    if existing_referral:
        # Update existing referral
        return referrals.update_one(
            {"_id": existing_referral["_id"]},
            {"$set": {
                "referral_code": str(referral_code),
                "target_referrals": int(target_referrals),
                "referred_by": str(referred_by) if referred_by else None,
                "timestamp": datetime.datetime.utcnow()
            }}
        )
    else:
        # Create new referral
        return referrals.insert_one({
            "user_id": str(user_id),
            "chat_id": str(chat_id),
            "referral_code": str(referral_code),
            "referred_by": str(referred_by) if referred_by else None,
            "referrals_count": 0,
            "target_referrals": int(target_referrals),
            "is_approved": False,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "referred_users_list": [],
            "last_reminder_sent_timestamp": None
        })

def get_referral_by_user_chat(user_id, chat_id):
    return referrals.find_one({"user_id": str(user_id), "chat_id": str(chat_id)})

def get_referral_by_code(referral_code):
    return referrals.find_one({"referral_code": str(referral_code)})

def increment_referral_count(referral_code, user_id_of_referrer):
    # This function might need adjustment based on how user_id_of_referrer is used.
    # Assuming it's to ensure the increment is for the correct referrer's code.
    return referrals.update_one(
        {"referral_code": str(referral_code), "user_id": str(user_id_of_referrer)},
        {"$inc": {"referrals_count": 1}}
    )

def mark_referral_approved(user_id, chat_id):
    return referrals.update_one(
        {"user_id": str(user_id), "chat_id": str(chat_id)},
        {"$set": {"is_approved": True}}
    )

def get_pending_referrals():
    return referrals.find({"is_approved": False})

def get_referral_status_for_user(user_id, chat_id):
    referral_entry = referrals.find_one({"user_id": str(user_id), "chat_id": str(chat_id)})
    if referral_entry:
        return {
            "count": referral_entry.get("referrals_count", 0),
            "target": referral_entry.get("target_referrals", 0),
            "is_approved": referral_entry.get("is_approved", False),
            "referral_code": referral_entry.get("referral_code")
        }
    return None

def add_referred_user_to_record(referral_code, new_user_id):
    # First, check if the user is already in the list
    referral_entry = referrals.find_one({"referral_code": str(referral_code)})
    if referral_entry and str(new_user_id) in referral_entry.get("referred_users_list", []):
        return False # User already referred

    # Add user to the list and then increment (or handle increment separately)
    result = referrals.update_one(
        {"referral_code": str(referral_code)},
        {"$addToSet": {"referred_users_list": str(new_user_id)}} # $addToSet prevents duplicates
    )
    return result.modified_count > 0 # Returns True if user was added, False otherwise

def get_referral_target_for_chat(chat_id_str: str) -> int:
    group = groups.find_one({"chat_id": str(chat_id_str)})
    if group and "referral_target" in group:
        try:
            return int(group["referral_target"])
        except ValueError:
            return 0 # Should not happen if data is clean
    return 0 # Default to 0 if not set, group not found, or target is invalid type

def update_last_reminder_timestamp(referral_code: str, timestamp: datetime.datetime):
    return referrals.update_one(
        {"referral_code": str(referral_code)},
        {"$set": {"last_reminder_sent_timestamp": timestamp.isoformat()}}
    )

def get_all_pending_referrals_for_user(user_id_str: str) -> list:
    return list(referrals.find({"user_id": str(user_id_str), "is_approved": False}))
