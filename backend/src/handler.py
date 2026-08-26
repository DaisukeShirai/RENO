"""RENO MVP Lambda entry point. Deliberately has no SQS dependency."""
import base64, hashlib, hmac, json, os, time, uuid
from urllib.request import Request, urlopen

import boto3

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
S3 = boto3.client("s3")
SES = boto3.client("ses")


def response(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}, "body": json.dumps(body, ensure_ascii=False, default=str)}


def token_for(subject, role="guest"):
    payload = json.dumps({"sub": subject, "role": role, "exp": int(time.time()) + 7 * 86400}, separators=(",", ":")).encode()
    sig = hmac.new(os.environ["TOKEN_SECRET"].encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"." + sig).decode().rstrip("=")


def subject_from_token(token):
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        payload, sig = raw.rsplit(b".", 1)
        expected = hmac.new(os.environ["TOKEN_SECRET"].encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected): return None
        data = json.loads(payload)
        return data if data["exp"] > time.time() else None
    except Exception:
        return None


def save(item):
    TABLE.put_item(Item=item)
    return item


def chat(body, user):
    messages = body.get("messages", [])
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        input_messages = [{"role": "system", "content": body.get("system", "")}] + [
            {"role": message.get("role", "user"), "content": str(message.get("content", ""))}
            for message in messages if message.get("role") in ("user", "assistant")
        ]
        request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps({"model": os.environ.get("OPENAI_MODEL", "gpt-5-mini"), "input": input_messages, "store": False}, ensure_ascii=False).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=25) as result:
            payload = json.loads(result.read())
        text = payload.get("output_text", "")
        if not text:
            text = "".join(
                part.get("text", "")
                for item in payload.get("output", [])
                for part in item.get("content", [])
                if part.get("type") == "output_text"
            )
    else:
        text = "ご相談内容を確認しました。現状写真をもとに、改善したい部屋とご希望の雰囲気を教えてください。"
    save({"pk": "USER#" + user["sub"], "sk": "CHAT#" + str(time.time_ns()), "messages": messages[-20:], "updated_at": int(time.time())})
    return {"content": [{"type": "text", "text": text}]}


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        typ = body.get("type")
        if typ == "verify_pin":
            pin = body.get("pin", "")
            item = TABLE.get_item(Key={"pk": "PIN#" + pin, "sk": "PIN"}).get("Item")
            if not item or item.get("expires_at", 0) < int(time.time()) or item.get("uses", 0) >= item.get("max_uses", 0): return response(401, {"error": "invalid pin"})
            TABLE.update_item(Key={"pk": "PIN#" + pin, "sk": "PIN"}, UpdateExpression="SET uses = uses + :one", ExpressionAttributeValues={":one": 1})
            return response(200, {"token": token_for("guest:" + pin), "role": "guest", "label": item.get("label", "")})
        user = subject_from_token(body.get("token", ""))
        if not user: return response(401, {"error": "unauthorized"})
        if typ == "chat": return response(200, chat(body, user))
        if typ == "get_usage": return response(200, {"plan": "standard", "count": 0, "limit": 10})
        if typ == "save_session":
            save({"pk": "USER#" + user["sub"], "sk": "SESSION#" + str(time.time_ns()), "data": body.get("data", {}), "created_at": int(time.time())})
            return response(200, {"ok": True})
        if typ == "create_upload_url":
            key = f"uploads/{user['sub']}/{uuid.uuid4().hex}-{body.get('filename', 'image.jpg')}"
            url = S3.generate_presigned_url("put_object", Params={"Bucket": os.environ["ASSET_BUCKET"], "Key": key, "ContentType": body.get("content_type", "image/jpeg")}, ExpiresIn=900)
            return response(200, {"key": key, "upload_url": url, "expires_in": 900})
        if typ == "create_download_url":
            key = body.get("key", "")
            if not key or not key.startswith((f"uploads/{user['sub']}/", f"generated/{user['sub']}/", f"proposals/{user['sub']}/")):
                return response(403, {"error": "forbidden"})
            url = S3.generate_presigned_url("get_object", Params={"Bucket": os.environ["ASSET_BUCKET"], "Key": key}, ExpiresIn=900)
            return response(200, {"download_url": url, "expires_in": 900})
        if typ == "create_guest_pin":
            if user.get("role") != "admin": return response(403, {"error": "admin only"})
            pin = f"{uuid.uuid4().int % 10000:04d}"
            save({"pk": "PIN#" + pin, "sk": "PIN", "label": body.get("label", ""), "uses": 0, "max_uses": int(body.get("max_uses", 3)), "expires_at": int(time.time()) + int(body.get("days", 7)) * 86400})
            return response(200, {"pin": pin, "label": body.get("label", ""), "max_uses": body.get("max_uses", 3), "expires_at": int(time.time()) + int(body.get("days", 7)) * 86400})
        if typ == "handoff":
            if os.environ.get("SES_FROM_EMAIL") and os.environ.get("SES_TO_EMAIL"):
                SES.send_email(Source=os.environ["SES_FROM_EMAIL"], Destination={"ToAddresses": [os.environ["SES_TO_EMAIL"]]}, Message={"Subject": {"Data": "RENO相談受付"}, "Body": {"Text": {"Data": json.dumps(body.get("data", {}), ensure_ascii=False)}}})
            save({"pk": "USER#" + user["sub"], "sk": "HANDOFF#" + str(time.time_ns()), "data": body.get("data", {}), "created_at": int(time.time())})
            return response(200, {"ok": True, "status": "received"})
        return response(400, {"error": "unsupported type"})
    except Exception as exc:
        print(json.dumps({"error": str(exc), "request_id": getattr(context, "aws_request_id", "")}, ensure_ascii=False))
        return response(500, {"error": "internal error"})
