import json
import os
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any

class SubscriptionManager:
    def __init__(self, keys_file: str = "keys.json"):
        self.keys_file = keys_file
        self.ensure_keys_file_exists()
    
    def ensure_keys_file_exists(self):
        """التأكد من وجود ملف المفاتيح"""
        if not os.path.exists(self.keys_file):
            self.save_keys({})
    
    def load_keys(self) -> Dict[str, Any]:
        """تحميل المفاتيح من الملف"""
        try:
            with open(self.keys_file, "r", encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_keys(self, keys: Dict[str, Any]) -> None:
        """حفظ المفاتيح في الملف"""
        with open(self.keys_file, "w", encoding='utf-8') as f:
            json.dump(keys, f, indent=4, ensure_ascii=False)
    
    def generate_unique_key(self) -> str:
        """توليد مفتاح فريد"""
        timestamp = int(datetime.now().timestamp())
        return f"KEY{timestamp}"
    
    def create_key(self, plan: str, custom_key: Optional[str] = None) -> Tuple[bool, str]:
        keys = self.load_keys()
        plan_durations = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1), 
            "monthly": timedelta(days=30),
            "yearly": timedelta(days=365)
        }
        
        if plan not in plan_durations:
            return False, "نوع خطة غير صحيح. الأنواع المتاحة: daily, weekly, monthly, yearly"
        
        key = custom_key if custom_key else self.generate_unique_key()
        if key in keys:
            return False, "المفتاح موجود بالفعل"
        
        now = datetime.now()
        expire_at = now + plan_durations[plan]
        
        keys[key] = {
            "plan": plan,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "expire_at": expire_at.strftime("%Y-%m-%d %H:%M:%S"),
            "active": True,
            "owner_id": None,
            "used_at": None
        }
        
        self.save_keys(keys)
        return True, key
    
    def activate_key(self, key: str, user_id: int) -> Tuple[bool, str]:
        keys = self.load_keys()
        if key not in keys:
            return False, "مفتاح غير صحيح"
        
        key_data = keys[key]
        if not key_data.get("active", False):
            return False, "المفتاح محظور أو مجمد"
        
        expire_at = datetime.strptime(key_data["expire_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expire_at:
            key_data["active"] = False
            self.save_keys(keys)
            return False, "المفتاح منتهي الصلاحية"
        
        if key_data.get("owner_id") is not None and key_data.get("owner_id") != user_id:
            return False, "المفتاح مستخدم من قبل مستخدم آخر"
        
        key_data["owner_id"] = user_id
        key_data["used_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_keys(keys)
        
        return True, f"تم تفعيل الاشتراك بنجاح! ينتهي في: {key_data['expire_at']}"
    
    def check_user_subscription(self, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        keys = self.load_keys()
        for key, data in keys.items():
            if data.get("owner_id") == user_id and data.get("active", False):
                expire_at = datetime.strptime(data["expire_at"], "%Y-%m-%d %H:%M:%S")
                if datetime.now() < expire_at:
                    return True, {
                        "key": key,
                        "plan": data["plan"],
                        "expire_at": data["expire_at"],
                        "days_left": (expire_at - datetime.now()).days
                    }
                else:
                    data["active"] = False
                    self.save_keys(keys)
                    return False, {"message": "انتهت صلاحية اشتراكك"}
        return False, {"message": "لا يوجد اشتراك نشط"}
    
    def get_key_info(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        keys = self.load_keys()
        if key not in keys:
            return False, {"message": "مفتاح غير موجود"}
        
        key_data = keys[key]
        expire_at = datetime.strptime(key_data["expire_at"], "%Y-%m-%d %H:%M:%S")
        return True, {
            "plan": key_data["plan"],
            "created_at": key_data.get("created_at", "غير معروف"),
            "expire_at": key_data["expire_at"],
            "active": key_data.get("active", False),
            "owner_id": key_data.get("owner_id"),
            "used_at": key_data.get("used_at"),
            "expired": datetime.now() > expire_at,
            "days_left": (expire_at - datetime.now()).days if datetime.now() < expire_at else 0
        }
    
    def ban_key(self, key: str) -> Tuple[bool, str]:
        keys = self.load_keys()
        if key not in keys:
            return False, "مفتاح غير موجود"
        
        keys[key]["active"] = False
        self.save_keys(keys)
        return True, f"تم حظر المفتاح {key}"
    
    def unban_key(self, key: str) -> Tuple[bool, str]:
        keys = self.load_keys()
        if key not in keys:
            return False, "مفتاح غير موجود"
        
        expire_at = datetime.strptime(keys[key]["expire_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expire_at:
            return False, "لا يمكن إلغاء حظر مفتاح منتهي الصلاحية"
        
        keys[key]["active"] = True
        self.save_keys(keys)
        return True, f"تم إلغاء حظر المفتاح {key}"
    
    def extend_key(self, key: str, days: int) -> Tuple[bool, str]:
        keys = self.load_keys()
        if key not in keys:
            return False, "مفتاح غير موجود"
        
        current_expire = datetime.strptime(keys[key]["expire_at"], "%Y-%m-%d %H:%M:%S")
        new_expire = current_expire + timedelta(days=days)
        keys[key]["expire_at"] = new_expire.strftime("%Y-%m-%d %H:%M:%S")
        keys[key]["active"] = True
        self.save_keys(keys)
        return True, f"تم تمديد المفتاح {days} يوم. الصلاحية الجديدة: {keys[key]['expire_at']}"
    
    def get_all_keys(self) -> Dict[str, Any]:
        keys = self.load_keys()
        result = {}
        for key, data in keys.items():
            expire_at = datetime.strptime(data["expire_at"], "%Y-%m-%d %H:%M:%S")
            result[key] = {
                **data,
                "expired": datetime.now() > expire_at,
                "days_left": (expire_at - datetime.now()).days if datetime.now() < expire_at else 0,
                "status": self._get_key_status(data, expire_at)
            }
        return result
    
    def _get_key_status(self, key_data: Dict[str, Any], expire_at: datetime) -> str:
        if not key_data.get("active", False):
            return "محظور"
        elif datetime.now() > expire_at:
            return "منتهي"
        elif key_data.get("owner_id") is None:
            return "غير مستخدم"
        else:
            return "نشط"
    
    def cleanup_expired_keys(self) -> int:
        keys = self.load_keys()
        cleaned = 0
        for key, data in keys.items():
            expire_at = datetime.strptime(data["expire_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expire_at and data.get("active", False):
                data["active"] = False
                cleaned += 1
        self.save_keys(keys)
        return cleaned
    
    def get_user_keys(self, user_id: int) -> Dict[str, Any]:
        keys = self.load_keys()
        user_keys = {}
        for key, data in keys.items():
            if data.get("owner_id") == user_id:
                expire_at = datetime.strptime(data["expire_at"], "%Y-%m-%d %H:%M:%S")
                user_keys[key] = {
                    **data,
                    "expired": datetime.now() > expire_at,
                    "days_left": (expire_at - datetime.now()).days if datetime.now() < expire_at else 0,
                    "status": self._get_key_status(data, expire_at)
                }
        return user_keys
