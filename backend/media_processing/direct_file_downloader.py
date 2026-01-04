# -*- coding: utf-8 -*-
"""直接文件下载器

用于下载直接的文件URL（如OSS链接、CDN链接等），不通过特定平台下载器。
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional, Callable, Dict
from urllib.parse import urlparse

import requests
import urllib3

# AI Agent: 禁用SSL警告（开发环境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from backend.common_interfaces import DownloadResult

logger = logging.getLogger(__name__)

# AI Agent: 支持的音频文件扩展名
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma', '.opus', '.mp4', '.webm'}

# AI Agent: 支持的视频文件扩展名
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'}


class DirectFileDownloader:
    """直接文件下载器
    
    用于下载直接的文件URL（如OSS链接、CDN链接等），不通过特定平台下载器。
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化直接文件下载器

        Args:
            output_dir: 下载输出目录
        """
        self.output_dir = output_dir or os.getcwd()

    def _is_audio_file(self, url: str) -> bool:
        """检查URL是否为音频文件"""
        # AI Agent: 从URL路径中提取文件扩展名
        parsed = urlparse(url)
        path = parsed.path.lower()
        # AI Agent: 移除查询参数，只检查路径
        path_without_query = path.split('?')[0]
        ext = os.path.splitext(path_without_query)[1]
        return ext in AUDIO_EXTENSIONS

    def _is_video_file(self, url: str) -> bool:
        """检查URL是否为视频文件"""
        # AI Agent: 从URL路径中提取文件扩展名
        parsed = urlparse(url)
        path = parsed.path.lower()
        # AI Agent: 移除查询参数，只检查路径
        path_without_query = path.split('?')[0]
        ext = os.path.splitext(path_without_query)[1]
        return ext in VIDEO_EXTENSIONS

    def _get_filename_from_url(self, url: str) -> str:
        """从URL中提取文件名"""
        parsed = urlparse(url)
        path = parsed.path
        # AI Agent: 移除查询参数
        path_without_query = path.split('?')[0]
        filename = os.path.basename(path_without_query)
        
        # AI Agent: 如果没有文件名或文件名无效，使用默认名称
        if not filename or '.' not in filename:
            # AI Agent: 尝试从Content-Disposition头获取文件名，或使用默认名称
            filename = "downloaded_file.mp3"
        
        return filename

    def download(self, url: str, progress_callback: Optional[Callable[[Dict], None]] = None) -> DownloadResult:
        """
        下载直接文件URL

        Args:
            url: 文件URL
            progress_callback: 进度回调函数

        Returns:
            DownloadResult: 下载结果
        """
        try:
            # AI Agent: 验证URL格式
            if not url.startswith(('http://', 'https://')):
                return DownloadResult(
                    success=False,
                    error_message=f"不支持的URL协议，仅支持HTTP/HTTPS: {url}"
                )

            # AI Agent: 检查是否为音频或视频文件
            is_audio = self._is_audio_file(url)
            is_video = self._is_video_file(url)

            if not is_audio and not is_video:
                # AI Agent: 如果无法从URL判断，尝试通过HEAD请求检查Content-Type
                try:
                    response = requests.head(url, timeout=10, allow_redirects=True, verify=False)
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'audio' in content_type:
                        is_audio = True
                    elif 'video' in content_type:
                        is_video = True
                    else:
                        # AI Agent: 默认当作音频文件处理（因为用户提供的链接是.mp3）
                        is_audio = True
                        logger.warning(f"无法确定文件类型，默认当作音频文件处理: {url}")
                except Exception as e:
                    logger.warning(f"HEAD请求失败，默认当作音频文件处理: {e}")
                    is_audio = True

            # AI Agent: 确定媒体类型
            if is_video and is_audio:
                media_type = "both"
            elif is_video:
                media_type = "video"
            else:
                media_type = "audio"

            # AI Agent: 获取文件名
            filename = self._get_filename_from_url(url)
            
            # AI Agent: 确保输出目录存在
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # AI Agent: 构建完整文件路径
            file_path = output_path / filename
            
            # AI Agent: 如果文件已存在，添加序号
            counter = 1
            original_file_path = file_path
            while file_path.exists():
                stem = original_file_path.stem
                suffix = original_file_path.suffix
                file_path = output_path / f"{stem}_{counter}{suffix}"
                counter += 1

            # AI Agent: 通知开始下载
            if progress_callback:
                progress_callback({
                    "status": "downloading",
                    "progress_percent": 0,
                    "filename": filename,
                    "downloaded_bytes": 0,
                    "total_bytes": 0,
                    "speed": 0,
                    "eta_seconds": None
                })

            # AI Agent: 下载文件
            logger.info(f"开始下载直接文件: {url} -> {file_path}")
            response = requests.get(url, stream=True, timeout=30, allow_redirects=True, verify=False)
            response.raise_for_status()

            # AI Agent: 获取文件大小（如果可用）
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded_size = 0

            # AI Agent: 写入文件
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # AI Agent: 更新进度
                        if progress_callback and total_size > 0:
                            progress_percent = int((downloaded_size / total_size) * 100)
                            progress_callback({
                                "status": "downloading",
                                "progress_percent": progress_percent,
                                "filename": filename,
                                "downloaded_bytes": downloaded_size,
                                "total_bytes": total_size,
                                "speed": 0,  # 可以计算，但这里简化处理
                                "eta_seconds": None
                            })

            logger.info(f"直接文件下载完成: {file_path}")

            # AI Agent: 根据媒体类型设置返回结果
            result = DownloadResult(
                success=True,
                title=filename,
                media_type=media_type
            )

            if is_audio:
                result.audio_path = str(file_path.resolve())
            if is_video:
                result.video_path = str(file_path.resolve())

            # AI Agent: 通知下载完成
            if progress_callback:
                progress_callback({
                    "status": "completed",
                    "progress_percent": 100,
                    "filename": filename,
                    "downloaded_bytes": downloaded_size,
                    "total_bytes": total_size,
                    "speed": 0,
                    "eta_seconds": None
                })

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"下载直接文件失败: {e}")
            return DownloadResult(
                success=False,
                error_message=f"下载失败: {str(e)}"
            )
        except Exception as e:
            logger.error(f"下载直接文件时发生未预期的错误: {e}", exc_info=True)
            return DownloadResult(
                success=False,
                error_message=f"下载失败: {str(e)}"
            )
