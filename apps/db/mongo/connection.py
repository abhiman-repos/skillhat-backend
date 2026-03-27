import os
from pymongo import MongoClient, errors
import certifi

_client = None


def get_client():
    global _client

    if _client:
        return _client

    mongo_uri = os.getenv("MONGO_URI")

    if not mongo_uri:
        raise ValueError("❌ MONGO_URI not found in environment")

    try:
        _client = MongoClient(
            mongo_uri,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000,
            retryWrites=True,
        )

        # ✅ Health check
        _client.admin.command("ping")

        print("✅ MongoDB connected")

    except errors.ServerSelectionTimeoutError as e:
        raise Exception(f"❌ MongoDB server timeout: {e}")

    except errors.ConnectionFailure as e:
        raise Exception(f"❌ MongoDB connection failed: {e}")

    except Exception as e:
        raise Exception(f"❌ Unexpected MongoDB error: {e}")

    return _client