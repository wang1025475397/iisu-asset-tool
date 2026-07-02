import json
import xml.etree.ElementTree as ET
import requests
import os
import zipfile
import tempfile
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# 简化的路径处理
import sys

def get_downloaded_dats_directory():
    """获取数据目录路径 - 统一使用用户目录"""
    # 无论开发环境还是打包环境，都使用用户目录
    return os.path.join(os.path.expanduser("~"), ".iisu_asset_tool", "downloaded_dats")

def get_games_by_crc_path():
    return os.path.join(get_downloaded_dats_directory(), "games_by_crc.json")

def ensure_app_directories():
    os.makedirs(get_downloaded_dats_directory(), exist_ok=True)




class EmuGifDataFetcher:
    """
    用于从 http://dat.emugif.com/update/ 获取和解析游戏数据的类
    """

    def __init__(self, base_url: str = "http://dat.emugif.com/update/", timeout: int = 30):
        """
        初始化EmuGifDataFetcher实例
        
        Args:
            base_url (str): 数据源URL
            timeout (int): 请求超时时间（秒）
        """
        self.base_url = base_url
        self.timeout = timeout

    def fix_xml_content(self, xml_content: str) -> str:
        """
        修复非标准XML内容，使其可以被正确解析

        Args:
            xml_content (str): 原始XML内容

        Returns:
            str: 修复后的XML内容
        """
        if not isinstance(xml_content, str):
            print("XML内容不是字符串类型")
            return ""
            
        # 修复未转义的&符号
        # 在XML中，&符号应该被转义为&amp;
        # 但要注意不要重复转义已经正确的转义序列
        try:
            fixed_content = re.sub(r'&(?!(amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;))', '&amp;', xml_content)
            return fixed_content
        except Exception as e:
            print(f"修复XML内容时出错: {e}")
            return xml_content

    def parse_xml_data(self, xml_content: str) -> Optional[Dict]:
        """
        解析XML数据并转换为JSON格式

        Args:
            xml_content (str): XML格式的数据

        Returns:
            dict: 解析后的JSON数据，出错时返回None
        """
        if not xml_content:
            print("XML内容为空")
            return None
            
        try:
            # 修复XML内容
            fixed_xml = self.fix_xml_content(xml_content)
            if not fixed_xml:
                return None

            # 解析XML内容
            root = ET.fromstring(fixed_xml)

            # 构建数据结构
            result = {
                "datfiles": []
            }

            # 遍历所有datfile节点
            for datfile in root.findall('datfile'):
                datfile_info = {}
                for child in datfile:
                    if child.text is not None:
                        datfile_info[child.tag] = child.text
                    else:
                        datfile_info[child.tag] = ""
                result["datfiles"].append(datfile_info)

            return result
        except ET.ParseError as e:
            print(f"解析XML时出错: {e}")
            return None
        except Exception as e:
            print(f"解析XML数据时发生未知错误: {e}")
            return None

    def fetch_data(self) -> Optional[str]:
        """
        从 http://dat.emugif.com/update/ 获取数据

        Returns:
            str: 获取到的原始XML数据，出错时返回None
        """
        try:
            # 验证URL格式
            parsed_url = urlparse(self.base_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                print(f"无效的URL格式: {self.base_url}")
                return None
                
            print(f"正在从 {self.base_url} 获取数据...")
            response = requests.get(self.base_url, timeout=self.timeout)
            response.raise_for_status()  # 如果请求失败会抛出异常
            print("数据获取成功")
            return response.text
        except requests.exceptions.Timeout:
            print(f"请求超时 ({self.timeout}秒)")
            return None
        except requests.exceptions.ConnectionError:
            print("连接错误，请检查网络连接")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"HTTP错误: {e}")
            return None
        except requests.RequestException as e:
            print(f"获取数据时出错: {e}")
            return None
        except Exception as e:
            print(f"获取数据时发生未知错误: {e}")
            return None

    def fetch_and_convert(self) -> Optional[Dict]:
        """
        从 http://dat.emugif.com/update/ 获取数据并转换为JSON格式

        Returns:
            dict: 解析后的JSON数据，如果出错则返回None
        """
        try:
            # 获取数据
            xml_data = self.fetch_data()

            if xml_data is None:
                print("未能获取到XML数据")
                return None

            # 解析XML数据
            parsed_data = self.parse_xml_data(xml_data)
            
            if parsed_data is None:
                print("XML数据解析失败")
                return None
                
            print(f"成功获取并解析数据，包含 {len(parsed_data.get('datfiles', []))} 个DAT文件信息")
            return parsed_data
        except Exception as e:
            print(f"获取并转换数据时发生错误: {e}")
            return None


class DatFileProcessor:
    """
    处理游戏DAT文件的下载、解压和读取
    """

    _instance = None
    _initialized = False

    def __new__(cls, download_dir: str = "", timeout: int = 60):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, download_dir: str = "", timeout: int = 60):
        """
        初始化DatFileProcessor实例
        
        Args:
            download_dir (str): 下载文件存储目录，默认为临时目录
            timeout (int): 下载超时时间（秒）
        """
        # 确保初始化代码只执行一次
        if DatFileProcessor._initialized:
            return
            
        self.download_dir = download_dir or tempfile.gettempdir()
        self.timeout = timeout
        self.reorganized_data = None
        # 确保下载目录存在
        try:
            os.makedirs(self.download_dir, exist_ok=True)
            print(f"下载目录已准备: {self.download_dir}")
        except Exception as e:
            print(f"创建下载目录失败: {e}")

        self.reorganized_data = self.fetch_and_save_all_data_incremental()
            
        DatFileProcessor._initialized = True

    def get_dat_info(self):
        """
        获取DAT文件信息
        
        Returns:
            List[Dict]: 包含每个DAT文件信息的列表
        """
        if not self.reorganized_data:
            self.reorganized_data = self.fetch_and_save_all_data_incremental()
        return self.reorganized_data
    def extract_dat_info(self, json_data: Optional[Dict]) -> List[Dict]:
        """
        从JSON数据中提取DAT文件信息
        
        Args:
            json_data (Dict): 从EmuGifDataFetcher获取的JSON数据
            
        Returns:
            List[Dict]: 包含每个DAT文件信息的列表
        """
        dat_files = []
        
        if not json_data or not isinstance(json_data, dict):
            print("输入的JSON数据无效")
            return dat_files
            
        datfiles_list = json_data.get("datfiles", [])
        if not isinstance(datfiles_list, list):
            print("datfiles字段不是列表类型")
            return dat_files
        
        for i, datfile in enumerate(datfiles_list):
            if not isinstance(datfile, dict):
                print(f"第{i}个datfile条目不是字典类型，跳过")
                continue
                
            # 从URL中提取dat字段作为主键
            url = datfile.get("url", "")
            dat_key = self._extract_dat_key_from_url(url)
            
            dat_info = {
                "dat_key": dat_key or f"unknown_{i}",
                "name": datfile.get("name", ""),
                "version": datfile.get("version", ""),
                "url": url,
                "file": datfile.get("file", ""),
                "author": datfile.get("author", ""),
                "machines": []  # 添加machines字段用于存储解析的数据
            }
            
            dat_files.append(dat_info)
            
        print(f"成功提取 {len(dat_files)} 个DAT文件信息")
        return dat_files

    def _extract_dat_key_from_url(self, url: str) -> Optional[str]:
        """
        从URL中提取dat参数作为主键
        
        Args:
            url (str): 完整的URL
            
        Returns:
            str: dat参数值，如果未找到则返回None
        """
        if not url or not isinstance(url, str):
            return None
            
        try:
            # 查找dat参数
            if "dat=" in url:
                # 找到dat=的位置
                dat_start = url.find("dat=") + 4  # 4是"dat="的长度
                # 找到下一个&符号或者字符串结尾
                dat_end = url.find("&", dat_start)
                if dat_end == -1:
                    dat_end = len(url)
                result = url[dat_start:dat_end]
                return result if result else None
            return None
        except Exception as e:
            print(f"从URL提取dat键时出错: {e}")
            return None

    def download_and_extract_dat(self, dat_info: Dict) -> Optional[str]:
        """
        下载并解压DAT文件
        
        Args:
            dat_info (Dict): 单个DAT文件的信息
            
        Returns:
            str: 解压后文件的路径，如果失败则返回None
        """
        if not isinstance(dat_info, dict):
            print("dat_info参数必须是字典类型")
            return None
            
        url = dat_info.get("url")
        file_name = dat_info.get("file")
        
        if not url or not file_name:
            print("缺少URL或文件名信息")
            return None
            
        if not isinstance(url, str) or not isinstance(file_name, str):
            print("URL和文件名必须是字符串类型")
            return None
            
        # 初始化变量
        zip_path = ""
        
        try:
            # 验证URL格式
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                print(f"无效的URL格式: {url}")
                return None
                
            # 下载文件
            print(f"正在下载: {url}")
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 保存压缩包到临时文件
            zip_path = os.path.join(self.download_dir, f"{file_name}.zip")
            with open(zip_path, "wb") as f:
                f.write(response.content)
            
            print(f"文件已下载到: {zip_path}")
            
            # 解压文件
            extracted_file_path = os.path.join(self.download_dir, file_name)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.download_dir)
                
            print(f"文件已解压到: {extracted_file_path}")
            
            # 删除压缩包
            try:
                os.remove(zip_path)
                print(f"已删除临时压缩包: {zip_path}")
            except Exception as e:
                print(f"删除临时压缩包失败: {e}")
            
            return extracted_file_path
            
        except requests.exceptions.RequestException as e:
            print(f"下载请求错误: {e}")
            # 清理可能已创建的文件
            if zip_path and os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except:
                    pass
            return None
        except zipfile.BadZipFile as e:
            print(f"损坏的ZIP文件: {zip_path}")
            # 清理可能已创建的损坏文件
            if zip_path and os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except:
                    pass
            return None
        except Exception as e:
            print(f"下载或解压文件时出错: {e}")
            # 清理可能已创建的文件
            if zip_path and os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except:
                    pass
            return None
            


    def read_dat_file(self, file_path: str) -> Optional[str]:
        """
        读取DAT文件内容
        
        Args:
            file_path (str): DAT文件路径
            
        Returns:
            str: 文件内容，如果失败则返回None
        """
        if not file_path or not isinstance(file_path, str):
            print("文件路径必须是非空字符串")
            return None
            
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return None
            
        if not os.path.isfile(file_path):
            print(f"路径不是文件: {file_path}")
            return None
            
        try:
            # 尝试不同的编码方式读取文件
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    print(f"使用 {encoding} 编码成功读取文件: {file_path}")
                    return content
                except UnicodeDecodeError:
                    continue
                    
            print(f"无法使用任何编码方式读取文件: {file_path}")
            return None
            
        except PermissionError:
            print(f"没有权限读取文件: {file_path}")
            return None
        except Exception as e:
            print(f"读取文件时出错: {e}")
            return None

    def parse_dat_content(self, dat_key: str, content: str) -> List[Dict]:
        """
        解析DAT文件内容，提取machine字段信息
        
        Args:
            dat_key (str): DAT文件的主键
            content (str): DAT文件内容
            
        Returns:
            List[Dict]: 包含所有machine信息的列表
        """
        machines = []
        
        if not dat_key or not isinstance(dat_key, str):
            print("dat_key必须是非空字符串")
            return machines
            
        if not content or not isinstance(content, str):
            print("content必须是非空字符串")
            return machines
            
        try:
            # 解析XML内容
            root = ET.fromstring(content)
            
            # 查找所有machine元素
            for i, machine in enumerate(root.findall('.//machine')):
                if machine is None:
                    continue
                    
                try:
                    machine_data = {
                        "dat_key": dat_key,  # 保留主键
                        "name": machine.get("name", ""),
                        "description": "",
                        "releaseNumber": "",
                        "title": "",
                        "year": "",
                        "manufacturer": "",
                        "location": "",
                        "sourceRom": "",
                        "language": "",
                        "rom": {},
                        "im1CRC": "",
                        "im2CRC": "",
                        "comment": "",
                        "duplicateID": ""
                    }
                    
                    # 提取machine下的所有字段
                    for child in machine:
                        if child.tag == "rom":
                            # 特殊处理rom字段
                            rom_data = {
                                "name": child.get("name", ""),
                                "size": child.get("size", ""),
                                "crc": child.get("crc", "")
                            }
                            machine_data["rom"] = rom_data
                        else:
                            # 其他字段直接赋值
                            machine_data[child.tag] = child.text or ""
                    
                    # 添加scrapername字段，基于comment字段但去除结尾的括号和方括号内容
                    comment = machine_data.get("comment", "")
                    scrapername = self._extract_scrapername(comment)
                    machine_data["scrapername"] = scrapername
                    
                    machines.append(machine_data)
                except Exception as e:
                    print(f"处理第{i}个machine元素时出错: {e}")
                    continue
                
            print(f"成功解析 {len(machines)} 个machine元素")
            return machines
            
        except ET.ParseError as e:
            print(f"解析XML内容时出错: {e}")
            return machines
        except Exception as e:
            print(f"处理DAT内容时出错: {e}")
            return machines

    def extract_dat_version_from_content(self, content: str) -> str:
        """
        从DAT文件内容中提取版本信息
        
        Args:
            content (str): DAT文件内容
            
        Returns:
            str: DAT文件版本号，如果未找到则返回空字符串
        """
        if not content or not isinstance(content, str):
            return ""
            
        try:
            # 解析XML内容
            root = ET.fromstring(content)
            
            # 查找header元素中的version字段
            header = root.find('.//header')
            if header is not None:
                version_element = header.find('version')
                if version_element is not None and version_element.text:
                    return version_element.text.strip()
            
            return ""
        except ET.ParseError as e:
            print(f"解析XML内容时出错: {e}")
            return ""
        except Exception as e:
            print(f"提取DAT版本信息时出错: {e}")
            return ""

    def _extract_scrapername(self, comment: str) -> str:
        """
        从comment字段中提取scrapername，去除结尾的括号和方括号中的内容
        
        Args:
            comment (str): 原始comment字段
            
        Returns:
            str: 处理后的scrapername
        """
        if not comment or not isinstance(comment, str):
            return ""
        
        # 使用正则表达式去除结尾的括号和方括号内容
        # 这个正则表达式会匹配结尾处的一个或多个(任意内容)或[任意内容]（包括前面的空格）
        scrapername = re.sub(r'\s*[\(\[][^)\]]*[\)\]]\s*$', '', comment)
        # 重复应用正则表达式直到没有更多匹配项，以处理多个括号的情况
        while re.search(r'\s*[\(\[][^)\]]*[\)\]]\s*$', scrapername):
            scrapername = re.sub(r'\s*[\(\[][^)\]]*[\)\]]\s*$', '', scrapername)
        return scrapername.strip()

    def is_dat_version_unchanged(self, dat_info: Dict, existing_data: Optional[Dict]) -> bool:
        """
        检查DAT文件版本是否未变更
        
        Args:
            dat_info (Dict): 当前DAT文件信息
            existing_data (Dict): 现有数据
            
        Returns:
            bool: 如果版本未变更返回True，否则返回False
        """
        if not isinstance(dat_info, dict) or not isinstance(existing_data, dict):
            return False
            
        dat_key = dat_info.get('dat_key')
        current_version = dat_info.get('version')
        
        if not dat_key or not current_version:
            return False
            
        # 检查现有数据中是否存在相同DAT文件的记录
        existing_dat_files = existing_data.get('dat_files', {})
        if not isinstance(existing_dat_files, dict):
            # 如果existing_dat_files不是字典类型，说明可能是旧的数据格式，无法进行版本检查
            print(f"现有数据格式不支持版本检查，将重新下载DAT文件 {dat_info.get('name', dat_key)}")
            return False
            
        existing_dat_info = existing_dat_files.get(dat_key)
        if not isinstance(existing_dat_info, dict):
            # 如果没有找到对应的DAT文件信息，说明是新增的DAT文件
            return False
            
        existing_version = existing_dat_info.get('version')
        
        # 如果版本号相同，则认为未变更
        if existing_version and existing_version == current_version:
            print(f"DAT文件 {dat_info.get('name', dat_key)} 版本未变更 ({current_version})，跳过下载")
            return True
            
        return False

    def process_single_dat(self, dat_info: Dict, existing_data: Optional[Dict] = None) -> bool:
        """
        处理单个DAT文件：下载、解压、读取并解析内容，直接更新dat_info中的machines字段
        
        Args:
            dat_info (Dict): DAT文件信息，会直接更新其中的machines字段
            existing_data (Dict): 现有数据，用于版本检查
            
        Returns:
            bool: 处理是否成功
        """
        if not isinstance(dat_info, dict):
            print("dat_info必须是字典类型")
            return False
            
        name = dat_info.get('name', 'Unknown')
        dat_key = dat_info.get('dat_key', 'Unknown')
        
        # 检查版本是否变更
        if existing_data and self.is_dat_version_unchanged(dat_info, existing_data):
            # 版本未变更，尝试从现有数据中恢复machine信息
            existing_dat_files = existing_data.get('dat_files', {})
            if isinstance(existing_dat_files, dict):
                existing_dat_info = existing_dat_files.get(dat_key)
                if existing_dat_info and isinstance(existing_dat_info, dict):
                    # 从现有数据中恢复machines信息
                    dat_info["machines"] = existing_dat_info.get("machines", [])
                    print(f"从现有数据恢复 {name} 的游戏信息 ({len(dat_info['machines'])} 个游戏)")
                    return True
        
        print(f"正在处理: {name}")
        
        try:
            # 下载并解压文件
            file_path = self.download_and_extract_dat(dat_info)
            if not file_path:
                print(f"下载或解压失败: {name}")
                return False
                
            # 读取文件内容
            content = self.read_dat_file(file_path)
            if content is None:
                print(f"读取文件内容失败: {name}")
                return False
                
            # 从文件内容中提取实际的版本信息
            actual_version = self.extract_dat_version_from_content(content)
            if actual_version:
                # 更新dat_info中的版本信息
                dat_info["version"] = actual_version
                print(f"从DAT文件内容中提取到版本信息: {actual_version}")
                
            # 解析文件内容，提取machine信息
            dat_key = dat_info.get("dat_key", "")
            machines = self.parse_dat_content(dat_key, content)
            
            # 直接更新传入的dat_info中的machines字段
            dat_info["machines"] = machines
            
            print(f"成功处理: {name} (包含 {len(machines)} 个游戏)")
            return True
        except Exception as e:
            print(f"处理DAT文件时发生错误: {name}, 错误: {e}")
            return False

    def process_all_dats(self, json_data: Dict, existing_data: Optional[Dict] = None) -> List[Dict]:
        """
        处理所有DAT文件
        
        Args:
            json_data (Dict): 从EmuGifDataFetcher获取的JSON数据
            existing_data (Dict): 现有数据，用于版本检查
            
        Returns:
            List[Dict]: 所有处理成功的文件信息列表，包含解析的machine数据
        """
        # 提取DAT文件信息
        dat_files = self.extract_dat_info(json_data)
        
        if not dat_files:
            print("没有有效的DAT文件需要处理")
            return dat_files
            
        # 处理每个文件，直接更新dat_files中的数据
        success_count = 0
        for dat_info in dat_files:
            if self.process_single_dat(dat_info, existing_data):
                success_count += 1
                
        print(f"处理完成: {success_count}/{len(dat_files)} 个DAT文件处理成功")
        return dat_files

    def reorganize_data_for_crc_lookup(self, dat_files: List[Dict]) -> Dict:
        """
        重新组织数据结构，方便通过ROM的CRC查找游戏条目
        
        Args:
            dat_files (list): 原始的DAT文件数据
            
        Returns:
            dict: 重新组织后的数据结构
        """
        # 创建新的数据结构
        reorganized_data = {
            "dat_files": {},  # 以dat_key为键的DAT文件信息
            "games_by_crc": {},  # 以CRC为键的游戏信息
            "statistics": {}  # 统计信息
        }
        
        if not isinstance(dat_files, list):
            print("dat_files必须是列表类型")
            return reorganized_data
        
        # 重新组织数据
        total_games = 0
        valid_dat_files = 0
        
        for i, dat_file in enumerate(dat_files):
            if not isinstance(dat_file, dict):
                print(f"第{i}个dat_file不是字典类型，跳过")
                continue
                
            dat_key = dat_file.get('dat_key')
            if not dat_key:
                print(f"第{i}个dat_file缺少dat_key，跳过")
                continue
                
            # 存储DAT文件信息，包括machines数据
            reorganized_data["dat_files"][dat_key] = {
                "name": dat_file.get('name', ''),
                "version": dat_file.get('version', ''),
                "url": dat_file.get('url', ''),
                "file": dat_file.get('file', ''),
                "author": dat_file.get('author', ''),
                "machines": dat_file.get('machines', [])  # 保存machines数据
            }
            valid_dat_files += 1
            
            # 为每个游戏创建CRC索引
            machines = dat_file.get('machines', [])
            if not isinstance(machines, list):
                print(f"DAT文件 {dat_key} 的machines字段不是列表类型")
                continue
                
            for j, game in enumerate(machines):
                if not isinstance(game, dict):
                    print(f"DAT文件 {dat_key} 中第{j}个游戏不是字典类型，跳过")
                    continue
                    
                rom_info = game.get('rom', {})
                if not isinstance(rom_info, dict):
                    print(f"DAT文件 {dat_key} 中第{j}个游戏的rom字段不是字典类型，跳过")
                    continue
                    
                rom_crc = rom_info.get('crc')
                
                # 只有当CRC存在时才添加到CRC索引中
                if rom_crc:
                    # 简化游戏数据
                    simplified_game = self.simplify_game_data(game)
                    # 确保CRC是唯一的，如果存在冲突，则存储为列表
                    if rom_crc in reorganized_data["games_by_crc"]:
                        # 如果已存在，转换为列表或添加到现有列表
                        existing_entry = reorganized_data["games_by_crc"][rom_crc]
                        if isinstance(existing_entry, list):
                            existing_entry.append(simplified_game)
                        else:
                            reorganized_data["games_by_crc"][rom_crc] = [existing_entry, simplified_game]
                    else:
                        reorganized_data["games_by_crc"][rom_crc] = simplified_game
                
                total_games += 1
        
        # 添加统计信息
        reorganized_data["statistics"] = {
            "dat_files_count": valid_dat_files,
            "games_count": total_games,
            "crc_index_count": len(reorganized_data["games_by_crc"])
        }
        
        print(f"数据重组完成: {valid_dat_files} 个DAT文件, {total_games} 个游戏, {len(reorganized_data['games_by_crc'])} 个CRC索引")
        return reorganized_data

    def reorganize_data_incremental_update(self, dat_files: List[Dict], existing_data: Optional[Dict] = None) -> Dict:
        """
        增量更新重新组织的数据，如果CRC节点已存在则跳过
        
        Args:
            dat_files (list): 原始的DAT文件数据
            existing_data (dict): 已存在的数据，用于增量更新
            
        Returns:
            dict: 重新组织后的数据结构（增量更新后的）
        """
        # 如果没有现有数据，则创建新的数据结构
        if existing_data is None:
            print("未提供现有数据，创建新数据结构")
            return self.reorganize_data_for_crc_lookup(dat_files)
        
        if not isinstance(existing_data, dict):
            print("现有数据格式不正确，创建新数据结构")
            return self.reorganize_data_for_crc_lookup(dat_files)
            
        # 复制现有数据作为基础
        try:
            reorganized_data = {
                "dat_files": existing_data.get("dat_files", {}).copy(),
                "games_by_crc": existing_data.get("games_by_crc", {}).copy(),
                "statistics": existing_data.get("statistics", {}).copy()
            }
        except Exception as e:
            print(f"复制现有数据时出错: {e}")
            return self.reorganize_data_for_crc_lookup(dat_files)
        
        # 验证现有数据结构
        if not isinstance(reorganized_data["dat_files"], dict):
            print("现有数据中的dat_files不是字典类型，重置为空字典")
            reorganized_data["dat_files"] = {}
            
        if not isinstance(reorganized_data["games_by_crc"], dict):
            print("现有数据中的games_by_crc不是字典类型，重置为空字典")
            reorganized_data["games_by_crc"] = {}
            
        # 记录新增的游戏
        added_games = []
        
        # 重新组织数据
        total_games = 0
        new_games_count = 0
        
        if not isinstance(dat_files, list):
            print("dat_files必须是列表类型")
            return reorganized_data
            
        for i, dat_file in enumerate(dat_files):
            if not isinstance(dat_file, dict):
                print(f"第{i}个dat_file不是字典类型，跳过")
                continue
                
            dat_key = dat_file.get('dat_key')
            if not dat_key:
                print(f"第{i}个dat_file缺少dat_key，跳过")
                continue
                
            # 存储或更新DAT文件信息
            reorganized_data["dat_files"][dat_key] = {
                "name": dat_file.get('name', ''),
                "version": dat_file.get('version', ''),
                "url": dat_file.get('url', ''),
                "file": dat_file.get('file', ''),
                "author": dat_file.get('author', ''),
                "machines": dat_file.get('machines', [])  # 保存machines数据
            }
            
            # 为每个游戏创建CRC索引（仅新增的）
            machines = dat_file.get('machines', [])
            if not isinstance(machines, list):
                print(f"DAT文件 {dat_key} 的machines字段不是列表类型")
                continue
                
            for j, game in enumerate(machines):
                if not isinstance(game, dict):
                    print(f"DAT文件 {dat_key} 中第{j}个游戏不是字典类型，跳过")
                    continue
                    
                rom_info = game.get('rom', {})
                if not isinstance(rom_info, dict):
                    print(f"DAT文件 {dat_key} 中第{j}个游戏的rom字段不是字典类型，跳过")
                    continue
                    
                rom_crc = rom_info.get('crc')
                
                # 只有当CRC存在时才处理
                if rom_crc:
                    # 如果CRC不存在于现有数据中，则添加
                    if rom_crc not in reorganized_data["games_by_crc"]:
                        # 简化游戏数据
                        simplified_game = self.simplify_game_data(game)
                        reorganized_data["games_by_crc"][rom_crc] = simplified_game
                        game_name = game.get('name', 'Unknown Game')
                        added_games.append(game_name)
                        new_games_count += 1
                        print(f"新增游戏: {game_name} (CRC: {rom_crc})")
                
                total_games += 1
        
        # 更新统计信息
        reorganized_data["statistics"] = {
            "dat_files_count": len(reorganized_data["dat_files"]),
            "games_count": total_games,
            "new_games_count": new_games_count,
            "crc_index_count": len(reorganized_data["games_by_crc"])
        }
        
        # 打印新增的游戏名称
        if added_games:
            print(f"新增了 {len(added_games)} 个游戏")
            # 只显示前10个新增游戏以避免日志过长
            for game_name in added_games[:10]:
                print(f"  - {game_name}")
            if len(added_games) > 10:
                print(f"  ... 还有 {len(added_games) - 10} 个游戏")
        else:
            print("没有新增游戏")
        
        print(f"增量更新完成: 总计 {total_games} 个游戏, 新增 {new_games_count} 个游戏, CRC索引 {len(reorganized_data['games_by_crc'])} 个")
        return reorganized_data

    def fetch_and_save_all_data_incremental(self) -> Optional[Dict]:
        """
        增量获取全部数据并保存到本地文件
        """
        try:
            # 创建数据获取器实例
            fetcher = EmuGifDataFetcher()
            
            # 获取并转换数据
            print("正在从 http://dat.emugif.com/update/ 获取数据...")
            data = fetcher.fetch_and_convert()
            
            if not data:
                print("无法获取数据")
                #return None
            else:
                print(f"成功获取到 {len(data.get('datfiles', []))} 个DAT文件信息")
            
            # 获取当前脚本所在目录的父目录（game_rom_manager目录）
            output_dir = get_downloaded_dats_directory()
            
            # 检查是否存在现有的CRC优化数据文件
            crc_optimized_file = get_games_by_crc_path()
            existing_data = None
            
            if os.path.exists(crc_optimized_file):
                print("发现现有数据，进行增量更新...")
                try:
                    with open(crc_optimized_file, 'r', encoding='utf-8') as f:
                        games_by_crc_data = json.load(f)
                    
                    # 尝试读取元数据文件
                    metadata_file = os.path.join(output_dir, "dat_metadata.json")
                    dat_files_data = {}
                    statistics_data = {}
                    if os.path.exists(metadata_file):
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        dat_files_data = metadata.get("dat_files", {})
                        statistics_data = metadata.get("statistics", {})
                    
                    # 构造完整的existing_data结构
                    existing_data = {
                        "dat_files": dat_files_data,
                        "games_by_crc": games_by_crc_data,
                        "statistics": statistics_data
                    }
                    existing_count = len(games_by_crc_data)
                    print(f"已加载现有数据，包含 {existing_count} 个游戏")
                except json.JSONDecodeError as e:
                    print(f"现有数据文件JSON格式错误: {e}")
                except Exception as e:
                    print(f"读取现有数据时出错: {e}")
            
            # 处理所有DAT文件，machine数据会直接合并到dat_files中
            print("正在处理所有DAT文件...")
            dat_files = self.process_all_dats(data, existing_data)
            
            # 显示处理结果统计
            total_machines = 0
            print("处理完成，详细信息:")
            for dat_file in dat_files:
                machine_count = len(dat_file.get('machines', []))
                total_machines += machine_count
                print(f"- {dat_file.get('name', 'Unknown')}: {machine_count} 个游戏")
            
            print(f"总计: {len(dat_files)} 个DAT文件, {total_machines} 个游戏条目")
            
            # 重新组织数据结构，方便通过CRC查找（增量更新）
            print("正在重新组织数据结构...")
            reorganized_data = self.reorganize_data_incremental_update(dat_files, existing_data)
            
            # 确保目录存在
            # 获取当前脚本所在目录的父目录（game_rom_manager目录）
            output_dir = get_downloaded_dats_directory()
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存原始数据
            raw_data_file = os.path.join(output_dir, "raw_data.json")
            try:
                with open(raw_data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"原始数据已保存到: {raw_data_file}")
            except Exception as e:
                print(f"保存原始数据时出错: {e}")
            
            # 保存完整数据（包含machines）
            full_data_file = os.path.join(output_dir, "full_data.json")
            try:
                with open(full_data_file, 'w', encoding='utf-8') as f:
                    json.dump(dat_files, f, ensure_ascii=False, indent=2)
                print(f"完整数据已保存到: {full_data_file}")
            except Exception as e:
                print(f"保存完整数据时出错: {e}")
            
            # 保存重新组织的数据（games_by_crc 字段保存到 downloaded_dats 文件夹）
            try:
                # games_by_crc 文件现在保存在 downloaded_dats 目录
                crc_optimized_file_new = get_games_by_crc_path()
                
                games_by_crc_data = reorganized_data.get("games_by_crc", {})
                with open(crc_optimized_file_new, 'w', encoding='utf-8') as f:
                    json.dump(games_by_crc_data, f, ensure_ascii=False, indent=2)
                print(f"games_by_crc 数据已保存到: {crc_optimized_file_new}")
                print(f"- 包含游戏数量: {len(games_by_crc_data)}")
                
                # 同时保存完整的元数据用于版本检查到 downloaded_dats 文件夹
                metadata_file = os.path.join(output_dir, "dat_metadata.json")
                metadata_to_save = {
                    "dat_files": reorganized_data.get("dat_files", {}),
                    "statistics": reorganized_data.get("statistics", {})
                }
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata_to_save, f, ensure_ascii=False, indent=2)
                print(f"DAT元数据已保存到: {metadata_file}")
            except Exception as e:
                print(f"保存games_by_crc数据时出错: {e}")
            
            # 显示统计信息
            stats = reorganized_data.get("statistics", {})
            print("重新组织数据统计:")
            print(f"- DAT文件数量: {stats.get('dat_files_count', 0)}")
            print(f"- 游戏条目数量: {stats.get('games_count', 0)}")
            print(f"- CRC索引数量: {stats.get('crc_index_count', 0)}")
            if 'new_games_count' in stats:
                print(f"- 新增游戏数量: {stats['new_games_count']}")
            
            return reorganized_data
        except Exception as e:
            print(f"获取并保存所有数据时发生错误: {e}")
            return None
    # ... existing code ...

    def save_or_update_game_by_crc(self, crc: str, game_data: Dict) -> bool:
        """
        保存或更新 games_by_crc.json 中的游戏数据
        
        Args:
            crc (str): 游戏的CRC校验码，作为键值
            game_data (dict): 完整的游戏数据
            
        Returns:
            bool: 保存或更新成功返回True，否则返回False
        """
        try:
            # games_by_crc 数据文件路径
            games_by_crc_file = get_games_by_crc_path()
            
            # 确保 downloaded_dats 目录存在
            ensure_app_directories()
            
            # 读取现有数据（如果文件存在）
            games_by_crc_data = {}
            if os.path.exists(games_by_crc_file):
                with open(games_by_crc_file, 'r', encoding='utf-8') as f:
                    games_by_crc_data = json.load(f)
            
            # 简化游戏数据并更新或添加游戏数据
            simplified_game_data = self.simplify_game_data(game_data)
            games_by_crc_data[crc] = simplified_game_data
            
            # 保存回文件
            with open(games_by_crc_file, 'w', encoding='utf-8') as f:
                json.dump(games_by_crc_data, f, ensure_ascii=False, indent=2)
            
            # 同时更新类中的 reorganized_data 属性
            if self.reorganized_data is not None:
                if "games_by_crc" not in self.reorganized_data:
                    self.reorganized_data["games_by_crc"] = {}
                self.reorganized_data["games_by_crc"][crc] = simplified_game_data
            
            print(f"成功保存或更新CRC为 {crc} 的游戏数据")
            return True
            
        except json.JSONDecodeError as e:
            print(f"JSON文件解析错误: {e}")
            return False
        except Exception as e:
            print(f"保存或更新游戏数据时发生错误: {e}")
            return False

    def find_game_by_crc_from_file(self, games_by_crc_file: str, crc: str) -> Optional[Dict]:
        """
        通过CRC在 games_by_crc.json 数据中查找游戏
        
        Args:
            games_by_crc_file (str): games_by_crc JSON文件路径
            crc (str): ROM的CRC校验码
            
        Returns:
            dict or list or None: 找到的游戏信息
        """
        if not crc or not isinstance(crc, str):
            print("CRC必须是非空字符串")
            return None
            
        if not games_by_crc_file or not isinstance(games_by_crc_file, str):
            print("文件路径必须是非空字符串")
            return None
            
        if not os.path.exists(games_by_crc_file):
            print(f"错误: 找不到文件 {games_by_crc_file}")
            return None
        
        try:
            with open(games_by_crc_file, 'r', encoding='utf-8') as f:
                games_by_crc_data = json.load(f)
            
            if not isinstance(games_by_crc_data, dict):
                print("数据文件格式不正确")
                return None
                
            return games_by_crc_data.get(crc)
        except json.JSONDecodeError as e:
            print(f"JSON文件解析错误: {e}")
            return None
        except Exception as e:
            print(f"查找游戏时发生错误: {e}")
            return None

    def simplify_game_data(self, game_data: Dict) -> Dict:
        """
        简化游戏数据，只保留必要的字段
        
        Args:
            game_data (Dict): 完整的游戏数据
            
        Returns:
            Dict: 简化后的游戏数据
        """
        if not isinstance(game_data, dict):
            return {}
            
        simplified_data = {
            "dat_key": game_data.get("dat_key", ""),
            "title": game_data.get("title", ""),
            "scrapername": game_data.get("scrapername", "")
        }
        
        return simplified_data


def main():
    """
    主函数，执行完整的数据获取和处理流程（增量更新模式）
    """
    try:
        # 创建DAT文件处理器实例
        processor = DatFileProcessor(get_downloaded_dats_directory())
        
        # 获取并保存所有数据（增量更新模式）
        reorganized_data = processor.get_dat_info()
        
        if reorganized_data is None:
            print("数据处理失败")
            return
            
        # game_data = {
        #     "dat_key": "gbcdd",
        #     "name": "0001 - 魂斗罗 (简) [未知]",
        #     "description": "0001 - 魂斗罗 (简) [未知]",
        #     "releaseNumber": "1",
        #     "title": "0001 - 魂斗罗 (简)",
        #     "year": "2009",
        #     "manufacturer": "Konami",
        #     "location": "7",
        #     "sourceRom": "未知",
        #     "language": "4",
        #     "rom": {
        #         "name": "0001 - 魂斗罗 (简) [未知].gb",
        #         "size": "262144",
        #         "crc": "979E0024"
        #     },
        #     "im1CRC": "541EBF46",
        #     "im2CRC": "1ECA7B3C",
        #     "comment": "Contra Spirits (Japan) [CHS]",
        #     "duplicateID": "1",
        #     "scrapername": "Contra Spirits"
        # }

        # success = processor.save_or_update_game_by_crc("777777", game_data)

        # reorganized_data = processor.get_dat_info()
        # temp = reorganized_data['games_by_crc'].get('777777')
        # 演示通过CRC查找游戏
        print("演示通过CRC查找游戏:")
        games_by_crc = reorganized_data.get("games_by_crc", {})
        if games_by_crc:
            sample_crc = 'E4E4F75A'
            game = games_by_crc.get(sample_crc)
            if game:
                print(f"通过CRC {sample_crc} 找到游戏:")
                if isinstance(game, list):
                    print(f"  发现 {len(game)} 个具有相同CRC的游戏")
                    game = game[0]
                
                print(f"  游戏名称: {game.get('name', 'N/A')}")
                print(f"  标题: {game.get('title', 'N/A')}")
                print(f"  制造商: {game.get('manufacturer', 'N/A')}")
                print(f"  年份: {game.get('year', 'N/A')}")
                print(f"  ROM注释: {game.get('comment', 'N/A')}")
                rom_info = game.get('rom', {})
                print(f"  ROM名称: {rom_info.get('name', 'N/A')}")
                print(f"  ROM大小: {rom_info.get('size', 'N/A')}")
                print(f"  ROM CRC: {rom_info.get('crc', 'N/A')}")

            else:
                print(f"未找到CRC为 {sample_crc} 的游戏")
        else:
            print("没有可用的游戏数据")
    except Exception as e:
        print(f"主函数执行时发生错误: {e}")


if __name__ == "__main__":
    main()