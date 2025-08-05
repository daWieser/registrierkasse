<p align="center">
  <img src="./pos_registrierkasse/static/description/icon.png" alt="RKSV-compliant Open Source Cash Register Logo" height="250px">
</p>

# RKSV-compliant Open Source Cash Register

[![Odoo Version 17](https://img.shields.io/badge/Odoo-v17-blue.svg)](https://www.odoo.com/page/download) [![Odoo Version 18](https://img.shields.io/badge/Odoo-v18-blue.svg)](https://www.odoo.com/page/download)

Open source Odoo addon, to enable RKSV compliance in Odoo POS.

---

## Features

*   **RKSV Compliance:** Enables your Odoo Point of Sale (POS) to comply with Austrian Registrierkassenpflicht (RKSV) regulations.
*   **Automated Startbeleg Creation:** Automatically generates the initial "Startbeleg" (starting receipt) when a POS is configured for RKSV.
*   **Configurable A-Trust API Environment:** Allows selection between Test and Production environments for A-Trust API communication directly from POS settings.
*   **Automated Nullbeleg Generation:** Automatically creates monthly Nullbeleg receipts as required by law.
*   **Stornobeleg Creation:** Supports the creation of Stornobelege (cancellation receipts) for RKSV compliance.
*   **Datenerfassungsprotokoll Export:** Enables the export of the "Datenerfassungsprotokoll" (data capture protocol) for quarterly backups.

---

## Table of Contents

- [How to Use](#how-to-use)
  - [Enable RKSV Compliance on your POS](#enable-rksv-compliance-on-your-pos)
  - [RKSV Configuration Options](#rksv-configuration-options)
- [Nullbeleg](#nullbeleg)
- [Datenerfassungsprotokoll](#datenerfassungsprotokoll)

---

## How to Use

### Enable RKSV Compliance on your POS

To comply with Austrian law, a signature certificate from A-Trust is required. This certificate can be obtained from [office@vorstieg.eu](mailto:office@vorstieg.eu).

Upon saving the POS with RKSV enabled, a Startbeleg is automatically created and can be registered using the "BMF Belegchek" app.

![screenshot RKSV settings](./pos_registrierkasse/static/description/rksv_1.png)

### RKSV Configuration Options

*   **A-Trust User Name:** The username for authenticating with the A-Trust API.
*   **A-Trust Password:** The password for authenticating with the A-Trust API.
*   **Umsatzzähler AES (AES Key):** An automatically generated AES key used for encrypting the revenue counter. This key must be registered with Finanzonline.
*   **Umsatzzähler AES Prüfsumme (AES Key Checksum):** A checksum for the generated AES key, used for verification.
*   **A-Trust Environment:** Select between Test or Production environments for A-Trust API communication.
*   **Time for Nullbeleg:** Specify the time of day for the monthly Nullbeleg cron job, which runs on the last day of each month.

---

## Nullbeleg

When the RKSV option is enabled on any POS, a Nullbelegprodukt is automatically created. This product is essential for the Startbeleg, as well as for the monthly and yearly end receipts.

In situations where an officer of the financial police inspects the POS, it is necessary to create an empty receipt using this product.

![screenshot with Nullbeleg](./pos_registrierkasse/static/description/rksv_2.png)

An automated task (cron job) is included in this module to create the monthly Nullbeleg. It is highly recommended to configure this job to run during non-business hours to avoid interfering with active POS sessions.

---

## Datenerfassungsprotokoll

According to Austrian law, all receipts must be exported and backed up once per quarter. This can be done by exporting the Datenerfassungsprotokoll for each POS.

![screenshot with Datenerfassungsprotokoll](./pos_registrierkasse/static/description/rksv_3.png)
