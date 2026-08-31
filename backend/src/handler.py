"""RENO MVP APIのエントリーポイント。"""
import base64, hashlib, hmac, json, os, posixpath, time, uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import boto3
from boto3.dynamodb.conditions import Attr, Key

AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")
TABLE = boto3.resource("dynamodb", endpoint_url=AWS_ENDPOINT_URL).Table(os.environ["TABLE_NAME"])
S3 = boto3.client("s3", endpoint_url=AWS_ENDPOINT_URL)
SES = boto3.client("ses", endpoint_url=AWS_ENDPOINT_URL)
COGNITO = boto3.client("cognito-idp", endpoint_url=AWS_ENDPOINT_URL)
USAGE_LIMIT = 10
UNLIMITED_MODE = os.environ.get("UNLIMITED_MODE", "false").strip().lower() == "true"
MAX_INPUT_MESSAGES = 20
MAX_MESSAGE_CHARS = 4000
MAX_SYSTEM_CHARS = 8000
MAX_OUTPUT_TOKENS = 500

ESTIMATE_SIZES = {"6": 10, "8": 13, "10": 16, "12": 20}
ESTIMATE_ITEMS = {
    "floor": {"base": (8, 15), "unit": "m2", "weeks": (1, 2)},
    "wall": {"base": (1, 2.5), "unit": "m2", "weeks": (1, 2)},
    "kitchen": {"base": (60, 180), "unit": "flat", "weeks": (2, 3)},
    "bath": {"base": (60, 150), "unit": "flat", "weeks": (2, 3)},
    "toilet": {"base": (15, 50), "unit": "flat", "weeks": (1, 2)},
    "wash": {"base": (15, 50), "unit": "flat", "weeks": (1, 2)},
    "light": {"base": (8, 30), "unit": "flat", "weeks": (1, 1)},
    "storage": {"base": (15, 60), "unit": "flat", "weeks": (1, 2)},
}
ESTIMATE_GRADES = {"eco": 0.75, "std": 1.0, "pre": 1.5}


def response(status, body):
    return {"statusCode": status, "headers": {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,apikey",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
    }, "body": json.dumps(body, ensure_ascii=False, default=str)}


def token_for(subject, role="guest"):
    payload = json.dumps({"sub": subject, "role": role, "exp": int(time.time()) + 7 * 86400}, separators=(",", ":")).encode()
    sig = hmac.new(os.environ["TOKEN_SECRET"].encode(), payload, hashlib.sha256).digest()
    # payloadと署名を分離してエンコードし、署名中の`.`を区切り文字と誤認しない。
    encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
    return encode(payload) + "." + encode(sig)


def subject_from_token(token):
    try:
        if not isinstance(token, str): return None
        if "." in token:
            payload_token, signature_token = token.split(".", 1)
            payload = base64.urlsafe_b64decode(payload_token + "=" * (-len(payload_token) % 4))
            signature = base64.urlsafe_b64decode(signature_token + "=" * (-len(signature_token) % 4))
        else:
            # 旧形式（payload + b"." + signatureをまとめてBase64化）も許容する。
            raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
            payload, signature = raw.rsplit(b".", 1)
        expected = hmac.new(os.environ["TOKEN_SECRET"].encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected): return None
        data = json.loads(payload)
        return data if data.get("exp", 0) > time.time() and data.get("sub") else None
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def save(item):
    TABLE.put_item(Item=item)
    return item


def query_user(user, prefix):
    result = TABLE.query(KeyConditionExpression=Key("pk").eq("USER#" + user["sub"]) & Key("sk").begins_with(prefix), ScanIndexForward=False)
    return result.get("Items", [])


def usage(user):
    count = len(query_user(user, "CHAT#"))
    return {"plan": "unlimited" if UNLIMITED_MODE else "standard", "count": count, "limit": USAGE_LIMIT, "remaining": None if UNLIMITED_MODE else max(0, USAGE_LIMIT - count), "unlimited": UNLIMITED_MODE}


def safe_filename(name):
    name = posixpath.basename(str(name or "image.jpg")).replace("\\", "_")
    return "".join(c for c in name if c.isalnum() or c in "._-")[:120] or "image.jpg"


def chat(body, user):
    messages = body.get("messages", [])
    if not isinstance(messages, list) or len(messages) > 50: return {"error": "messages must be an array of at most 50 items"}
    current = usage(user)
    if not UNLIMITED_MODE and current["count"] >= current["limit"]: return {"error": "usage limit reached", "usage": current}
    # CIの空値指定などで空白だけが渡っても、OpenAI API呼び出しへ進めない。
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key:
        input_messages = ([{"role": "system", "content": str(body.get("system", ""))[:MAX_SYSTEM_CHARS]}] + [{"role": m.get("role", "user"), "content": str(m.get("content", ""))[:MAX_MESSAGE_CHARS]} for m in messages[-MAX_INPUT_MESSAGES:] if isinstance(m, dict) and m.get("role") in ("user", "assistant")])
        request = Request("https://api.openai.com/v1/responses", data=json.dumps({"model": os.environ.get("OPENAI_MODEL", "gpt-5-mini"), "input": input_messages, "max_output_tokens": MAX_OUTPUT_TOKENS, "store": False}).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=25) as result: payload = json.loads(result.read())
        except (HTTPError, URLError, TimeoutError) as exc:
            print(json.dumps({"openai_error": str(exc)}, ensure_ascii=False))
            return {"error": "AI service is temporarily unavailable"}
        text = payload.get("output_text", "") or "".join(part.get("text", "") for item in payload.get("output", []) for part in item.get("content", []) if part.get("type") == "output_text")
    else:
        text = "ご相談内容を確認しました。現在の状態・ご希望の部屋・ご予算を教えてください。"
    save({"pk": "USER#" + user["sub"], "sk": "CHAT#" + str(time.time_ns()), "messages": messages[-20:], "updated_at": int(time.time())})
    return {"content": [{"type": "text", "text": text}], "usage": usage(user)}


def estimate(body, user):
    """サーバー側の料金マスタで計算し、AIには説明文だけを生成させる。"""
    size_key = str(body.get("size", "8"))
    item_keys = body.get("items", [])
    grade_key = str(body.get("grade", "std"))
    if size_key not in ESTIMATE_SIZES or grade_key not in ESTIMATE_GRADES:
        return {"error": "invalid estimate condition"}
    if not isinstance(item_keys, list) or not item_keys or any(key not in ESTIMATE_ITEMS for key in item_keys):
        return {"error": "at least one valid estimate item is required"}

    m2 = ESTIMATE_SIZES[size_key]
    multiplier = ESTIMATE_GRADES[grade_key]
    low = high = 0
    low_weeks = high_weeks = 0
    for key in dict.fromkeys(item_keys):
        item = ESTIMATE_ITEMS[key]
        factor = m2 if item["unit"] == "m2" else 1
        low += item["base"][0] * factor * 10000
        high += item["base"][1] * factor * 10000
        low_weeks = max(low_weeks, item["weeks"][0])
        high_weeks = max(high_weeks, item["weeks"][1])
    low = round(low * multiplier / 10000) * 10000
    high = round(high * multiplier / 10000) * 10000
    duration = {"low": max(1, low_weeks), "high": max(low_weeks, high_weeks)}

    explanation = "選択した工事内容と面積をもとに、標準的な施工条件で概算しています。"
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key:
        prompt = (
            "あなたはリフォーム見積りアシスタントです。以下の計算済み結果を変更せず、"
            "前提と注意点を含む日本語の説明を80文字以内で返してください。金額や工期を新たに計算しないでください。\n"
            f"面積:{m2}m2、工事項目:{','.join(dict.fromkeys(item_keys))}、グレード:{grade_key}、"
            f"概算:{low}〜{high}円、工期:{duration['low']}〜{duration['high']}週間"
        )
        request = Request("https://api.openai.com/v1/responses", data=json.dumps({
            "model": os.environ.get("OPENAI_MODEL", "gpt-5-mini"),
            "input": [{"role": "system", "content": "リフォーム業務の説明を簡潔かつ正確に行う。"}, {"role": "user", "content": prompt}],
            "max_output_tokens": 160,
            "store": False,
        }).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=15) as result:
                payload = json.loads(result.read())
            explanation = payload.get("output_text", "") or explanation
        except (HTTPError, URLError, TimeoutError):
            explanation = "計算済みの概算です。現地調査と仕様確定後に正式なお見積りとなります。"
    return {"estimate": {"low": low, "high": high}, "duration": duration, "explanation": explanation, "source": "ai" if api_key else "rule"}


def lambda_handler(event, context):
    try:
        method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
        if method == "OPTIONS": return response(204, {})
        body = json.loads(event.get("body") or "{}")
        if not isinstance(body, dict): return response(400, {"error": "request body must be an object"})
        typ = body.get("type")
        if typ == "demo_login":
            # PINなしの動作デモ用。ブラウザごとに利用量を分けるため識別子をハッシュ化する。
            demo_id = str(body.get("demo_id", "browser"))[:120]
            subject = "demo:" + hashlib.sha256(demo_id.encode()).hexdigest()[:32]
            return response(200, {"token": token_for(subject), "role": "guest", "label": "動作デモ"})
        if typ == "verify_pin":
            pin = str(body.get("pin", ""))
            demo_pin = os.environ.get("DEMO_PIN", "").strip()
            if demo_pin and pin == demo_pin:
                return response(200, {"token": token_for("demo:" + pin), "role": "guest", "label": "デモ用PIN"})
            item = TABLE.get_item(Key={"pk": "PIN#" + pin, "sk": "PIN"}).get("Item")
            if not item or item.get("expires_at", 0) < int(time.time()) or item.get("uses", 0) >= item.get("max_uses", 0): return response(401, {"error": "invalid pin"})
            TABLE.update_item(Key={"pk": "PIN#" + pin, "sk": "PIN"}, UpdateExpression="SET uses = uses + :one", ExpressionAttributeValues={":one": 1})
            return response(200, {"token": token_for("guest:" + pin), "role": "guest", "label": item.get("label", "")})
        if typ == "cognito_login":
            access_token = str(body.get("access_token", ""))
            admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
            if not access_token or not admin_email: return response(401, {"error": "admin login is not configured"})
            try:
                cognito_user = COGNITO.get_user(AccessToken=access_token)
                attributes = {item.get("Name"): item.get("Value", "") for item in cognito_user.get("UserAttributes", [])}
                email = attributes.get("email", "").strip().lower()
                if not email or email != admin_email: return response(403, {"error": "admin access denied"})
                return response(200, {"token": token_for("admin:" + email, "admin"), "role": "admin", "email": email})
            except Exception:
                return response(401, {"error": "invalid Cognito session"})
        user = subject_from_token(body.get("token", ""))
        if not user: return response(401, {"error": "unauthorized"})
        if typ == "chat":
            result = chat(body, user)
            status = 429 if "usage limit" in result.get("error", "") else 503 if "unavailable" in result.get("error", "") else 400 if "messages" in result.get("error", "") else 200
            return response(status, result)
        if typ == "estimate":
            result = estimate(body, user)
            status = 400 if "error" in result else 200
            return response(status, result)
        if typ == "get_usage": return response(200, usage(user))
        if typ == "save_session":
            save({"pk": "USER#" + user["sub"], "sk": "SESSION#" + str(time.time_ns()), "data": body.get("data", {}), "created_at": int(time.time())})
            return response(200, {"ok": True})
        if typ == "create_upload_url":
            content_type = str(body.get("content_type", "image/jpeg"))
            if content_type not in ("image/jpeg", "image/png", "image/webp", "application/pdf"): return response(400, {"error": "unsupported content type"})
            key = f"uploads/{user['sub']}/{uuid.uuid4().hex}-{safe_filename(body.get('filename'))}"
            url = S3.generate_presigned_url("put_object", Params={"Bucket": os.environ["ASSET_BUCKET"], "Key": key, "ContentType": content_type}, ExpiresIn=900)
            return response(200, {"key": key, "upload_url": url, "expires_in": 900})
        if typ == "create_download_url":
            key = str(body.get("key", "")); allowed = (f"uploads/{user['sub']}/", f"generated/{user['sub']}/", f"proposals/{user['sub']}/")
            if not key.startswith(allowed): return response(403, {"error": "forbidden"})
            url = S3.generate_presigned_url("get_object", Params={"Bucket": os.environ["ASSET_BUCKET"], "Key": key}, ExpiresIn=900)
            return response(200, {"download_url": url, "expires_in": 900})
        if typ == "create_guest_pin":
            if user.get("role") != "admin": return response(403, {"error": "admin only"})
            pin = f"{uuid.uuid4().int % 10000:04d}"; max_uses = min(100, max(1, int(body.get("max_uses", 30)))); expires_at = int(time.time()) + min(30, max(1, int(body.get("days", 7)))) * 86400
            save({"pk": "PIN#" + pin, "sk": "PIN", "owner_sub": user["sub"], "label": str(body.get("label", ""))[:120], "uses": 0, "max_uses": max_uses, "expires_at": expires_at})
            return response(200, {"pin": pin, "label": body.get("label", ""), "max_uses": max_uses, "expires_at": expires_at * 1000})
        if typ == "get_guest_pins":
            if user.get("role") != "admin": return response(403, {"error": "admin only"})
            items = TABLE.scan(FilterExpression=Attr("owner_sub").eq(user["sub"])).get("Items", [])
            return response(200, [{"id": i["pk"].replace("PIN#", ""), "pin": i["pk"].replace("PIN#", ""), "label": i.get("label", ""), "use_count": i.get("uses", 0), "max_uses": i.get("max_uses", 0), "expires_at": i.get("expires_at", 0) * 1000, "is_active": i.get("uses", 0) < i.get("max_uses", 0) and i.get("expires_at", 0) > int(time.time())} for i in items])
        if typ == "delete_guest_pin":
            if user.get("role") != "admin": return response(403, {"error": "admin only"})
            pin = str(body.get("id", "")); item = TABLE.get_item(Key={"pk": "PIN#" + pin, "sk": "PIN"}).get("Item")
            if not item or item.get("owner_sub") != user["sub"]: return response(404, {"error": "pin not found"})
            TABLE.delete_item(Key={"pk": "PIN#" + pin, "sk": "PIN"}); return response(200, {"ok": True})
        if typ == "save_case":
            title, room = str(body.get("title", "")).strip(), str(body.get("room", "")).strip()
            if not title or not room: return response(400, {"error": "title and room are required"})
            image = str(body.get("image_data", ""))
            if len(image) > 700_000: return response(413, {"error": "image is too large"})
            item = {"pk": "USER#" + user["sub"], "sk": "CASE#" + str(uuid.uuid4()), "id": str(uuid.uuid4()), "title": title[:120], "room": room[:80], "style": str(body.get("style", ""))[:80], "budget_range": str(body.get("budget_range", ""))[:80], "description": str(body.get("description", ""))[:1000], "image_data": image, "created_at": int(time.time())}
            save(item); return response(200, {"ok": True, "case": item})
        if typ == "get_cases":
            room, style = str(body.get("room", "")), str(body.get("style", "")); items = query_user(user, "CASE#")
            return response(200, [i for i in items if (not room or i.get("room") == room) and (not style or i.get("style") == style)])
        if typ == "delete_case":
            items = [i for i in query_user(user, "CASE#") if i.get("id") == str(body.get("id", ""))]
            if not items: return response(404, {"error": "case not found"})
            TABLE.delete_item(Key={"pk": items[0]["pk"], "sk": items[0]["sk"]}); return response(200, {"ok": True})
        if typ == "handoff":
            if os.environ.get("SES_FROM_EMAIL") and os.environ.get("SES_TO_EMAIL"):
                SES.send_email(Source=os.environ["SES_FROM_EMAIL"], Destination={"ToAddresses": [os.environ["SES_TO_EMAIL"]]}, Message={"Subject": {"Data": "RENO相談受付"}, "Body": {"Text": {"Data": json.dumps(body.get("data", {}), ensure_ascii=False)}}})
            save({"pk": "USER#" + user["sub"], "sk": "HANDOFF#" + str(time.time_ns()), "data": body.get("data", {}), "created_at": int(time.time())})
            return response(200, {"ok": True, "status": "received"})
        return response(400, {"error": "unsupported type"})
    except Exception as exc:
        print(json.dumps({"error": str(exc), "request_id": getattr(context, "aws_request_id", "")}, ensure_ascii=False))
        return response(500, {"error": "internal error"})
