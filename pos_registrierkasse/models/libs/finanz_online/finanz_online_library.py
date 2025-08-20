import os
import logging
from dataclasses import dataclass

from zeep import Client, Settings, __version__
from zeep.transports import Transport
from zeep.xsd import SkipValue
from zeep.exceptions import Fault
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)

base_path = os.path.dirname(os.path.abspath(__file__))
SESSION_WSDL = os.path.join(base_path, "sessionService.wsdl.xml")
REGKASSE_WSDL = os.path.join(base_path, "regKasseService.wsdl.xml")

@dataclass
class FinanzOnlineCredentials:
    tid: str
    benid: str
    pin: str
    herstellerid: str
    env: str

class FinanzOnlineClient:
    def __init__(self, credentials):
        """Initializes the client with necessary credentials."""
        self.credentials = credentials
        self.session_id = None
        self.settings = Settings(strict=False, xml_huge_tree=True)
        self.transport = Transport(timeout=10)
        self.session_client = Client(SESSION_WSDL, settings=self.settings, transport=self.transport)
        self.regkasse_client = Client(REGKASSE_WSDL, settings=self.settings, transport=self.transport)

    def __enter__(self):
        """Logs into FinanzOnline and returns the client instance."""
        try:
            response = self.session_client.service.login(
                tid=self.credentials.tid,
                benid=self.credentials.benid,
                pin=self.credentials.pin,
                herstellerid=self.credentials.herstellerid
            )
            if response.rc == 0:
                self.session_id = response.id
                return self
            else:
                raise ConnectionError(f"FinanzOnline login failed. RC: {response.rc}, Msg: {response.msg}")
        except Fault as e:
            raise ConnectionError(f"SOAP Fault during login: {e.message}")
        except Exception as e:
            raise ConnectionError(f"An unexpected error occurred during login: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Logs out from FinanzOnline."""
        if self.session_id:
            response = self.session_client.service.logout(
                tid=self.credentials.tid,
                benid=self.credentials.benid,
                id=self.session_id
            )
            if response.rc != 0:
                _logger.warning(f"Logout failed. RC: {response.rc}, Msg: {response.msg}")

    def register_se(self, customer_info, se_type, vda_id, serial_number, transmission_type='T'):
        rkdb_payload = {
            'paket_nr': 2,
            'ts_erstellung': datetime.now(timezone.utc).isoformat(),
            'registrierung_se': [{
                'satznr': 1,
                'kundeninfo': customer_info,
                'art_se': se_type,
                'vda_id': vda_id,
                'zertifikatsseriennummer': serial_number
            }]
        }

        response = self.regkasse_client.service.rkdb(
            tid=self.credentials.tid,
            benid=self.credentials.benid,
            id=self.session_id,
            art_uebermittlung=transmission_type,
            rkdb=rkdb_payload
        )

        result_message = response.result[0].rkdbMessage[0]
        # B10 means the SE has already been registered, which is fine for us
        if result_message.rc not in ('0', 0, 'B10'):
            raise Exception(f"Signatureinheit registration failed. RC: {result_message.rc}, Msg: {result_message.msg}")

    def register_registrierkasse(self, kassen_id, customer_info, user_key, transmission_type='T', note=''):
        rkdb_payload = {
            'paket_nr': 1,
            'ts_erstellung': datetime.now(timezone.utc).isoformat(),
            'registrierung_kasse': [{
                'satznr': 1,
                'kundeninfo': customer_info,
                'kassenidentifikationsnummer': kassen_id,
                'anmerkung': note,
                'benutzerschluessel': user_key
            }]
        }

        response = self.regkasse_client.service.rkdb(
            tid=self.credentials.tid, benid=self.credentials.benid, id=self.session_id,
            art_uebermittlung=transmission_type, rkdb=rkdb_payload
        )

        result_message = response.result[0].rkdbMessage[0]
        if result_message.rc not in ('0', 0):
            raise Exception(f"Registrierkasse registration failed. RC: {result_message.rc}, Msg: {result_message.msg}")

    def verify_receipt(self, customer_info, receipt_data, transmission_type='T'):
        rkdb_payload = {
            'paket_nr': 6,
            'ts_erstellung': datetime.now(timezone.utc).isoformat(),
            'belegpruefung': {
                'satznr': 1,
                'kundeninfo': customer_info,
                'beleg': receipt_data
            }
        }

        response = self.regkasse_client.service.rkdb(
            tid=self.credentials.tid, benid=self.credentials.benid, id=self.session_id,
            art_uebermittlung=transmission_type, rkdb=rkdb_payload
        )

        result_message = response.result[0].rkdbMessage[0]
        # If we are in Testing-Mode we do not care about the result of this, since it will always fail if A-Trust is also in Testing mode
        if result_message.rc not in ('0', 0) and transmission_type == 'P':
            raise Exception(f"Receipt verification failed. RC: {result_message.rc}, Msg: {result_message.msg}")
        return True
