import json
import os
from typing import Dict, Any, Optional
from config import DATABASE_FILE

class Database:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """Загружает данные из файла базы данных"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {"users": {}, "psychological_maps": {}}
        return {"users": {}, "psychological_maps": {}}
    
    def _save_data(self):
        """Сохраняет данные в файл базы данных"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def get_user_state(self, user_id: int) -> Optional[str]:
        """Получает текущее состояние пользователя"""
        return self.data.get("users", {}).get(str(user_id), {}).get("state")
    
    def set_user_state(self, user_id: int, state: str):
        """Устанавливает состояние пользователя"""
        if "users" not in self.data:
            self.data["users"] = {}
        
        if str(user_id) not in self.data["users"]:
            self.data["users"][str(user_id)] = {}
        
        self.data["users"][str(user_id)]["state"] = state
        self._save_data()
    
    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Получает данные пользователя"""
        return self.data.get("users", {}).get(str(user_id), {})
    
    def set_user_data(self, user_id: int, key: str, value: Any):
        """Устанавливает данные пользователя"""
        if "users" not in self.data:
            self.data["users"] = {}
        
        if str(user_id) not in self.data["users"]:
            self.data["users"][str(user_id)] = {}
        
        self.data["users"][str(user_id)][key] = value
        self._save_data()
    
    def save_psychological_map(self, user_id: int, map_data: Dict[str, Any]):
        """Сохраняет психологическую карту"""
        if "psychological_maps" not in self.data:
            self.data["psychological_maps"] = {}
        
        map_id = f"map_{user_id}_{len(self.data['psychological_maps']) + 1}"
        self.data["psychological_maps"][map_id] = {
            "user_id": user_id,
            "data": map_data,
            "status": "pending"  # pending, approved, rejected
        }
        self._save_data()
        return map_id
    
    def get_pending_maps(self) -> Dict[str, Any]:
        """Получает все карты на модерации"""
        pending_maps = {}
        for map_id, map_data in self.data.get("psychological_maps", {}).items():
            if map_data.get("status") == "pending":
                pending_maps[map_id] = map_data
        return pending_maps
    
    def approve_map(self, map_id: str):
        """Одобряет психологическую карту"""
        if map_id in self.data.get("psychological_maps", {}):
            self.data["psychological_maps"][map_id]["status"] = "approved"
            self._save_data()
    
    def reject_map(self, map_id: str):
        """Отклоняет психологическую карту"""
        if map_id in self.data.get("psychological_maps", {}):
            self.data["psychological_maps"][map_id]["status"] = "rejected"
            self._save_data()
    
    def get_user_maps(self, user_id: int) -> Dict[str, Any]:
        """Получает все карты пользователя"""
        user_maps = {}
        for map_id, map_data in self.data.get("psychological_maps", {}).items():
            if map_data.get("user_id") == user_id:
                user_maps[map_id] = map_data
        return user_maps 