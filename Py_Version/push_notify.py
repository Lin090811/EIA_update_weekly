#!/usr/bin/env python3
"""
EIA 数据推送模块 (macOS 适用)
支持多种推送方式，通过 config.ini [Push] 配置

推送方式:
  notification - macOS 系统通知（无需配置）
  telegram     - Telegram Bot 发送图片
  wecom        - 企业微信机器人 Webhook
  dingtalk     - 钉钉机器人 Webhook（图片通过 GitHub 仓库托管）
  pushplus     - PushPlus 微信推送（需微信公众号关注）
"""
import os
import shutil
import base64
import configparser
import platform
import subprocess
import datetime


def upload_to_github(files, repo_dir, repo_url):
    """
    将图片文件推送到 GitHub 仓库，返回 raw 链接列表
    repo_dir: 本地 git 仓库路径
    repo_url: GitHub 仓库 URL (如 https://github.com/user/repo)
    返回: [(filename, raw_url), ...]
    """
    if not os.path.isdir(repo_dir):
        print(f"  [图床] 仓库目录不存在: {repo_dir}")
        return [(os.path.basename(f), None) for f in files]

    date_folder = datetime.datetime.now().strftime('%Y-%m-%d')
    target_dir = os.path.join(repo_dir, date_folder)
    os.makedirs(target_dir, exist_ok=True)

    results = []
    try:
        for f in files:
            fname = os.path.basename(f)
            if not os.path.isfile(f):
                results.append((fname, None))
                continue
            shutil.copy2(f, os.path.join(target_dir, fname))
            results.append((fname, True))

        # git add, commit, pull (rebase), push
        subprocess.run(["git", "add", "-A"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"EIA update {date_folder}"],
                       cwd=repo_dir, capture_output=True)
        # 先 pull 远程最新变更再 push，避免冲突
        pull_result = subprocess.run(["git", "pull", "--rebase", "origin", "main"],
                                    cwd=repo_dir, capture_output=True, timeout=60)
        if pull_result.returncode != 0:
            print(f"  [图床] git pull 警告: {pull_result.stderr.decode()}")
        push_result = subprocess.run(["git", "push", "origin", "main"],
                                     cwd=repo_dir, capture_output=True, timeout=120)
        if push_result.returncode != 0:
            print(f"  [图床] git push 失败: {push_result.stderr.decode()}")
            return [(fn, None) for fn, _ in results]

        # 构建 raw URL
        # 从 repo_url 提取 user/repo: https://github.com/user/repo.git -> user/repo
        repo_path = repo_url.rstrip("/")
        if repo_path.endswith(".git"):
            repo_path = repo_path[:-4]
        repo_path = repo_path.replace("https://github.com/", "")

        final = []
        for fn, ok in results:
            if ok:
                raw_url = f"https://raw.githubusercontent.com/{repo_path}/main/{date_folder}/{fn}"
                final.append((fn, raw_url))
            else:
                final.append((fn, None))
        return final

    except Exception as e:
        print(f"  [图床] 上传异常: {e}")
        return [(os.path.basename(f), None) for f in files]


def _send_request(url, payload, desc="推送"):
    """通用 HTTP POST 请求，返回 (ok, message)"""
    import requests
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            resp = r.json()
            if resp.get("errcode", 0) == 0 or resp.get("ok", False) or r.status_code == 200:
                return True, f"{desc}成功"
            else:
                return False, f"{desc}失败: {resp}"
        else:
            return False, f"{desc}失败 (HTTP {r.status_code}): {r.text}"
    except Exception as e:
        return False, f"{desc}异常: {e}"


def push_files_macos(files, method="notification"):
    """
    在 macOS 上推送文件/通知
    支持多种推送方式，可通过 config.ini 配置多个渠道同时推送
    method 可以是逗号分隔的多个方式，如 "dingtalk,pushplus"
    """
    import requests
    config = configparser.ConfigParser()
    config.read("config.ini", encoding="utf-8")

    results = []
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    img_links = []  # 图片链接缓存，多个推送渠道可复用

    # 允许多渠道推送，method 支持 "dingtalk,pushplus" 这种写法
    methods = [m.strip().lower() for m in method.split(",")]

    # 方法1: macOS 系统通知（本地提醒，不需要额外配置）
    if "notification" in methods:
        for f in files:
            fname = os.path.basename(f)
            script = f'''
            display notification "EIA 油品数据已更新\\n文件: {fname}" with title "EIA 数据更新完成" sound name "Glass"
            '''
            subprocess.run(["osascript", "-e", script])
        results.append(f"系统通知已发送 ({len(files)} 个文件)")

    # 方法2: Telegram Bot
    if "telegram" in methods and config.has_option("Push", "telegram_token") and config.has_option("Push", "telegram_chat_id"):
        token = config.get("Push", "telegram_token").strip()
        chat_id = config.get("Push", "telegram_chat_id").strip()
        for f in files:
            if not os.path.isfile(f):
                results.append(f"文件不存在: {f}")
                continue
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(f, 'rb') as pic:
                r = requests.post(url, data={"chat_id": chat_id}, files={"photo": pic})
            if r.status_code == 200:
                results.append(f"Telegram 推送成功: {os.path.basename(f)}")
            else:
                results.append(f"Telegram 推送失败: {r.text}")

    # 方法3: 企业微信机器人 Webhook
    if "wecom" in methods and config.has_option("Push", "wecom_webhook"):
        webhook = config.get("Push", "wecom_webhook").strip()
        msg = {
            "msgtype": "text",
            "text": {
                "content": f"EIA 油品数据已更新 ({now_str})，请查看生成的图表。",
                "mentioned_list": ["@all"]
            }
        }
        ok, info = _send_request(webhook, msg, "企业微信")
        results.append(info)

    # 方法4: 钉钉机器人 Webhook（图片通过 GitHub 仓库托管）
    if "dingtalk" in methods and config.has_option("Push", "dingtalk_webhook"):
        webhook = config.get("Push", "dingtalk_webhook").strip()
        secret = ""
        if config.has_option("Push", "dingtalk_secret"):
            secret = config.get("Push", "dingtalk_secret").strip()

        # 如果配置了加签密钥，需要签名
        if secret:
            import time
            import hmac
            import hashlib
            timestamp = str(round(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256
            ).digest()
            sign = base64.b64encode(hmac_code).decode("utf-8")
            webhook = f"{webhook}&timestamp={timestamp}&sign={sign}"

        # 上传图片到 GitHub 图床
        script_dir = os.path.dirname(os.path.abspath(__file__))
        images_repo_dir = os.path.join(script_dir, "eia-images-repo")
        images_repo_url = "https://github.com/Lin090811/EIA-data.git"
        img_links = upload_to_github(files, images_repo_dir, images_repo_url)

        # 构造 Markdown 消息，嵌入图片链接
        md_text = f"### EIA 油品数据已更新\n\n- 时间: {now_str}\n\n"
        has_images = False
        for fname, url in img_links:
            if url:
                md_text += f"#### {fname}\n\n![{fname}]({url})\n\n"
                has_images = True
            else:
                md_text += f"- {fname}（图片上传失败）\n\n"
        if not has_images:
            file_names = ", ".join(os.path.basename(f) for f in files)
            md_text += f"\n请到服务器查看图表文件: {file_names}\n"

        msg = {
            "msgtype": "markdown",
            "markdown": {
                "title": "EIA 数据更新完成",
                "text": md_text
            }
        }
        ok, info = _send_request(webhook, msg, "钉钉")
        results.append(info)

    # 方法5: PushPlus 微信推送（图片通过 GitHub 仓库托管）
    if "pushplus" in methods and config.has_option("Push", "pushplus_token"):
        token = config.get("Push", "pushplus_token").strip()

        # 复用已有的 img_links（如果钉钉已经上传过）
        if not img_links:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            images_repo_dir = os.path.join(script_dir, "eia-images-repo")
            images_repo_url = "https://github.com/Lin090811/EIA-data.git"
            img_links = upload_to_github(files, images_repo_dir, images_repo_url)

        # 构建 HTML 内容，嵌入 GitHub 图片链接
        html_content = f"<h3>EIA 油品数据已更新</h3><p>时间: {now_str}</p><hr>"
        has_images = False
        for fname, url in img_links:
            if url:
                html_content += f'<p><b>{fname}</b></p><img src="{url}" style="max-width:100%;margin:8px 0;">'
                has_images = True
            else:
                html_content += f'<p>{fname}（图片上传失败）</p>'
        if not has_images:
            file_names = ", ".join(os.path.basename(f) for f in files)
            html_content += f"<p>文件: {file_names}</p>"

        try:
            payload = {
                "token": token,
                "title": f"EIA 油品数据已更新 ({now_str})",
                "content": html_content,
                "template": "html",
                "topic": ""
            }
            if config.has_option("Push", "pushplus_topic"):
                payload["topic"] = config.get("Push", "pushplus_topic").strip()
            ok, info = _send_request("http://www.pushplus.plus/send", payload, "PushPlus")
            results.append(info)
        except Exception as e:
            fallback_payload = {
                "token": token,
                "title": f"EIA 油品数据已更新 ({now_str})",
                "content": f"EIA 油品数据已更新，请查看 GitHub 仓库获取图表。",
                "template": "txt",
            }
            if config.has_option("Push", "pushplus_topic"):
                fallback_payload["topic"] = config.get("Push", "pushplus_topic").strip()
            ok, info = _send_request("http://www.pushplus.plus/send", fallback_payload, "PushPlus")
            results.append(info)

    return results


def push_results():
    """
    主推送函数，根据 config.ini 配置自动推送
    在 macOS 上：优先系统通知 + 可选的 Telegram/企业微信
    在 Windows 上：保留原有微信文件发送逻辑
    """
    pic_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pic")
    config = configparser.ConfigParser()
    config.read("config.ini", encoding="utf-8")

    # 收集生成的图片文件（仅推送合并图）
    files = []
    for f in ["eia.png"]:
        fpath = os.path.join(pic_dir, f)
        if os.path.isfile(fpath):
            files.append(fpath)

    if not files:
        print("[推送] 未找到生成的图片文件")
        return

    # 读取推送方式
    method = "notification"
    if config.has_option("Push", "method"):
        method = config.get("Push", "method").strip()

    print(f"[推送] 使用方式: {method}，文件数: {len(files)}")

    if platform.system() == "Darwin":
        # macOS: 使用推送模块
        results = push_files_macos(files, method)
        for r in results:
            print(f"  {r}")
    elif platform.system() == "Windows":
        # Windows: 使用原有微信发送逻辑
        print("[推送] Windows 平台，使用微信发送...")
        try:
            from wechat_send import sending_pics
            sending_pics()
        except Exception as e:
            print(f"[推送] 微信发送失败: {e}")
    else:
        print(f"[推送] 未知平台: {platform.system()}")


if __name__ == "__main__":
    push_results()
