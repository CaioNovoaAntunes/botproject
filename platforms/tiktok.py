import requests
import json
import os
import time


class TikTokPublisher:
    def __init__(self, access_token, client_key=None, client_secret=None, open_id=None):
        self.access_token = access_token
        self.client_key = client_key
        self.client_secret = client_secret
        self.open_id = open_id
        self.api_base = "https://open.tiktokapis.com"

    def post_video(self, video_path, title, description="", tags=None, video_url=None):
        if not self.access_token:
            return {"success": False, "error": "TikTok não configurado. Configure o token de acesso."}

        try:
            combined = title
            if description:
                combined += "\n\n" + description
            if tags:
                combined += "\n" + " ".join(f"#{t}" for t in tags)

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            }

            post_info = {
                "title": combined[:2200],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            }

            if video_url:
                # Direct Post — PULL_FROM_URL
                init_url = f"{self.api_base}/v2/post/publish/inbox/video/init/"
                source_info = {
                    "source": "PULL_FROM_URL",
                    "video_url": video_url,
                }
                data = {
                    "post_info": post_info,
                    "source_info": source_info,
                }
                if self.open_id:
                    data["open_id"] = self.open_id
            else:
                # Upload — FILE_UPLOAD
                init_url = f"{self.api_base}/v2/post/publish/video/init/"
                chunk_size = 5 * 1024 * 1024
                file_size = os.path.getsize(video_path)
                total_chunks = max(1, (file_size + chunk_size - 1) // chunk_size)
                source_info = {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": chunk_size,
                    "total_chunk_count": total_chunks,
                }
                data = {
                    "post_info": post_info,
                    "source_info": source_info,
                }

            response = requests.post(init_url, headers=headers, json=data, timeout=30)
            result = response.json()

            if response.status_code != 200 or result.get("error", {}).get("code") != "ok":
                err = result.get("error", result)
                return {
                    "success": False,
                    "platform": "tiktok",
                    "error": err.get("message", str(result)),
                }

            publish_id = result["data"]["publish_id"]
            upload_url = result["data"].get("upload_url")

            # FILE_UPLOAD: make the PUT to upload_url
            if not video_url and upload_url:
                file_size = os.path.getsize(video_path)
                with open(video_path, "rb") as f:
                    data_bytes = f.read()

                upload_headers = {
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(data_bytes)),
                    "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                }
                upload_resp = requests.put(upload_url, headers=upload_headers, data=data_bytes, timeout=300)
                if upload_resp.status_code not in (200, 201):
                    return {
                        "success": False,
                        "platform": "tiktok",
                        "error": f"Falha no upload: {upload_resp.status_code}",
                    }

            return {
                "success": True,
                "publish_id": publish_id,
                "platform": "tiktok",
                "message": "Vídeo enviado ao TikTok com sucesso.",
            }

        except requests.Timeout:
            return {"success": False, "platform": "tiktok", "error": "Tempo limite excedido ao conectar com TikTok"}
        except Exception as e:
            return {"success": False, "platform": "tiktok", "error": str(e)}

    def validate_credentials(self):
        if not self.access_token:
            return {"valid": False, "error": "Token de acesso não configurado"}

        try:
            url = f"{self.api_base}/v2/user/info/"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            params = {"fields": "open_id,union_id,display_name"}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()

            if data.get("error", {}).get("code") == "ok":
                user = data.get("data", {}).get("user", {})
                return {"valid": True, "username": user.get("display_name", "N/A")}
            return {"valid": False, "error": str(data)}
        except Exception as e:
            return {"valid": False, "error": str(e)}
