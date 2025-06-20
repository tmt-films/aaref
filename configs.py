# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API_ID
    api_id_str = getenv("API_ID")
    if api_id_str is None or not api_id_str.strip():
        raise ValueError("API_ID environment variable is missing or empty. Please set it in your .env file or environment.")
    try:
        API_ID = int(api_id_str)
    except ValueError:
        raise ValueError(f"API_ID '{api_id_str}' is not a valid integer.")

    # API_HASH
    API_HASH = getenv("API_HASH", "")
    if not API_HASH:
        # Depending on strictness, you might want to raise an error if it's absolutely required.
        # For now, allowing empty string as per original logic.
        print("Warning: API_HASH is not set. This is likely required for the bot to function.")


    # BOT_TOKEN
    BOT_TOKEN = getenv("BOT_TOKEN", "")
    if not BOT_TOKEN:
        # Similarly, BOT_TOKEN is critical.
        raise ValueError("BOT_TOKEN environment variable is missing or empty. This is required.")

    # CHID (Force Subscribe Channel ID)
    chid_str = getenv("CHID")
    if chid_str is None or not chid_str.strip():
        # CHID is used for force subscribe, making it critical.
        raise ValueError("CHID environment variable is missing or empty. Please set it for the force subscribe feature.")
    try:
        CHID = int(chid_str)
    except ValueError:
        raise ValueError(f"CHID '{chid_str}' is not a valid integer.")

    # SUDO (Admin/Owner IDs)
    sudo_str = getenv("SUDO", "")
    if not sudo_str.strip():
        SUDO = []  # Default to an empty list if SUDO is not set
    else:
        try:
            SUDO = list(map(int, sudo_str.split()))
        except ValueError:
            # This error occurs if any part of the split string cannot be converted to int
            raise ValueError(f"SUDO string '{sudo_str}' contains non-integer values or is improperly formatted.")

    # MONGO_URI
    MONGO_URI = getenv("MONGO_URI", "")
    if not MONGO_URI:
        # MongoDB is critical for database operations.
        raise ValueError("MONGO_URI environment variable is missing or empty. This is required for database connectivity.")
    
cfg = Config()

# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01
