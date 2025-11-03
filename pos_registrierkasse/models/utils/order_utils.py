import unittest
from base64 import b64encode, urlsafe_b64encode
from hashlib import sha256
from unittest.mock import MagicMock
from datetime import datetime
import pytz
from .a_trust_library import OrderData


def chain_hash(config, order):
    data_to_sign = OrderData(config.name,
                             order.registrierkasse_receipt_number,
                             format_order_date_datetime(order.date_order),
                             order.sum_vat_normal,
                             order.sum_vat_discounted_1,
                             order.sum_vat_discounted_2,
                             order.sum_vat_null,
                             order.sum_vat_special,
                             order.encrypted_revenue,
                             config.certificate_serial_number,
                             order.prev_order_signature)
    return hash_signature(jws_signature_compact(data_to_sign.parse(), order.order_signature))


def jws_signature_compact(payload, signature):
    encoded_payload = urlsafe_b64encode(payload.encode('utf-8')).decode("utf-8")

    # the padding characters need to be removed with the rstrip function, since JWS requires base64-URĹ encoding, instead of normal base64
    encoded_payload = encoded_payload.rstrip("=")
    return "eyJhbGciOiJFUzI1NiJ9." + encoded_payload + "." + signature


def hash_signature(signature):
    hash_value = sha256(signature.encode('utf-8')).digest()
    relevant_bytes = hash_value[:8]
    return b64encode(relevant_bytes).decode("utf-8")

def base64url_to_base64(base64url_str: str) -> str:
    """Converts a Base64URL encoded string to a Base64 encoded string."""
    base64_str = base64url_str.replace('-', '+').replace('_', '/')
    padding = '=' * (-len(base64_str) % 4)
    return base64_str + padding

def format_order_date(date):
    utc_time = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    utc_time = utc_time.replace(tzinfo=pytz.UTC)

    local_time = utc_time.astimezone(pytz.timezone("Europe/Vienna"))
    return datetime.strftime(local_time, "%Y-%m-%dT%H:%M:%S")

def format_order_date_datetime(time):
    local_time = time.astimezone(pytz.timezone("Europe/Vienna"))
    return datetime.strftime(local_time, "%Y-%m-%dT%H:%M:%S")


class PosUtilsTest(unittest.TestCase):
    BELEG_CODE = "_R1-AT0_DEMO-CASH-BOX524_366587_2015-12-17T11:23:44_34,77_59,64_38,13_0,00_0,00_8MG8C1Kr7HA=_20f2ed172daa09e5_xTfZvkBSTr4="
    BELEG_SIGNATURE = "GeWps9kci-fUqKLymS1pHlIbv0L8Oek-v6TDmZj9Ffucb8yvSijqZ8LcBalV9lADMXQ8U3itViKkd_i1Ba22BA"

    def test_jws_compact(self):
        self.assertEqual(jws_signature_compact(
            self.BELEG_CODE, self.BELEG_SIGNATURE),
            "eyJhbGciOiJFUzI1NiJ9.X1IxLUFUMF9ERU1PLUNBU0gtQk9YNTI0XzM2NjU4N18yMDE1LTEyLTE3VDExOjIzOjQ0XzM0LDc3XzU5LDY0XzM4LDEzXzAsMDBfMCwwMF84TUc4QzFLcjdIQT1fMjBmMmVkMTcyZGFhMDllNV94VGZadmtCU1RyND0.GeWps9kci-fUqKLymS1pHlIbv0L8Oek-v6TDmZj9Ffucb8yvSijqZ8LcBalV9lADMXQ8U3itViKkd_i1Ba22BA",
            "Compact JWS signature")

    def test_with_hyphen_and_underscore(self):
        base64url_hyphen = "3q2-7w"
        expected_base64_hyphen = "3q2+7w=="
        self.assertEqual(base64url_to_base64(base64url_hyphen), expected_base64_hyphen)

        base64url_underscore = "AQID_w"
        expected_base64_underscore = "AQID/w=="
        self.assertEqual(base64url_to_base64(base64url_underscore), expected_base64_underscore)

    def test_hash_signature_startbeleg(self):
        self.assertEqual(hash_signature("A12347"), "OeSKQjO4zKI=", "Hash Startbeleg")

    def test_hash_signature_beleg(self):
        self.assertEqual(hash_signature(jws_signature_compact(
            self.BELEG_CODE, self.BELEG_SIGNATURE)),
            "5HjRCx+XIz4=",
            "Hash normaler Beleg")

    def test_chain_hash(self):
        OrderData.ALGO_KENNUNG = '_R1-AT0_'  # AT1 ist die Kennung von A-Trust
        config = MagicMock()

        config.name = "DEMO-CASH-BOX524"
        config.certificate_serial_number = "20f2ed172daa09e5"

        order = MagicMock()
        order.registrierkasse_receipt_number = "366587"
        order.date_order = datetime.strptime("2015-12-17T11:23:44","%Y-%m-%dT%H:%M:%S")
        order.sum_vat_normal = 34.77
        order.sum_vat_discounted_1 = 59.64
        order.sum_vat_discounted_2 = 38.13
        order.sum_vat_null = 0
        order.sum_vat_special = 0
        order.encrypted_revenue = "8MG8C1Kr7HA="
        order.prev_order_signature = "xTfZvkBSTr4="
        order.order_signature = self.BELEG_SIGNATURE

        self.assertEqual(chain_hash(config, order), "5HjRCx+XIz4=", "Chain Hash is calculated correctly")

    def test_format_order_date(self):
        self.assertEqual(format_order_date("2025-04-23 15:34:22"),"2025-04-23T17:34:22")

if __name__ == "__main__":
    unittest.main()
