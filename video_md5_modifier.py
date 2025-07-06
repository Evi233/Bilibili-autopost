import os
import shutil
import hashlib
import subprocess
import datetime
import uuid
from typing import List, Dict, Tuple, Optional

# 全局变量，用于缓存FFmpeg的安装状态，避免重复检查
_FFMPEG_INSTALLED: Optional[bool] = None

def _check_ffmpeg_installed() -> bool:
    """
    内部函数：检查系统是否安装了 FFmpeg。
    结果会被缓存。
    """
    global _FFMPEG_INSTALLED
    if _FFMPEG_INSTALLED is not None:
        return _FFMPEG_INSTALLED

    try:
        # 使用 stdout=subprocess.PIPE 来隐藏输出，只关注返回码
        subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
        _FFMPEG_INSTALLED = True
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        _FFMPEG_INSTALLED = False
        return False

def calculate_md5(filepath: str) -> Optional[str]:
    """
    计算文件的MD5哈希值。
    Args:
        filepath (str): 文件的完整路径。
    Returns:
        Optional[str]: 文件的MD5哈希值（字符串），如果文件不存在或出错则返回None。
    """
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(4096)  # 分块读取，提高大文件效率
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        # print(f"错误：文件 '{filepath}' 未找到。") # 在库中不直接打印，而是让调用者处理
        return None
    except Exception as e:
        # print(f"计算文件 '{filepath}' 的MD5时发生错误: {e}")
        return None

def _modify_video_metadata(input_path: str, output_path: str, title_tag: str) -> bool:
    """
    内部函数：使用ffmpeg修改视频元数据（如标题），不重新编码。
    Args:
        input_path (str): 原始视频文件路径。
        output_path (str): 输出视频文件路径。
        title_tag (str): 用于构建新标题的唯一标识。
    Returns:
        bool: True表示成功修改并创建副本，False表示失败。
    """
    current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    unique_id = str(uuid.uuid4())[:8]  # 取UUID前8位，更短
    # 构建新的标题，确保每次都不同，从而改变元数据
    new_title = f"Modified_Video_{title_tag}_{current_time}_{unique_id}"

    command = [
        'ffmpeg',
        '-i', input_path,
        '-c', 'copy',  # 复制视频和音频流，不重新编码
        '-metadata', f'title={new_title}', # 修改标题元数据
        '-y', # 如果输出文件已存在，则覆盖它
        output_path
    ]

    try:
        # check=True: 如果ffmpeg返回非零退出码，则抛出CalledProcessError
        # capture_output=True: 捕获ffmpeg的stdout和stderr
        subprocess.run(command, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        # print(f"FFmpeg执行失败，错误代码: {e.returncode}\nSTDOUT:\n{e.stdout.decode()}\nSTDERR:\n{e.stderr.decode()}")
        return False
    except FileNotFoundError:
        # print("ffmpeg 命令未找到。请确认ffmpeg已安装并添加到系统PATH中。")
        return False
    except Exception as e:
        # print(f"修改元数据时发生未知错误: {e}")
        return False

def _create_output_directory(dir_path: str) -> bool:
    """
    内部函数：创建输出目录（如果不存在）。
    Args:
        dir_path (str): 要创建的目录路径。
    Returns:
        bool: True表示目录存在或成功创建，False表示创建失败。
    """
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        return True
    except OSError as e:
        # print(f"创建目录 '{dir_path}' 失败: {e}")
        return False

def generate_modified_video_copies(
    original_video_path: str,
    output_directory: str = "modified_video_copies",
    num_copies: int = 10
) -> Dict[str, any]:
    """
    通过修改元数据的方式，为视频文件生成多个副本，并计算MD5值进行对比。

    Args:
        original_video_path (str): 原始视频文件的完整路径。
        output_directory (str): 存放生成副本的目录名称，默认为 "modified_video_copies"。
        num_copies (int): 要生成的副本数量，默认为 10。

    Returns:
        Dict[str, any]: 包含操作结果的字典，结构如下：
            {
                'success': bool,                  # 整体操作是否成功
                'message': str,                   # 操作结果消息
                'original_md5': Optional[str],    # 原始视频文件的MD5哈希值
                'original_copy_path': Optional[str], # 原始文件在输出目录的副本路径
                'modified_copies': List[Dict[str, str]], # 成功生成的修改后副本列表
                    # 每个元素是 {'path': '文件路径', 'md5': 'MD5值'}
                'duplicate_md5_found': bool,      # 生成的副本中是否存在MD5重复
                'duplicate_md5_details': Dict[str, List[str]] # 包含重复MD5的文件列表
            }
    """
    results: Dict[str, any] = {
        'success': False,
        'message': '',
        'original_md5': None,
        'original_copy_path': None,
        'modified_copies': [],
        'duplicate_md5_found': False,
        'duplicate_md5_details': {}
    }

    if not os.path.exists(original_video_path):
        results['message'] = f"错误：原始视频文件 '{original_video_path}' 不存在。"
        return results

    if not _check_ffmpeg_installed():
        results['message'] = "错误：FFmpeg 未安装或不在系统PATH中。请先安装FFmpeg。"
        return results

    if not _create_output_directory(output_directory):
        results['message'] = f"错误：无法创建输出目录 '{output_directory}'。"
        return results

    base_name = os.path.splitext(os.path.basename(original_video_path))[0]
    extension = os.path.splitext(original_video_path)[1]

    # 1. 计算原始视频文件的MD5
    results['original_md5'] = calculate_md5(original_video_path)
    if results['original_md5'] is None:
        results['message'] = f"错误：无法计算原始文件 '{original_video_path}' 的MD5值。"
        return results

    # 2. 将原始文件复制一份到输出目录，以便与副本一起比较MD5
    original_copy_path = os.path.join(output_directory, f"{base_name}_original{extension}")
    try:
        shutil.copyfile(original_video_path, original_copy_path)
        results['original_copy_path'] = original_copy_path
        # print(f"已将原始文件复制到: {original_copy_path}")
    except Exception as e:
        results['message'] = f"错误：复制原始文件到输出目录失败: {e}"
        # 即使复制失败，也尝试继续生成副本，但不影响原始MD5的报告
        results['original_copy_path'] = None # 确保明确标记失败
        # return results # 不直接返回，尝试继续

    # 3. 生成指定数量的副本并修改元数据
    # print(f"正在生成 {num_copies} 个视频副本并修改元数据...")
    for i in range(num_copies):
        output_filename = f"{base_name}_copy_{i+1}{extension}"
        output_path = os.path.join(output_directory, output_filename)
        if _modify_video_metadata(original_video_path, output_path, f"Copy_{i+1}"):
            modified_md5 = calculate_md5(output_path)
            if modified_md5:
                results['modified_copies'].append({'path': output_path, 'md5': modified_md5})
            else:
                # print(f"警告：无法计算副本 '{output_path}' 的MD5值。")
                pass # 忽略无法计算MD5的副本
        else:
            # print(f"警告：副本 {i+1} 生成失败，将跳过。")
            pass # 忽略生成失败的副本

    if not results['modified_copies']:
        results['message'] = "警告：没有成功生成任何修改后的视频副本。"
        results['success'] = False
        return results

    # 4. 对比所有文件的MD5值
    all_md5_to_check: Dict[str, str] = {} # {md5_value: filename}
    all_md5_to_check[results['original_md5']] = original_video_path # 原始文件

    # 将原始文件在输出目录的副本也加入比较，以便更全面地检测
    if results['original_copy_path'] and os.path.exists(results['original_copy_path']):
        original_copy_md5 = calculate_md5(results['original_copy_path'])
        if original_copy_md5:
            all_md5_to_check[original_copy_md5] = results['original_copy_path']


    for item in results['modified_copies']:
        all_md5_to_check[item['md5']] = item['path'] # 存储路径，方便报告重复

    # 检查MD5重复
    seen_md5s = {}
    for md5_val, file_path in all_md5_to_check.items():
        if md5_val in seen_md5s:
            results['duplicate_md5_found'] = True
            if md5_val not in results['duplicate_md5_details']:
                results['duplicate_md5_details'][md5_val] = []
                results['duplicate_md5_details'][md5_val].append(seen_md5s[md5_val])
            results['duplicate_md5_details'][md5_val].append(file_path)
        else:
            seen_md5s[md5_val] = file_path

    if results['duplicate_md5_found']:
        results['message'] = "操作完成，但发现重复的MD5值。"
        results['success'] = False # 尽管操作完成，但结果不是理想的唯一性
    else:
        results['message'] = f"成功生成 {len(results['modified_copies'])} 个视频副本，所有文件的MD5值都是唯一的。"
        results['success'] = True

    return results

def cleanup_video_copies(output_directory: str) -> Tuple[bool, str]:
    """
    删除指定目录下的所有视频副本和目录本身。
    Args:
        output_directory (str): 存放副本的目录路径。
    Returns:
        Tuple[bool, str]: (是否成功删除, 消息)。
    """
    if not os.path.exists(output_directory):
        return False, f"目录 '{output_directory}' 不存在，无需删除。"

    try:
        shutil.rmtree(output_directory)
        return True, f"成功删除目录 '{output_directory}' 及其所有内容。"
    except OSError as e:
        return False, f"删除目录 '{output_directory}' 失败: {e}"
    except Exception as e:
        return False, f"删除目录 '{output_directory}' 时发生未知错误: {e}"