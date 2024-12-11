import unittest

from .a_trust_library import OrderData
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from hashlib import sha256
from base64 import b64decode, b64encode
from unittest.mock import MagicMock, patch


def chain_hash(config, order):
    data_to_sign = OrderData(config.name,
                             order.registrierkasse_receipt_number,
                             order.date_order,
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
    encoded_payload = b64encode(payload.encode('utf-8')).decode("utf-8")

    # the padding characters need to be removed with the rstrip function, since JWS requires base64-URĹ encoding, instead of normal base64
    encoded_payload = encoded_payload.rstrip("=")
    return "eyJhbGciOiJFUzI1NiJ9." + encoded_payload + "." + signature


def hash_signature(signature):
    hash_value = sha256(signature.encode('utf-8')).digest()
    relevant_bytes = hash_value[:8]
    return b64encode(relevant_bytes).decode("utf-8")


def _init_vector(pos_name, bill_number):
    return modes.CTR(sha256((pos_name + str(bill_number)).encode('utf-8')).digest()[:16])


def encrypt_revenue_counter(revenue_counter, aes_key, pos_name, sequence_number):
    cipher = Cipher(algorithms.AES(b64decode(aes_key)), _init_vector(pos_name, sequence_number))
    encryptor = cipher.encryptor()

    # According to the detailed Specification, the length of a block needs to be 16 Bytes.
    # However for the qr code it needs to be 5 bytes. So the first 5 bytes of the revenue counter are filled
    data = int(revenue_counter * 100).to_bytes(5, byteorder='big') + b'\x00' * 11

    encrypted = encryptor.update(data) + encryptor.finalize()[:5]
    return b64encode(encrypted).decode('utf-8')


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
        order.registrierkasse_receipt_number = "366587"
        order.date_order = "2015-12-17T11:23:44"
        order.sum_vat_normal = "34,77"
        order.sum_vat_discounted_1 = "59,64"
        order.sum_vat_discounted_2 = "38,13"
        order.sum_vat_null = "0,00"
        order.sum_vat_special = "0,00"
        order.encrypted_revenue = "8MG8C1Kr7HA="
        order.prev_order_signature = "xTfZvkBSTr4="
        order.order_signature = self.BELEG_SIGNATURE

        self.assertEqual(chain_hash(config, order), "5HjRCx+XIz4=", "Chain Hash is calculated correctly")


if __name__ == "__main__":
    unittest.main()
