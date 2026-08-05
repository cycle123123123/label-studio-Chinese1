import os
import sys

from minio import Minio
from minio.error import S3Error

# Prefer env vars to avoid leaking secrets in source code:
# MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SESSION_TOKEN
# MINIO_BUCKET, MINIO_SECURE, MINIO_PREFIX
ENDPOINT = os.getenv("MINIO_ENDPOINT", "s3.nacta.edu.cn").strip()
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "").strip()
SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "").strip()
SESSION_TOKEN = os.getenv("MINIO_SESSION_TOKEN", "").strip() or None
BUCKET = os.getenv("MINIO_BUCKET", "lable-studio").strip()
SECURE = os.getenv("MINIO_SECURE", "true").strip().lower() in {"1", "true", "yes", "y"}
PREFIX = os.getenv("MINIO_PREFIX", "").strip()


def mask(text: str) -> str:
    if not text:
        return "<empty>"
    if len(text) <= 6:
        return "*" * len(text)
    return text[:3] + "*" * (len(text) - 6) + text[-3:]


def fail(msg: str, exit_code: int = 1) -> None:
    print(msg)
    sys.exit(exit_code)


if not ENDPOINT:
    fail("MINIO_ENDPOINT is empty.")
if not ACCESS_KEY or ACCESS_KEY.upper() == "YOUR_ACCESS_KEY":
    fail("MINIO_ACCESS_KEY is missing or placeholder.")
if not SECRET_KEY or SECRET_KEY.upper() == "YOUR_SECRET_KEY":
    fail("MINIO_SECRET_KEY is missing or placeholder.")

print("MinIO connection settings:")
print(f"- endpoint: {ENDPOINT}")
print(f"- secure: {SECURE}")
print(f"- bucket: {BUCKET}")
print(f"- prefix: '{PREFIX}'")
print(f"- access_key: {mask(ACCESS_KEY)}")
print(f"- secret_key: {mask(SECRET_KEY)}")
print(f"- session_token: {'set' if SESSION_TOKEN else 'not set'}")
print("-" * 60)

client = Minio(
    ENDPOINT,
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    session_token=SESSION_TOKEN,
    secure=SECURE,
)

try:
    # 1) Validate credentials first.
    buckets = client.list_buckets()
    print(f"Auth OK. Visible buckets: {[b.name for b in buckets]}")

    # 2) Then validate bucket access.
    if not client.bucket_exists(BUCKET):
        fail(
            f"Bucket not found or no permission: {BUCKET}\n"
            "Tip: check spelling (e.g., label-studio vs lable-studio) and IAM policy."
        )

    print("-" * 60)
    print("One-level view:")
    has_item = False
    for obj in client.list_objects(BUCKET, prefix=PREFIX, recursive=False):
        has_item = True
        if obj.object_name.endswith("/"):
            print(f"[DIR ] {obj.object_name}")
        else:
            print(f"[FILE] {obj.object_name} ({obj.size} bytes)")
    if not has_item:
        print("(empty)")

except S3Error as e:
    print("MinIO error:", e)
    if getattr(e, "code", "") == "InvalidAccessKeyId":
        print("Diagnosis: Access Key does not exist on MinIO.")
        print("Check: user/key exists, key copied correctly, no extra spaces/newlines.")
        print("If using temporary credentials, set MINIO_SESSION_TOKEN as well.")
        print("Also verify endpoint/port with admin (example: host:9000).")
    elif getattr(e, "code", "") == "SignatureDoesNotMatch":
        print("Diagnosis: Secret key mismatch or request signing context mismatch.")
        print("Check secret key, protocol(HTTP/HTTPS), endpoint, and system time.")
