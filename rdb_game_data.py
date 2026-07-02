"""
RDB游戏名称数据库加载器
提供对config/rdb_gamename.json的加载和查询接口
"""

import json
import os
import sys
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import re


class RDBGameData:
    """RDB游戏名称数据库加载和查询类"""
    
    _instance: Optional['RDBGameData'] = None
    _data: Dict[str, Dict[str, str]] = {}
    _data_crc: Dict[str, str] = {}
    
    def __new__(cls) -> 'RDBGameData':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化加载数据"""
        if not self._data:
            self._load_data()
    
    def _load_data(self) -> None:
        """加载rdb_gamename.json文件"""
        # 获取config目录路径
        if hasattr(sys, 'frozen') and sys.frozen:
            # 打包环境：使用exe所在目录
            base_dir = Path(sys.executable).parent
        else:
            # 开发环境：使用项目根目录
            base_dir = Path(__file__).parent

        config_dir = base_dir / "data"
        file_path = config_dir / "rdb_gamename.json"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            if self._data:
                self._data_crc.clear()
                for key, value in self._data.items():
                    crc = value.get('crc')
                    if crc:
                        self._data_crc[crc] = value
        except FileNotFoundError:
            raise FileNotFoundError(f"RDB游戏名称数据库文件不存在: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"RDB游戏名称数据库文件格式错误: {e}")
    
    def reload(self) -> None:
        """重新加载数据"""
        self._data.clear()
        self._data_crc.clear()
        self._load_data()
    
    def get_by_key(self, key: str) -> Optional[Dict[str, str]]:
        """根据key获取游戏信息
        
        Args:
            key: 游戏的key（通常是文件名或标识符）
            
        Returns:
            包含scrapername和system的字典，如果不存在则返回None
        """
        query = key.lower()
        query = re.sub(r"[^a-z0-9]", '', query)
        query = query.strip()
        return self._data.get(query)
    
    def get_scrapername(self, key: str) -> Optional[str]:
        """获取游戏的scrapername
        
        Args:
            key: 游戏的key
            
        Returns:
            scrapername，如果不存在则返回None
        """
        query = key.lower()
        query = re.sub(r"[^a-z0-9]", '', query)
        query = query.strip()
        game_info = self.get_by_key(query)
        return game_info.get('scrapername') if game_info else None
    
    def get_system(self, key: str) -> Optional[str]:
        """获取游戏的system
        
        Args:
            key: 游戏的key
            
        Returns:
            system，如果不存在则返回None
        """
        query = key.lower()
        query = re.sub(r"[^a-z0-9]", '', query)
        query = query.strip()
        game_info = self.get_by_key(query)
        return game_info.get('system') if game_info else None
    
    def search_by_scrapername(self, scrapername: str) -> list[str]:
        """根据scrapername搜索所有匹配的key
        
        Args:
            scrapername: 要搜索的游戏名称
            
        Returns:
            匹配的key列表
        """
        return [key for key, value in self._data.items() 
                if value.get('scrapername') == scrapername]
    
    def search_by_system(self, system: str) -> list[str]:
        """根据system搜索所有匹配的key
        
        Args:
            system: 要搜索的系统名称
            
        Returns:
            匹配的key列表
        """
        return [key for key, value in self._data.items() 
                if value.get('system') == system]
    
    def get_all_systems(self) -> list[str]:
        """获取所有系统列表
        
        Returns:
            去重后的系统列表
        """
        systems = set()
        for value in self._data.values():
            if 'system' in value:
                systems.add(value['system'])
        return sorted(list(systems))
    
    def get_all_keys(self) -> list[str]:
        """获取所有key列表
        
        Returns:
            所有key的列表
        """
        return list(self._data.keys())
    
    def get_total_count(self) -> int:
        """获取游戏总数
        
        Returns:
            游戏数量
        """
        return len(self._data)
    
    def exists(self, key: str) -> bool:
        """检查key是否存在
        
        Args:
            key: 要检查的key
            
        Returns:
            如果存在返回True，否则返回False
        """
        return key in self._data
    
    def get_all_data(self) -> Dict[str, Dict[str, str]]:
        """获取完整数据副本
        
        Returns:
            完整的数据字典副本
        """
        return self._data.copy()
    
    def get_by_crc(self, crc: str) -> Optional[Dict[str, str]]:
        """根据CRC值获取游戏信息
        
        Args:
            crc: 游戏的CRC值
            
        Returns:
            包含游戏信息的字典，如果不存在则返回None
        """
        return self._data_crc.get(crc)
    
    def exists_crc(self, crc: str) -> bool:
        """检查CRC是否存在
        
        Args:
            crc: 要检查的CRC值
            
        Returns:
            如果存在返回True，否则返回False
        """
        return crc in self._data_crc

if __name__ == "__main__":
    rdb_data = RDBGameData()
    print(rdb_data.get_by_crc('37E8B947'))