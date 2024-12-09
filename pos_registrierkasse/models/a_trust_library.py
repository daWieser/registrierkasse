from dataclasses import dataclass

from requests import get, put, post, delete
import base64


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

    def parse(self):
        return (
            '_R1-AT75_' + #replace AT75 with the correct value for a-trust
            str(self.pos_name) + '_' +
            str(self.receipt_number) + '_' +
            str(self.receipt_date) + '_' +
            str(self.sum_vat_normal) + '_' +
            str(self.sum_vat_discounted_1) + '_' +
            str(self.sum_vat_discounted_2) + '_' +
            str(self.sum_vat_null) + '_' +
            str(self.sum_vat_special) + '_' +
            str(self.revenue_counter_encrypted) + '_' +
            str(self.certificate_serial_number) + '_' +
            str(self.prev_order_signature))


basePath = "https://hs-abnahme.a-trust.at/asignrkonline/v2"


def login(user):
    url = basePath + '/Session/' + user.username
    request_payload = {'password': user.password}

    response = put(url, json=request_payload)
    if response.status_code != 200:
        raise Exception("Couldn't login to " + url)
    response_payload = response.json()
    return SessionData(response_payload['sessionkey'], response_payload['sessionid'])


def logout(session):
    url = basePath + '/Session/' + session.sessionId

    response = delete(url)
    if response.status_code != 200:
        raise Exception("Couldn't logout from " + url)
    return response


def create_signature(session, orderData):
    url = basePath + '/Session/' + session.sessionId + '/Sign'
    payload = {
        "sessionkey": session.sessionKey,
        "to_be_signed": base64.encodebytes(bytes(orderData.parse(), 'utf-8')).decode('utf-8'),
    }

    response = post(url, json=payload)

    if response.status_code == 401:
        raise PermissionError("Please log in ")

    if response.status_code != 200:
        raise Exception("got the following error from signature: " + str(response.status_code))
    return response.json()['signature']

def get_serial_number(user):
    url = basePath + '/' + user.username + '/Certificates'
    response = get(url)

    if response.status_code == 401:
        raise PermissionError("Please log in ")

    if response.status_code != 200:
        raise Exception("got the following error from signature: " + str(response.status_code))
    return response.json()