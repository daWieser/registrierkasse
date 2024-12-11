import unittest
from base64 import b64decode, b64encode
from hashlib import sha256

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def _init_vector(pos_name, bill_number):
    return modes.CTR(sha256(_init_vector_string(pos_name, bill_number).encode('utf-8')).digest()[:16])


def _init_vector_string(pos_name, bill_number):
    return pos_name + str(bill_number).zfill(5)


def encrypt_revenue_counter(revenue_counter, aes_key, pos_name, sequence_number):
    cipher = Cipher(algorithms.AES(b64decode(aes_key)), _init_vector(pos_name, sequence_number))
    encryptor = cipher.encryptor()

    # According to the detailed Specification, the length of a block needs to be 16 Bytes.
    # However for the qr code it needs to be 5 bytes. So the first 5 bytes of the revenue counter are filled
    data = int(revenue_counter * 100).to_bytes(5, byteorder='big', signed=True) + b'\x00' * 11

    encrypted = encryptor.update(data) + encryptor.finalize()[:5]
    return b64encode(encrypted).decode('utf-8')


class PosUtilsTest(unittest.TestCase):
    AES_KEY = "yrv/OHCvvATh6P64DOBpdAXc97ZhBP9FyB/NPmrfRI4="

    def test_init_vector_string(self):
        self.assertEquals(_init_vector_string('DEMO-CASH-BOX524', 1),
                          'DEMO-CASH-BOX52400001',
                          "Init vector string")

    def test_revenue_counter(self):
        self.assertEqual(encrypt_revenue_counter('0',
                                                 self.AES_KEY,
                                                 "DEMO-CASH-BOX",
                                                 1),
                         'TJUK/sNj38aLxlSb69mekQ==',
                         "Revenue counter 0")

    def test_decrypt_revenue_counter_zero(self):
        encrypted = b64decode(encrypt_revenue_counter(0,
                                                      self.AES_KEY,
                                                      "DEMO-CASH-BOX",
                                                      1))
        decrypted = self._decrypt(self.AES_KEY, encrypted, "DEMO-CASH-BOX",
                                  1)
        int_value = int.from_bytes(decrypted, byteorder='big', signed=True)
        self.assertEqual(int_value, 0)

    def test_decrypt_revenue_counter_negatuve(self):
        encrypted = b64decode(encrypt_revenue_counter(-10,
                                                      self.AES_KEY,
                                                      "DEMO-CASH-BOX",
                                                      1))
        decrypted = self._decrypt(self.AES_KEY, encrypted, "DEMO-CASH-BOX",
                                  1)
        int_value = int.from_bytes(decrypted, byteorder='big', signed=True)
        self.assertEqual(int_value, -1000)

    def test_decrypt_revenue_counter_positive(self):
        encrypted = b64decode(encrypt_revenue_counter(22,
                                                      self.AES_KEY,
                                                      "DEMO-CASH-BOX",
                                                      1))
        decrypted = self._decrypt(self.AES_KEY, encrypted, "DEMO-CASH-BOX",
                                  1)
        int_value = int.from_bytes(decrypted, byteorder='big', signed=True)
        self.assertEqual(int_value, 2200)

    def _decrypt(self, key, encrypted, pos_name, sequence_number):
        cipher = Cipher(algorithms.AES(b64decode(key)), _init_vector(pos_name, sequence_number))
        encryptor = cipher.decryptor()
        return (encryptor.update(encrypted) + encryptor.finalize())[:5]


if __name__ == "__main__":
    unittest.main()
