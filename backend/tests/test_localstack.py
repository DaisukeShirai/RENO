import json
import os
import sys
import time
import unittest
from urllib.request import urlopen

import boto3
from botocore.exceptions import ClientError


ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://127.0.0.1:4566")
TABLE_NAME = "reno-localstack-test"
BUCKET_NAME = "reno-localstack-assets"

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("TABLE_NAME", TABLE_NAME)
os.environ.setdefault("ASSET_BUCKET", BUCKET_NAME)
# CI環境に同名の秘密があっても、発行と検証で同じテスト用秘密を使う。
os.environ["TOKEN_SECRET"] = "localstack-test-secret-0123456789abcdef"
os.environ.setdefault("AWS_ENDPOINT_URL", ENDPOINT)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class LocalStackHandlerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        deadline = time.time() + 180
        while time.time() < deadline:
            try:
                with urlopen(ENDPOINT + "/_localstack/health", timeout=2) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError("LocalStack did not become ready")

        cls.dynamodb = boto3.resource("dynamodb", endpoint_url=ENDPOINT, region_name="ap-northeast-1")
        cls.s3 = boto3.client("s3", endpoint_url=ENDPOINT, region_name="ap-northeast-1")
        # ローカルで繰り返し実行しても、既存のテスト用リソースを再利用する。
        if TABLE_NAME not in cls.dynamodb.meta.client.list_tables().get("TableNames", []):
            cls.dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}],
                AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}, {"AttributeName": "sk", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
        cls.dynamodb.Table(TABLE_NAME).wait_until_exists()
        try:
            cls.s3.head_bucket(Bucket=BUCKET_NAME)
        except ClientError:
            cls.s3.create_bucket(Bucket=BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"})

        import handler

        cls.handler = handler

    def test_verify_pin_and_authenticated_usage(self):
        self.handler.save({
            "pk": "PIN#1234",
            "sk": "PIN",
            "label": "LocalStack test",
            "uses": 0,
            "max_uses": 1,
            "expires_at": int(time.time()) + 300,
        })
        verify_event = {"body": json.dumps({"type": "verify_pin", "pin": "1234"})}
        verified = self.handler.lambda_handler(verify_event, None)
        self.assertEqual(verified["statusCode"], 200)
        token = json.loads(verified["body"])["token"]

        usage_event = {"body": json.dumps({"type": "get_usage", "token": token})}
        usage = self.handler.lambda_handler(usage_event, None)
        self.assertEqual(usage["statusCode"], 200)
        self.assertEqual(json.loads(usage["body"])["limit"], 10)


if __name__ == "__main__":
    unittest.main()
