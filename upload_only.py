
import requests
import json
import os
import time
import math
from PIL import Image
from tqdm import tqdm

class BilibiliUploader:
    def __init__(self, sessdata, bili_jct):
        self.sessdata = sessdata
        self.bili_jct = bili_jct
        self.cookies = {
            'SESSDATA': self.sessdata,
            'bili_jct': self.bili_jct
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Origin': 'https://space.bilibili.com',
            'Referer': 'https://space.bilibili.com/'
        }

    def preupload_video(self, video_path):
        file_name = os.path.basename(video_path)
        file_size = os.path.getsize(video_path)
        timestamp = int(time.time() * 1000)

        url = f"https://member.bilibili.com/preupload?name={file_name}&r=upos&profile=ugcfx/bup&size={file_size}&webVersion=2.13.0&build=2140000&version=2.14.0.0&ssl=0&zone=cs&upcdn=txa&probe_version=20221109&t={timestamp}"
        
        try:
            response = requests.get(url, headers=self.headers, cookies=self.cookies)
            response.raise_for_status()
            print(f"[DEBUG] preupload_video response status: {response.status_code}")
            print(f"[DEBUG] preupload_video response content: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] preupload_video failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[ERROR] preupload_video response content: {e.response.text}")
            raise

    def post_video_meta(self, preupload_data, video_path):
        scheme_and_host = "https:" + preupload_data['endpoint']
        path = preupload_data['upos_uri'].replace("upos:/", "")
        file_size = os.path.getsize(video_path)

        url = f"{scheme_and_host}{path}?uploads=&output=json&profile=ugcfx/bup&filesize={file_size}&partsize={preupload_data['chunk_size']}&biz_id={preupload_data['biz_id']}"
        
        headers = self.headers.copy()
        headers['X-Upos-Auth'] = preupload_data['auth']

        try:
            response = requests.post(url, headers=headers, cookies=self.cookies)
            response.raise_for_status()
            print(f"[DEBUG] post_video_meta response status: {response.status_code}")
            print(f"[DEBUG] post_video_meta response content: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] post_video_meta failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[ERROR] post_video_meta response content: {e.response.text}")
            raise

    def upload_chunk(self, preupload_data, post_meta_data, video_path, chunk_number, start_byte, end_byte, total_size, chunk_data):
        scheme_and_host = "https:" + preupload_data['endpoint']
        path = preupload_data['upos_uri'].replace("upos:/", "")
        
        chunk_size = preupload_data['chunk_size']
        total_chunks = math.ceil(total_size / chunk_size)

        url = f"{scheme_and_host}{path}?partNumber={chunk_number}&uploadId={post_meta_data['upload_id']}&chunk={chunk_number-1}&chunks={total_chunks}&size={len(chunk_data)}&start={start_byte}&end={end_byte}&total={total_size}"

        headers = self.headers.copy()
        headers['X-Upos-Auth'] = preupload_data['auth']
        headers['Content-Type'] = 'application/octet-stream'
        headers['Content-Length'] = str(len(chunk_data))

        try:
            response = requests.put(url, headers=headers, cookies=self.cookies, data=chunk_data)
            response.raise_for_status()
            print(f"[DEBUG] Uploaded chunk {chunk_number}/{total_chunks}, bytes {start_byte}-{end_byte}. Status: {response.status_code}")
            print(f"[DEBUG] Chunk upload response: {response.text}")
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Uploading chunk {chunk_number}/{total_chunks} failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[ERROR] Chunk upload response content: {e.response.text}")
            raise

    def end_upload(self, preupload_data, post_meta_data, video_path, parts_info):
        scheme_and_host = "https:" + preupload_data['endpoint']
        path = preupload_data['upos_uri'].replace("upos:/", "")
        file_name = os.path.basename(video_path)

        url = f"{scheme_and_host}{path}?output=json&name={file_name}&profile=ugcfx/bup&uploadId={post_meta_data['upload_id']}&biz_id={preupload_data['biz_id']}"

        headers = self.headers.copy()
        headers['X-Upos-Auth'] = preupload_data['auth']
        headers['Content-Type'] = 'application/json; charset=UTF-8'

        payload = {
            "parts": parts_info
        }

        try:
            response = requests.post(url, headers=headers, cookies=self.cookies, data=json.dumps(payload))
            response.raise_for_status()
            print(f"[DEBUG] end_upload response status: {response.status_code}")
            print(f"[DEBUG] end_upload response content: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] end_upload failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[ERROR] end_upload response content: {e.response.text}")
            raise

    def upload_video_file_and_get_info(self, video_path):
        print(f"开始上传视频文件: {video_path}")
        try:
            preupload_data = self.preupload_video(video_path)
            print("预上传成功:", preupload_data)
        except Exception as e:
            print(f"[ERROR] 预上传失败: {e}")
            return None

        try:
            post_meta_data = self.post_video_meta(preupload_data, video_path)
            print("上传视频元数据成功:", post_meta_data)
        except Exception as e:
            print(f"[ERROR] 上传视频元数据失败: {e}")
            return None

        chunk_size = preupload_data['chunk_size']
        total_size = os.path.getsize(video_path)
        total_chunks = math.ceil(total_size / chunk_size)
        parts_info = []

        with open(video_path, 'rb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc='上传视频') as pbar:
                for i in range(total_chunks):
                    chunk_data = f.read(chunk_size)
                    start_byte = i * chunk_size
                    end_byte = min((i + 1) * chunk_size, total_size)
                    
                    try:
                        self.upload_chunk(preupload_data, post_meta_data, video_path, i + 1, start_byte, end_byte, total_size, chunk_data)
                        parts_info.append({"partNumber": i + 1, "eTag": "etag"}) # eTag is not returned by Bilibili, so use a placeholder
                        pbar.update(len(chunk_data))
                    except Exception as e:
                        print(f"[ERROR] 上传分块 {i+1}/{total_chunks} 失败: {e}")
                        return None # Stop upload if a chunk fails

        try:
            end_upload_data = self.end_upload(preupload_data, post_meta_data, video_path, parts_info)
            print("结束上传成功:", end_upload_data)
        except Exception as e:
            print(f"[ERROR] 结束上传失败: {e}")
            return None
        
        video_info_for_submit = {
            'filename': preupload_data['upos_uri'].split('/')[-1].split('.')[0], # Extract filename without extension
            'biz_id': preupload_data['biz_id']
        }
        return video_info_for_submit

    def submit_video(self, video_info, cover_url, title, desc, tags):
        url = "https://member.bilibili.com/x/vu/web/add/v3"
        timestamp = int(time.time() * 1000)

        headers = self.headers.copy()
        headers['Content-Type'] = 'application/json; charset=utf-8'

        payload = {
            "videos": [
                {
                    "filename": video_info['filename'],
                    "title": title, # Use the same title for part title for simplicity
                    "desc": desc,
                    "cid": video_info['biz_id']
                }
            ],
            "cover": cover_url,
            "cover43": "",
            "title": title,
            "copyright": 1, # 1 for original, 2 for reprinted
            "tid": 21, # For '日常' category, adjust as needed
            "tag": ",".join(tags),
            "desc_format_id": 9999,
            "desc": desc,
            "recreate": -1, # Allow secondary creation
            "dynamic": f"新视频上线啦！{title}",
            "interactive": 0,
            "act_reserve_create": 0,
            "no_disturbance": 0,
            "no_reprint": 1, # Allow reprinting
            "subtitle": {"open": 0, "lan": ""},
            "dolby": 0,
            "lossless_music": 0,
            "up_selection_reply": False,
            "up_close_reply": False,
            "up_close_danmu": False,
            "web_os": 3,
            "csrf": self.bili_jct
        }

        try:
            response = requests.post(url, headers=headers, cookies=self.cookies, params={'ts': timestamp, 'csrf': self.bili_jct}, data=json.dumps(payload))
            response.raise_for_status()
            print(f"[DEBUG] submit_video response status: {response.status_code}")
            print(f"[DEBUG] submit_video response content: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] submit_video failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[ERROR] submit_video response content: {e.response.text}")
            raise

    def upload_cover(self, image_path):
        with open(image_path, 'rb') as f:
            image_data = f.read()
        import base64
        encoded_image = base64.b64encode(image_data).decode('utf-8')

        url = "https://member.bilibili.com/x/vu/web/cover/up"
        timestamp = int(time.time() * 1000)

        headers = self.headers.copy()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

        payload = {
            "csrf": self.bili_jct,
            "cover": f"data:image/jpeg;base64,{encoded_image}"
        }

        try:
            response = requests.post(url, headers=headers, cookies=self.cookies, params={'ts': timestamp}, data=payload)
            response.raise_for_status()
            print(f"[DEBUG] upload_cover response status: {response.status_code}")
            print(f"[DEBUG] upload_cover response content: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] upload_cover failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[ERROR] upload_cover response content: {e.response.text}")
            raise

    def full_upload_process(self, video_file_path, cover_image_path, title, description, tags):
        try:
            # 1. Upload cover image
            cover_upload_result = self.upload_cover(cover_image_path)
            cover_url = cover_upload_result['data']['url']
            print("封面上传成功，URL:", cover_url)

            # 2. Upload video file
            video_info_for_submit = self.upload_video_file_and_get_info(video_file_path)
            if video_info_for_submit is None:
                print("[ERROR] 视频文件上传失败，终止后续操作。")
                return None

            # 3. Submit video
            submit_result = self.submit_video(video_info_for_submit, cover_url, title, description, tags)
            print("视频投稿成功:", submit_result)
            
            if submit_result['code'] == 0 and 'bvid' in submit_result['data']:
                return submit_result['data']['bvid']
            else:
                print(f"视频投稿失败: {submit_result.get('message', '未知错误')}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 请求失败: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] 发生错误: {e}")
            return None


if __name__ == '__main__':
    SESSDATA = 'bb250dfc%2C1767020160%2C0d7b0%2A71CjD77vUnizRstnRK6Sqs_5KF7MyQ6u09bEqoqWmRNevkiZHojGCuCNnxGSBtkEu9AVcSVmhzM3NKNUtSZlJfeTdHdEI2Tlc1NHhyV2NEaEc3ZERfRWxwUy1KUzJ4d2pRMGZRUHI3YjFoOUM0OUVrVEl5OVBpTDhWdUJQUzRiT0RoMlJoWF9ENmV3IIEC'
    bili_jct = '03316ca4b6a0a732e2ec14ad7e18d21b'

    uploader = BilibiliUploader(SESSDATA, bili_jct)

    video_file_path = '29283911782-1-16.mp4'
    cover_image_path = '1262dda6e9e0ef341440353f7a35e748ffee61f7.jpg'
    title = "单独上传测试视频"
    description = "补档第1次"
    tags = ["测试", "单独上传"]

    new_bvid = uploader.full_upload_process(video_file_path, cover_image_path, title, description, tags)
    if new_bvid:
        print(f"视频上传成功，bvid: {new_bvid}")
    else:
        print("视频上传失败。")



