import os
import json
import hashlib
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# ============== MONGODB CONFIGURATION ==============
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://omar_admin:OmarHost2026@cluster0.mongodb.net/omar_host_db_v2?retryWrites=true&w=majority')
DB_NAME = 'omar_host_db_v2'

ADMIN_USERNAME = "OMAR_ADMIN"
ADMIN_PASSWORD = "OMAR_2026_BRO"

class MongoDBHandler:
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        try:
            self.client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[DB_NAME]
            self.connected = True
            self._initialize_collections()
        except Exception as e:
            print(f"⚠️ MongoDB Connection Failed: {e}")
            self.connected = False
    
    def _initialize_collections(self):
        if self.connected:
            if 'users' not in self.db.list_collection_names():
                admin_user = {
                    "_id": ADMIN_USERNAME,
                    "password": hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
                    "is_admin": True,
                    "created_at": str(datetime.now()),
                    "max_servers": 10
                }
                self.db['users'].insert_one(admin_user)
            
            if 'servers' not in self.db.list_collection_names():
                self.db.create_collection('servers')
    
    def load_db(self):
        if not self.connected: return {"users": {}, "servers": {}}
        try:
            users = {u.pop('_id'): u for u in self.db['users'].find()}
            servers = {s.pop('_id'): s for s in self.db['servers'].find()}
            return {"users": users, "servers": servers}
        except:
            return {"users": {}, "servers": {}}
    
    def save_db(self, db_data):
        if not self.connected: return
        try:
            # Update Users
            for uname, udata in db_data.get('users', {}).items():
                udata['_id'] = uname
                self.db['users'].replace_one({"_id": uname}, udata, upsert=True)
            # Update Servers
            for sname, sdata in db_data.get('servers', {}).items():
                sdata['_id'] = sname
                self.db['servers'].replace_one({"_id": sname}, sdata, upsert=True)
        except:
            pass

db_handler = MongoDBHandler()
