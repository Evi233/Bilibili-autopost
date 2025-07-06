import os
import random
import time
from datetime import datetime
from upload_only import BilibiliUploader
from video_md5_modifier import generate_modified_video_copies
import shutil
import requests

class AutoBilibiliUploader:
    def __init__(self, cookies_dir='cookies'):
        self.cookies_dir = cookies_dir
        self.cookies_files = self.get_cookies_files()
        self.current_cookie_index = 0
        self.load_current_cookies()
        # --- 在这里添加以下代码 ---
        # 状态服务器地址
        self.status_server_url = 'http://127.0.0.1:7652/status'
        self.secret_key = "*"
        
        # 状态追踪变量
        self.uploads_by_account = {cookie: 0 for cookie in self.cookies_files}
        self.failed_accounts = set()
        self.uploaded_bvids = []
        
        # 发送初始状态
        self.send_status_update(event_type="init")
        # --- 添加结束 ---
    # --- 在这里添加一个全新的方法 ---
    def refresh_cookies_list(self):
        """检查cookies目录，动态加载新cookie文件"""
        try:
            # 重新扫描cookies目录
            current_files_on_disk = [f for f in os.listdir(self.cookies_dir) if f.endswith('.txt')]
            
            # 找出新增的文件
            new_files = [f for f in current_files_on_disk if f not in self.cookies_files]
            
            if new_files:
                for file in new_files:
                    print(f"检测到新的Cookie文件: {file}")
                    self.cookies_files.append(file)
                    self.uploads_by_account[file] = 0 # 初始化新账号的上传计数
                
                # 更新状态
                self.send_status_update("cookies_reloaded")
                
        except Exception as e:
            print(f"刷新Cookie列表时出错: {e}")
    def send_status_update(self, event_type="update"):
        """收集状态并发送到监控服务器"""
        status_data = {
            "current_account": self.cookies_files[self.current_cookie_index],
            "uploads_by_account": self.uploads_by_account,
            "failed_accounts_count": len(self.failed_accounts),
            "total_accounts": len(self.cookies_files),
            "successful_videos": self.uploaded_bvids,
            "total_successful_uploads": len(self.uploaded_bvids),
            "event": event_type,
            "timestamp": datetime.now().isoformat()
        }
        try:
            headers = {
                'X-Auth-Token': self.secret_key
            }
            # 在 post 请求中加入 headers
            requests.post(self.status_server_url, json=status_data, headers=headers, timeout=5)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 状态已发送到服务器: {event_type}")
        except requests.exceptions.RequestException as e:
            print(f"无法连接到状态服务器: {e}")
# --- 添加结束 ---
    def get_cookies_files(self):
        """获取cookies文件夹中的所有cookies文件"""
        if not os.path.exists(self.cookies_dir):
            raise FileNotFoundError(f"Cookies directory '{self.cookies_dir}' not found")
            
        files = [f for f in os.listdir(self.cookies_dir) if f.endswith('.txt')]
        if not files:
            raise ValueError(f"No cookie files found in {self.cookies_dir}")
        return files
        
    def load_current_cookies(self):
        """加载当前index的cookies"""
        cookie_file = os.path.join(self.cookies_dir, self.cookies_files[self.current_cookie_index])
        self.cookies = self.load_cookies(cookie_file)
        self.uploader = BilibiliUploader(self.cookies['SESSDATA'], self.cookies['bili_jct'])
        print(f"使用账号: {self.cookies_files[self.current_cookie_index]}")
        
    def load_cookies(self, cookies_file):
        """从cookies文件加载cookies"""
        import json
        with open(cookies_file, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)
        
        cookies = {}
        for cookie in cookies_data:
            if cookie['name'] == 'SESSDATA':
                cookies['SESSDATA'] = cookie['value']
            elif cookie['name'] == 'bili_jct':
                cookies['bili_jct'] = cookie['value']
        
        if not cookies.get('SESSDATA') or not cookies.get('bili_jct'):
            raise ValueError(f"Invalid cookies file: {cookies_file}")
        return cookies
        
    def switch_to_next_cookie(self):
        """切换到下一个cookies账号"""
        self.current_cookie_index = (self.current_cookie_index + 1) % len(self.cookies_files)
        self.load_current_cookies()
        # --- 在这里添加以下代码 ---
        self.send_status_update(event_type="account_switch")
        # --- 添加结束 ---
        return True
    
    def get_video_file(self):
        """获取视频文件，处理可能的重复文件名"""
        video_files = [f for f in os.listdir() if f.endswith('.mp4')]
        
        if not video_files:
            raise FileNotFoundError("No video file found")
            
        # 优先选择不带重复后缀的文件
        for f in video_files:
            if not f.endswith('.mp4.mp4'):
                return f
                
        # 如果只有带重复后缀的文件
        return video_files[0]
    
    def generate_random_title(self):
        """生成随机视频标题"""
        prefixes = ['测试视频', '上传测试', '自动上传', '随机视频']
        suffixes = ['第1次', '第2次', '第3次', '补档', '备份']
        adjectives = ['精彩的', '有趣的', '随机的', '测试用的']
        nouns = ['内容', '视频', '素材', '文件']
        
        title = f"{random.choice(prefixes)}-{random.choice(adjectives)}{random.choice(nouns)}-{random.choice(suffixes)}"
        return title
    
    def generate_random_description(self):
        """生成随机视频描述"""
        descriptions = [
            "这是一个自动上传的测试视频",
            "补档视频，请勿举报",
            "自动上传测试，随机内容",
            "哈希修改后上传的视频",
            "循环上传测试的一部分"
        ]
        return random.choice(descriptions)
    
    def modify_video_hash(self, video_path):
        """修改视频哈希值"""
        # 创建临时目录
        temp_dir = 'temp_modified_videos'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # 生成修改后的视频副本
        result = generate_modified_video_copies(
            original_video_path=video_path,
            output_directory=temp_dir,
            num_copies=1
        )
        
        if not result['success'] or not result['modified_copies']:
            raise RuntimeError("Failed to modify video hash")
            
        # 获取修改后的视频路径
        modified_path = result['modified_copies'][0]['path']
        
        # 返回修改后的视频路径
        return modified_path
    
    def cleanup_temp_files(self, temp_dir='temp_modified_videos'):
        """清理临时文件"""
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    def upload_once(self, test_mode=True):
        """执行单次上传"""
        try:
            # 获取视频文件
            original_video = self.get_video_file()
            print(f"找到视频文件: {original_video}")
            
            # 修改视频哈希
            modified_video = self.modify_video_hash(original_video)
            print(f"哈希修改后的视频: {modified_video}")
            
            # 封面文件
            cover_image = '1262dda6e9e0ef341440353f7a35e748ffee61f7.jpg'
            if not os.path.exists(cover_image):
                raise FileNotFoundError(f"封面文件 {cover_image} 不存在")
            
            # 使用固定标题、描述和标签
            title = "Butcher Vanity 虚荣屠夫 FLAVOR FOLEY feat.奕夕"
            description = """https://flavorfoley.com/
introducing FLAVOR FOLEY, a delicious new music circle consisting of vane, ricedeity, and JamieP! serving up delectable ditties guaranteed to satisfy your cravings! and also... "satisfy" your "cravings"? yknow?? it's a song about eating people
– 
hi i think we're insane. rice got yi xi 3 days ago. I fuckign love meatgirl. and now a word from the rest of flavor foley 

Jamie P: "some five years ago, my broke ass once got duped into going to an absurdly expensive upscale restaurant with some folks. i could've just not gotten anything, or settled for a bite or two off someone else's plate, but instead i unwisely overdrafted my bank account and ordered something i had never eaten before in my life - steak tartare. onions, capers, cilantro, egg yolk, and raw beef. it was the most delicious thing i've ever eaten in my life. i have been haunted by the insatiable primal desire to eat raw red meat every single day since. anyways we made all of this in like three days max and its incredible we are so goated"

rice: "I would Also like to try the raw beef Jamie got from that restaurant"
ALSO CHECK OUT BEATSHOBONS REMIX OF OUR SONG !!!!    • BUTCHER VANITY (beat_shobon remix)  
—
Vocals by Yi Xi SynthV
—
FLAVOR FOLEY CREDITS: 
@vanelily: composition, arrange, lyrics
  / rhythmfriend  
@JamiePaigeIRL: composition, arrange, lyrics
  / pamiejaige  
@ricedeity: composition, lyrics, violin
  / ricedeity  

mv by ricedeity
日本語訳：りきくん (https://rikikun.com/)
– 
spotify: https://open.spotify.com/track/5w5wBk...
apple music:   / butcher-vanity-feat-jamie-paige-ricedeity-...  
bandcamp: https://jamiepaige.bandcamp.com/album...
inst/svp/lyrics dl: https://drive.google.com/drive/folder..."""
            tags = ["虚荣屠夫", "Bucher Vainty", "补档"]
            
            print(f"标题: {title}")
            print(f"描述: {description[:50]}...")  # 只打印前50字符避免输出过长
            print(f"标签: {tags}")
            
            # 执行上传
            print("开始上传...")
            bvid = self.uploader.full_upload_process(
                video_file_path=modified_video,
                cover_image_path=cover_image,
                title=title,
                description=description,
                tags=tags
            )
            
            if bvid:
                print(f"上传成功! BV号: {bvid}")
                # --- 在这里添加/修改以下代码 ---
                # 更新状态
                self.uploaded_bvids.append(bvid)
                current_cookie_file = self.cookies_files[self.current_cookie_index]
                self.uploads_by_account[current_cookie_file] += 1
                # 发送状态更新
                self.send_status_update(event_type="upload_success")
                # --- 添加结束 ---
            else:
                print("上传失败")
            
            return bvid is not None
            
        except Exception as e:
            print(f"上传过程中出错: {e}")
            return False
        finally:
            # 清理临时文件
            self.cleanup_temp_files()
    
    def run_loop(self, test_mode=True):
        """运行循环上传"""
        if test_mode:
            print("测试模式: 仅上传一次")
            success = self.upload_once(test_mode=True)
            return success
        
        print("开始循环上传...")
        count = 0
        fail_count = 0
        
        while True:
            count += 1
            print(f"\n=== 第 {count} 次上传尝试 ===")
            self.refresh_cookies_list()  # 每次循环开始时检查新cookie
            try:
                success = self.upload_once(test_mode=False)
                if not success:
                    fail_count += 1
                    # --- 在这里添加以下代码 ---
                    # 标记当前账号为失败
                    failed_cookie = self.cookies_files[self.current_cookie_index]
                    self.failed_accounts.add(failed_cookie)
                    # --- 添加结束 ---
                    
                    if fail_count >= len(self.cookies_files):
                        print("所有账号均上传失败，停止循环")
                        self.send_status_update("all_accounts_failed") # 发送最终状态
                        break
                        
                    print("上传失败，切换账号重试...")
                    self.switch_to_next_cookie()
                    continue
                
                fail_count = 0
                # 固定等待5秒
                wait_time = 5
                print(f"等待 {wait_time} 秒后继续...")
                time.sleep(wait_time)
                
            except KeyboardInterrupt:
                print("\n用户中断，停止上传")
                break
            except Exception as e:
                print(f"发生错误: {e}")
                fail_count += 1
                if fail_count >= len(self.cookies_files):
                    print("所有账号均出错，停止循环")
                    break
                    
                print("切换账号并等待5分钟后重试...")
                self.switch_to_next_cookie()
                time.sleep(300)


if __name__ == '__main__':
    try:
        uploader = AutoBilibiliUploader()
        
        # 正式循环上传
        uploader.run_loop(test_mode=False)
        
    except Exception as e:
        print(f"初始化失败: {e}")
