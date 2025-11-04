import unittest
from base64 import b64encode, urlsafe_b64encode
from hashlib import sha256
from unittest.mock import MagicMock
from datetime import datetime
import pytz

def chain_hash(order):
    return hash_signature(jws_signature_compact(order.machine_readable_code, order.order_signature))


def jws_signature_compact(payload, signature):
    encoded_payload = urlsafe_b64encode(payload.encode('utf-8')).decode("utf-8")

    # the padding characters need to be removed with the rstrip function, since JWS requires base64-URĹ encoding, instead of normal base64
    encoded_payload = encoded_payload.rstrip("=")
    return "eyJhbGciOiJFUzI1NiJ9." + encoded_payload + "." + signature


def hash_signature(signature):
    hash_value = sha256(signature.encode('utf-8')).digest()
    relevant_bytes = hash_value[:8]
    return b64encode(relevant_bytes).decode("utf-8")


def format_order_date(date):
    utc_time = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    utc_time = utc_time.replace(tzinfo=pytz.UTC)

    local_time = utc_time.astimezone(pytz.timezone("Europe/Vienna"))
    return datetime.strftime(local_time, "%Y-%m-%dT%H:%M:%S")


class PosUtilsTest(unittest.TestCase):
    BELEG_CODE = "_R1-AT0_DEMO-CASH-BOX524_366587_2015-12-17T11:23:44_34,77_59,64_38,13_0,00_0,00_8MG8C1Kr7HA=_20f2ed172daa09e5_xTfZvkBSTr4="
    BELEG_SIGNATURE = "GeWps9kci-fUqKLymS1pHlIbv0L8Oek-v6TDmZj9Ffucb8yvSijqZ8LcBalV9lADMXQ8U3itViKkd_i1Ba22BA"

    def test_jws_compact(self):
        self.assertEqual(jws_signature_compact(
            self.BELEG_CODE, self.BELEG_SIGNATURE),
            "eyJhbGciOiJFUzI1NiJ9.X1IxLUFUMF9ERU1PLUNBU0gtQk9YNTI0XzM2NjU4N18yMDE1LTEyLTE3VDExOjIzOjQ0XzM0LDc3XzU5LDY0XzM4LDEzXzAsMDBfMCwwMF84TUc4QzFLcjdIQT1fMjBmMmVkMTcyZGFhMDllNV94VGZadmtCU1RyND0.GeWps9kci-fUqKLymS1pHlIbv0L8Oek-v6TDmZj9Ffucb8yvSijqZ8LcBalV9lADMXQ8U3itViKkd_i1Ba22BA",
            "Compact JWS signature")

    def test_hash_signature_startbeleg(self):
        self.assertEqual(hash_signature("A12347"), "OeSKQjO4zKI=", "Hash Startbeleg")

    def test_hash_signature_beleg(self):
        self.assertEqual(hash_signature(jws_signature_compact(
            self.BELEG_CODE, self.BELEG_SIGNATURE)),
            "5HjRCx+XIz4=",
            "Hash normaler Beleg")

    def test_chain_hash(self):
        config = MagicMock()

        config.name = "DEMO-CASH-BOX524"
        config.certificate_serial_number = "20f2ed172daa09e5"

        order = MagicMock()
        order.machine_readable_code= self.BELEG_CODE
        order.order_signature = self.BELEG_SIGNATURE

        self.assertEqual(chain_hash(order), "5HjRCx+XIz4=", "Chain Hash is calculated correctly")

    def test_format_order_date(self):
        self.assertEqual(format_order_date("2025-04-23 15:34:22"), "2025-04-23T17:34:22")


if __name__ == "__main__":
    unittest.main()
