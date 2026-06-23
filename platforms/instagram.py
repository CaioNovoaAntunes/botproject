import requests
import json
import os


class InstagramPublisher:
    def __init__(self, access_token, user_id):
        self.access_token = access_token
        self.user_id = user_id
        self.api_base = "https://graph.facebook.com/v22.0"

    def post_video(self, video_path, title, description="", tags=None, video_url=None):
        if not self.access_token or not self.user_id:
            return {"success": False, "error": "Instagram não configurado. Configure o token e user_id."}

        if not video_url:
            return {"success": False, "error": "Instagram requer uma URL pública do vídeo para publicação."}

        try:
            caption = title
            if description:
                caption += f"\n\n{description}"
            if tags:
                caption += "\n" + " ".join(f"#{t}" for t in tags)
            if len(caption) > 2200:
                caption = caption[:2197] + "..."

            params = {"access_token": self.access_token}

            media_url = f"{self.api_base}/{self.user_id}/media"
            media_data = {
                "media_type": "VIDEO",
                "video_url": video_url,
                "caption": caption,
            }
            init_response = requests.post(media_url, params=params, data=media_data, timeout=30)
            init_result = init_response.json()

            if "id" not in init_result:
                return {"success": False, "platform": "instagram", "error": str(init_result)}

            media_id = init_result["id"]
            publish_url = f"{self.api_base}/{self.user_id}/media_publish"
            publish_response = requests.post(publish_url, params=params, data={"creation_id": media_id}, timeout=30)
            publish_result = publish_response.json()

            if "id" in publish_result:
                return {"success": True, "post_id": publish_result["id"], "platform": "instagram"}
            return {"success": False, "platform": "instagram", "error": str(publish_result)}

        except requests.Timeout:
            return {"success": False, "platform": "instagram", "error": "Tempo limite excedido ao conectar com Instagram"}
        except Exception as e:
            return {"success": False, "platform": "instagram", "error": str(e)}

    def validate_credentials(self):
        if not self.access_token or not self.user_id:
            return {"valid": False, "error": "Token ou User ID não configurados"}

        try:
            url = f"{self.api_base}/{self.user_id}"
            params = {"access_token": self.access_token, "fields": "username,name"}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if "username" in data:
                return {"valid": True, "username": data["username"]}
            return {"valid": False, "error": str(data)}
        except Exception as e:
            return {"valid": False, "error": str(e)}
