"""Generate a VAPID keypair for Web Push and print .env-ready values."""

from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand
from py_vapid import Vapid
from py_vapid.utils import b64urlencode


class Command(BaseCommand):
    help = (
        "Generate a VAPID keypair for Web Push. Paste the printed "
        "VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY lines into .env to enable push."
    )

    def handle(self, *args, **options):
        vapid = Vapid()
        vapid.generate_keys()

        # Application server key: the raw uncompressed EC point, base64url
        # encoded. This is exactly what the browser's
        # PushManager.subscribe({applicationServerKey}) expects.
        public_bytes = vapid.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        # Raw 32-byte private scalar, base64url encoded. py_vapid.Vapid.from_string
        # recognizes this format (falls back to from_raw() for 32-byte values).
        private_value = vapid.private_key.private_numbers().private_value
        private_bytes = private_value.to_bytes(32, "big")

        self.stdout.write(f"VAPID_PUBLIC_KEY={b64urlencode(public_bytes)}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={b64urlencode(private_bytes)}")
