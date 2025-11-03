import unittest
import base64
from dataclasses import dataclass
from abc import ABC, abstractmethod
from requests import get, put, post, delete


@dataclass()
class SessionData:
    sessionKey: str
    sessionId: str


@dataclass()
class LoginData:
    username: str
    password: str


@dataclass()
class OrderData:
    pos_name: str
    receipt_number: str
    receipt_date: str
    sum_vat_normal: float
    sum_vat_discounted_1: float
    sum_vat_discounted_2: float
    sum_vat_null: float
    sum_vat_special: float
    revenue_counter_encrypted: str
    certificate_serial_number: str
    prev_order_signature: str
    ALGO_KENNUNG = '_R1-AT1_'  # AT1 ist die Kennung von A-Trust

    def parse(self):
        return (
                OrderData.ALGO_KENNUNG +
                str(self.pos_name) + '_' +
                str(self.receipt_number) + '_' +
                str(self.receipt_date) + '_' +
                self._format_number(self.sum_vat_normal) + '_' +
                self._format_number(self.sum_vat_discounted_1) + "_" +
                self._format_number(self.sum_vat_discounted_2) + "_" +
                self._format_number(self.sum_vat_null) + "_" +
                self._format_number(self.sum_vat_special) + "_" +
                str(self.revenue_counter_encrypted) + '_' +
                str(self.certificate_serial_number) + '_' +
                str(self.prev_order_signature))

    def _format_number(self, value):
        return "{:.2f}".format(value).replace(".", ",")


@dataclass()
class CertificateInformation:
    certificate_serial_number: str
    certificate_serial_number_binary: str
    signature_certificate: str
    certification_body: [str]


class ATrustProvider(ABC):
    @abstractmethod
    def login(self, user: LoginData) -> SessionData:
        pass

    @abstractmethod
    def logout(self, session: SessionData):
        pass

    @abstractmethod
    def create_signature(self, session: SessionData, machine_readable_code: str) -> str:
        pass

    @abstractmethod
    def get_certificate_information(self, username: str) -> CertificateInformation:
        pass


class ATrustProdProvider(ATrustProvider):
    base_path = "https://rksv.a-trust.at/asignrkonline/v2"

    def __init__(self, base_path):
        self.base_path = base_path

    def login(self, user):
        url = self.base_path + '/Session/' + user.username
        request_payload = {'password': user.password}

        response = put(url, json=request_payload)
        if response.status_code != 200:
            raise Exception("Couldn't login to " + url)
        response_payload = response.json()
        return SessionData(response_payload['sessionkey'], response_payload['sessionid'])

    def logout(self, session):
        url = self.base_path + '/Session/' + session.sessionId

        response = delete(url)
        if response.status_code != 200:
            raise Exception("Couldn't logout from " + url)
        return response

    def create_signature(self, session, machine_readable_code):
        jws_payload = base64.urlsafe_b64encode(bytes(machine_readable_code, 'utf-8')).decode('utf-8').rstrip("=")

        to_be_signed = "eyJhbGciOiJFUzI1NiJ9" + '.' + jws_payload
        to_be_signed = base64.b64encode(bytes(to_be_signed, 'utf-8')).decode('ascii')

        url = self.base_path + '/Session/' + session.sessionId + '/Sign'
        payload = {
            "sessionkey": session.sessionKey,
            "to_be_signed": to_be_signed,
        }

        response = post(url, json=payload)

        if response.status_code == 401:
            raise PermissionError("Please log in ")

        if response.status_code != 200:
            raise Exception("got the following error from signature: " + str(response.status_code))
        return response.json()['signature']

    def get_certificate_information(self, username):
        url = self.base_path + '/' + username + '/Certificates'
        response = get(url)

        if response.status_code == 401:
            raise PermissionError("Please log in ")

        if response.status_code != 200:
            raise Exception("got the following error from signature: " + str(response.status_code))
        certificate = response.json()['Signaturzertifikate'][0]
        return CertificateInformation(certificate['ZertifikatsseriennummerHex'],
                                      certificate['Zertifikatsseriennummer'],
                                      certificate['Signaturzertifikat'],
                                      certificate['Zertifizierungsstellen'])


class ATrustMockProvider(ATrustProvider):
    def login(self, user):
        return SessionData('mock_session_key', 'mock_session_id')

    def logout(self, session):
        return True

    def create_signature(self, session, machine_readable_code):
        return "mock_signature_string"

    def get_certificate_information(self, username):
        return CertificateInformation(
            certificate_serial_number='1234567890ABC',
            signature_certificate='mock_signature_certificate',
            certification_body=['mock_certification_body']
        )


def get_atrust_api(env):
    if env == 'test':
        return ATrustMockProvider()
    elif env == 'qa':
        return ATrustProdProvider("https://hs-abnahme.a-trust.at/asignrkonline/v2")
    return ATrustProdProvider("https://rksv.a-trust.at/asignrkonline/v2")


class PosUtilsTest(unittest.TestCase):
    def test_parse_order_data(self):
        expected = "_R1-AT1_DEMO-CASH-BOX524_366585AB_2015-12-17T11:23:43_5,00_0,00_9,00_13,30_0,00_VFJB_245abcde_OJ16FcqeA7s"

        orderData = OrderData("DEMO-CASH-BOX524", "366585AB", "2015-12-17T11:23:43", 5, 0, 9, 13.3, 0, "VFJB",
                              "245abcde", "OJ16FcqeA7s")
        self.assertEqual(expected, orderData.parse())


if __name__ == "__main__":
    unittest.main()
