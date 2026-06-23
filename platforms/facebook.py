import requests
import json
import os


class FacebookPublisher:
    def __init__(self, access_token, page_id):
        self.access_token = access_token
        self.page_id = page_id
        self.api_base = "https://graph.facebook.com/v22.0"

    def post_video(self, video_path, title, description="", tags=None, video_url=None):
        if not self.access_token or not self.page_id:
            return {"success": False, "error": "Facebook não configurado. Configure o token e page_id."}

        try:
            url = f"{self.api_base}/{self.page_id}/videos"
            params = {"access_token": self.access_token}

            desc = description or ""
            if tags:
                desc += "\n" + " ".join(f"#{t}" for t in tags)

            with open(video_path, "rb") as video_file:
                files = {"source": video_file}
                data = {"title": title, "description": desc}
                response = requests.post(url, params=params, files=files, data=data, timeout=300)

            result = response.json()

            if "id" in result:
                return {"success": True, "post_id": result["id"], "platform": "facebook"}
            return {"success": False, "error": str(result)}

        except requests.Timeout:
            return {"success": False, "platform": "facebook", "error": "Tempo limite excedido ao enviar para Facebook"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_credentials(self):
        if not self.access_token or not self.page_id:
            return {"valid": False, "error": "Token ou Page ID não configurados"}

        try:
            url = f"{self.api_base}/{self.page_id}"
            params = {"access_token": self.access_token, "fields": "name"}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if "name" in data:
                return {"valid": True, "page_name": data["name"]}
            return {"valid": False, "error": str(data)}
        except Exception as e:
            return {"valid": False, "error": str(e)}
