import os
import json
import threading
import time
import secrets
import webbrowser
import hashlib
import base64
import urllib.parse
import logging
from datetime import datetime
import mimetypes
import requests as http_requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

from config import Config
from platforms.facebook import FacebookPublisher
from platforms.instagram import InstagramPublisher
from platforms.tiktok import TikTokPublisher

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

HISTORY_FILE = "publish_history.json"

history = []
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    except (json.JSONDecodeError, IOError):
        history = []


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def get_config():
    return {
        "FACEBOOK_ACCESS_TOKEN": app.config.get("FACEBOOK_ACCESS_TOKEN", ""),
        "FACEBOOK_PAGE_ID": app.config.get("FACEBOOK_PAGE_ID", ""),
        "INSTAGRAM_ACCESS_TOKEN": app.config.get("INSTAGRAM_ACCESS_TOKEN", ""),
        "INSTAGRAM_USER_ID": app.config.get("INSTAGRAM_USER_ID", ""),
        "TIKTOK_CLIENT_KEY": app.config.get("TIKTOK_CLIENT_KEY", ""),
        "TIKTOK_CLIENT_SECRET": app.config.get("TIKTOK_CLIENT_SECRET", ""),
        "TIKTOK_ACCESS_TOKEN": app.config.get("TIKTOK_ACCESS_TOKEN", ""),
        "TIKTOK_OPEN_ID": app.config.get("TIKTOK_OPEN_ID", ""),
    }


def get_platforms_status():
    config = get_config()

    fb = FacebookPublisher(config["FACEBOOK_ACCESS_TOKEN"], config["FACEBOOK_PAGE_ID"])
    fb_status = fb.validate_credentials()

    ig = InstagramPublisher(config["INSTAGRAM_ACCESS_TOKEN"], config["INSTAGRAM_USER_ID"])
    ig_status = ig.validate_credentials()

    tt = TikTokPublisher(
        config["TIKTOK_ACCESS_TOKEN"],
        config["TIKTOK_CLIENT_KEY"],
        config["TIKTOK_CLIENT_SECRET"],
        config.get("TIKTOK_OPEN_ID"),
    )
    tt_status = tt.validate_credentials()

    return {
        "facebook": fb_status,
        "instagram": ig_status,
        "tiktok": tt_status,
    }


def publish_to_platform(platform, video_path, title, description, tags, video_url, results_list):
    config = get_config()

    if platform == "facebook":
        publisher = FacebookPublisher(config["FACEBOOK_ACCESS_TOKEN"], config["FACEBOOK_PAGE_ID"])
    elif platform == "instagram":
        publisher = InstagramPublisher(config["INSTAGRAM_ACCESS_TOKEN"], config["INSTAGRAM_USER_ID"])
    elif platform == "tiktok":
        publisher = TikTokPublisher(
            config["TIKTOK_ACCESS_TOKEN"],
            config["TIKTOK_CLIENT_KEY"],
            config["TIKTOK_CLIENT_SECRET"],
            config.get("TIKTOK_OPEN_ID"),
        )
    else:
        results_list.append({"platform": platform, "success": False, "error": "Plataforma desconhecida"})
        return

    v_url = None if platform == "tiktok" else video_url
    result = publisher.post_video(video_path, title, description, tags=tags, video_url=v_url)
    results_list.append(result)


@app.route("/")
def index():
    platforms_status = get_platforms_status()
    return render_template("index.html", platforms_status=platforms_status)


@app.route("/publish", methods=["POST"])
def publish():
    if "video" not in request.files:
        return jsonify({"success": False, "error": "Nenhum vídeo enviado"}), 400

    video = request.files["video"]
    if video.filename == "" or not allowed_file(video.filename):
        return jsonify({"success": False, "error": "Formato de vídeo não suportado"}), 400

    filename = secure_filename(video.filename)
    timestamp = str(int(time.time()))
    safe_name = f"{timestamp}_{filename}"
    video_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
    video.save(video_path)

    title = request.form.get("title", "Vídeo sem título")
    description = request.form.get("description", "")
    tags = request.form.get("tags", "").strip()
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    selected_platforms = request.form.getlist("platforms")

    if not selected_platforms:
        return jsonify({"success": False, "error": "Selecione pelo menos uma plataforma"}), 400

    video_url = request.host_url.rstrip("/") + url_for("serve_upload", filename=safe_name)

    results = []
    threads = []

    for platform in selected_platforms:
        t = threading.Thread(
            target=publish_to_platform,
            args=(platform, video_path, title, description, tags_list, video_url, results),
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    entry = {
        "title": title,
        "platforms": selected_platforms,
        "tags": tags_list,
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "results": results,
    }
    history.append(entry)
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[-50:], f)
    except IOError:
        pass

    return jsonify({"results": results, "history": history[-20:]})


@app.route("/setup", methods=["GET"])
def setup():
    return render_template("setup.html", config=get_config())

@app.route("/uploads/<filename>")
def serve_upload(filename):
    safe_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    safe_path = os.path.normpath(safe_path)
    if not safe_path.startswith(os.path.normpath(app.config["UPLOAD_FOLDER"])):
        return "Invalid path", 403
    if not os.path.exists(safe_path):
        return "Not found", 404
    mimetype, _ = mimetypes.guess_type(filename)
    with open(safe_path, "rb") as f:
        return f.read(), 200, {"Content-Type": mimetype or "video/mp4"}


@app.route("/setup", methods=["POST"])
def save_config():
    facebook_access_token = request.form.get("facebook_access_token", "")
    facebook_page_id = request.form.get("facebook_page_id", "")
    instagram_access_token = request.form.get("instagram_access_token", "")
    instagram_user_id = request.form.get("instagram_user_id", "")
    tiktok_client_key = request.form.get("tiktok_client_key", "")
    tiktok_client_secret = request.form.get("tiktok_client_secret", "")
    tiktok_access_token = request.form.get("tiktok_access_token", "")
    tiktok_open_id = request.form.get("tiktok_open_id", "")

    env_lines = []
    if facebook_access_token:
        env_lines.append(f"FACEBOOK_ACCESS_TOKEN={facebook_access_token}")
    if facebook_page_id:
        env_lines.append(f"FACEBOOK_PAGE_ID={facebook_page_id}")
    if instagram_access_token:
        env_lines.append(f"INSTAGRAM_ACCESS_TOKEN={instagram_access_token}")
    if instagram_user_id:
        env_lines.append(f"INSTAGRAM_USER_ID={instagram_user_id}")
    if tiktok_client_key:
        env_lines.append(f"TIKTOK_CLIENT_KEY={tiktok_client_key}")
    if tiktok_client_secret:
        env_lines.append(f"TIKTOK_CLIENT_SECRET={tiktok_client_secret}")
    if tiktok_access_token:
        env_lines.append(f"TIKTOK_ACCESS_TOKEN={tiktok_access_token}")
    if tiktok_open_id:
        env_lines.append(f"TIKTOK_OPEN_ID={tiktok_open_id}")

    try:
        with open(".env", "w") as f:
            f.write("\n".join(env_lines))
        for key, value in {
            "FACEBOOK_ACCESS_TOKEN": facebook_access_token,
            "FACEBOOK_PAGE_ID": facebook_page_id,
            "INSTAGRAM_ACCESS_TOKEN": instagram_access_token,
            "INSTAGRAM_USER_ID": instagram_user_id,
            "TIKTOK_CLIENT_KEY": tiktok_client_key,
            "TIKTOK_CLIENT_SECRET": tiktok_client_secret,
            "TIKTOK_ACCESS_TOKEN": tiktok_access_token,
            "TIKTOK_OPEN_ID": tiktok_open_id,
        }.items():
            if value:
                app.config[key] = value
    except IOError as e:
        return jsonify({"success": False, "error": str(e)}), 500

    return redirect(url_for("index"))


@app.route("/auth/tiktok")
def auth_tiktok():
    client_key = app.config.get("TIKTOK_CLIENT_KEY", "")
    log.info("=== INÍCIO FLUXO OAUTH TIKTOK ===")
    log.info("client_key lida: '%s' (len=%d)", client_key, len(client_key))

    if not client_key:
        log.error("client_key está vazia!")
        return jsonify({"success": False, "error": "CLIENT_KEY não configurada. Preencha no /setup primeiro."}), 400

    state = secrets.token_urlsafe(16)
    session["tiktok_oauth_state"] = state
    log.info("state gerado: %s", state)

    code_verifier = secrets.token_urlsafe(64)
    session["tiktok_code_verifier"] = code_verifier
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    log.info("code_verifier (primeiros 20): %s...", code_verifier[:20])
    log.info("code_challenge: %s", code_challenge)

    redirect_uri = url_for("auth_tiktok_callback", _external=True)
    log.info("redirect_uri gerada: %s", redirect_uri)

    params = {
        "client_key": client_key,
        "scope": "user.info.basic,video.publish",
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(params)
    log.info("URL de autorização gerada: %s", auth_url)
    log.info("=== FIM FLUXO OAUTH TIKTOK ===")
    return redirect(auth_url)


@app.route("/auth/tiktok/callback")
def auth_tiktok_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    log.info("=== CALLBACK TIKTOK ===")
    log.info("code: %s", "***" if code else "None")
    log.info("state recebido: %s", state)
    log.info("error: %s", error)
    log.info("args completos: %s", dict(request.args))

    if error:
        log.error("Erro retornado pelo TikTok: %s", error)
        return f"Erro na autoriza\u00e7\u00e3o TikTok: {error}", 400

    saved_state = session.pop("tiktok_oauth_state", None)
    log.info("saved_state: %s", saved_state)
    if not state or not saved_state or state != saved_state:
        log.error("state inválido! state=%s saved_state=%s", state, saved_state)
        return "Erro: state inv\u00e1lido (poss\u00edvel CSRF). Tente novamente.", 400

    if not code:
        log.error("Código de autorização não recebido")
        return "Erro: c\u00f3digo de autoriza\u00e7\u00e3o n\u00e3o recebido.", 400

    code_verifier = session.pop("tiktok_code_verifier", None)
    log.info("code_verifier recuperado: %s", "***" if code_verifier else "None")
    if not code_verifier:
        log.error("code_verifier não encontrado na sessão")
        return "Erro: code_verifier n\u00e3o encontrado na sess\u00e3o. Inicie o fluxo novamente.", 400

    client_key = app.config.get("TIKTOK_CLIENT_KEY", "")
    client_secret = app.config.get("TIKTOK_CLIENT_SECRET", "")
    redirect_uri = url_for("auth_tiktok_callback", _external=True)
    log.info("client_key: '%s'", client_key)
    log.info("client_secret: '%s'", "***" if client_secret else "vazio")
    log.info("redirect_uri: %s", redirect_uri)

    try:
        log.info("Fazendo POST para troca de token...")
        resp = http_requests.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            timeout=30,
        )
        log.info("Status code da resposta: %d", resp.status_code)
        log.info("Resposta bruta: %s", resp.text[:500])

        data = resp.json()
        log.info("Resposta JSON: %s", json.dumps(data, indent=2)[:500])

        if "access_token" not in data:
            log.error("Token não veio na resposta: %s", data)
            return f"Erro ao obter token: {json.dumps(data)}", 400

        access_token = data["access_token"]
        open_id = data.get("open_id", "")
        token_type = data.get("token_type", "Bearer")
        expires_in = data.get("expires_in", 0)

        env_path = os.path.join(os.path.dirname(__file__), ".env")
        env_lines = {}
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, val = line.split("=", 1)
                        env_lines[key] = val

        env_lines["TIKTOK_ACCESS_TOKEN"] = access_token
        env_lines["TIKTOK_OPEN_ID"] = open_id
        if not env_lines.get("TIKTOK_CLIENT_KEY"):
            env_lines["TIKTOK_CLIENT_KEY"] = client_key
        if not env_lines.get("TIKTOK_CLIENT_SECRET"):
            env_lines["TIKTOK_CLIENT_SECRET"] = client_secret

        with open(env_path, "w") as f:
            for key, val in env_lines.items():
                f.write(f"{key}={val}\n")

        app.config["TIKTOK_ACCESS_TOKEN"] = access_token
        app.config["TIKTOK_OPEN_ID"] = open_id

        return f"""
        <html><body style="background:#0f0c29;color:#e0e0e0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh">
        <div style="text-align:center;background:rgba(255,255,255,0.04);padding:40px;border-radius:16px;border:1px solid rgba(255,255,255,0.06)">
            <h1 style="color:#00d2ff">✅ TikTok Conectado!</h1>
            <p>Access Token salvo com sucesso.</p>
            <p style="font-size:0.8rem;color:#888;word-break:break-all">Open ID: {open_id}</p>
            <br>
            <a href="/" style="color:#00d2ff;text-decoration:none;font-weight:600">Voltar ao Dashboard</a>
        </div>
        </body></html>
        """

    except Exception as e:
        log.exception("Exceção na troca do código: %s", e)
        return f"Erro na troca do c\u00f3digo: {e}", 500


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5000)
