# app/schemas/iso_schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

# Pega aquí el ISO8583Transaction completo que ya generamos
# ==========================================================
#   MODELO DE ENTRADA ISO 8583
# ==========================================================

class ISO8583Transaction(BaseModel):
    """
    Modelo Pydantic para recibir datos de transacción en formato ISO 8583.
    Los campos siguen la convención i_0002_pan, i_0003_processing_code, etc.
    """

    # MTI + Bitmap
    mti: str = Field(..., max_length=4, example="0100")
    bitmap: Optional[str] = Field(
        None,
        max_length=32,
        description="Bitmap primario (16 hex) o primario+secundario (32 hex)",
        example="723820300180C000"
    )

    # ------------------------------------------------------------------
    # DE 2–4 (obligatorios para tu lógica actual)
    # ------------------------------------------------------------------
    i_0002_pan: str = Field(
        ...,
        max_length=19,
        description="Primary Account Number (PAN)",
        example="4000123456789010"
    )
    i_0003_processing_code: str = Field(
        ...,
        max_length=6,
        description="Processing Code",
        example="000000"
    )
    i_0004_amount_transaction: str = Field(
        ...,
        max_length=12,
        description="Amount, transaction (12 n, sin punto, ej: 000000001500)",
        example="000000001500"
    )

    # Opcionales 5–6
    i_0005_amount_settlement: Optional[str] = Field(
        None, max_length=12, description="Amount, settlement"
    )
    i_0006_amount_cardholder_billing: Optional[str] = Field(
        None, max_length=12, description="Amount, cardholder billing"
    )

    # ------------------------------------------------------------------
    # DE 7–13 (7,11,12,13 los usas; se marcan obligatorios)
    # ------------------------------------------------------------------
    i_0007_transmission_datetime: str = Field(
        ...,
        max_length=10,
        description="Transmission date & time (MMDDhhmmss)",
        example="1124123045"
    )
    i_0008_amount_cardholder_billing_fee: Optional[str] = Field(
        None, max_length=8, description="Amount, cardholder billing fee"
    )
    i_0009_conversion_rate_settlement: Optional[str] = Field(
        None, max_length=8, description="Conversion rate, settlement"
    )
    i_0010_conversion_rate_cardholder_billing: Optional[str] = Field(
        None, max_length=8, description="Conversion rate, cardholder billing"
    )
    i_0011_stan: str = Field(
        ...,
        max_length=6,
        description="System Trace Audit Number (STAN)",
        example="123456"
    )
    i_0012_time_local: str = Field(
        ...,
        max_length=6,
        description="Local transaction time (hhmmss)",
        example="153045"
    )
    i_0013_date_local: str = Field(
        ...,
        max_length=4,
        description="Local transaction date (MMDD)",
        example="1124"
    )

    # ------------------------------------------------------------------
    # DE 14–21
    # ------------------------------------------------------------------
    i_0014_expiration_date: Optional[str] = Field(
        None, max_length=4, description="Expiration date (YYMM)"
    )
    i_0015_settlement_date: Optional[str] = Field(
        None, max_length=4, description="Settlement date (MMDD)"
    )
    i_0016_currency_conversion_date: Optional[str] = Field(
        None, max_length=4, description="Currency conversion date"
    )
    i_0017_capture_date: Optional[str] = Field(
        None, max_length=4, description="Capture date"
    )
    i_0018_merchant_type_mcc: str = Field(
        None,
        max_length=4,
        description="Merchant type / MCC",
        example="5999"
    )
    i_0019_acq_country_code: Optional[str] = Field(
        None, max_length=3, description="Acquiring institution (country code)"
    )
    i_0020_pan_extended_country_code: Optional[str] = Field(
        None, max_length=3, description="PAN extended (country code)"
    )
    i_0021_fwd_country_code: Optional[str] = Field(
        None, max_length=3, description="Forwarding institution (country code)"
    )

    # ------------------------------------------------------------------
    # DE 22–27 (22,24,25 los usas; los marco obligatorios)
    # ------------------------------------------------------------------
    i_0022_pos_entry_mode: str = Field(
        None,
        max_length=3,
        description="Point of service entry mode",
        example="901"
    )
    i_0023_pan_sequence_number: Optional[str] = Field(
        None, max_length=3, description="Application PAN sequence number"
    )
    i_0024_function_code_nii: str = Field(
        None,
        max_length=3,
        description="Function code / Network international identifier (NII)",
        example="200"
    )
    i_0025_pos_condition_code: str = Field(
        None,
        max_length=2,
        description="Point of service condition code",
        example="00"
    )
    i_0026_pos_capture_code: Optional[str] = Field(
        None, max_length=2, description="Point of service capture code"
    )
    i_0027_auth_id_response_length: Optional[str] = Field(
        None, max_length=1, description="Authorizing identification response length"
    )

    # ------------------------------------------------------------------
    # DE 28–31 (x+n 8 → lo dejamos como string)
    # ------------------------------------------------------------------
    i_0028_amount_tx_fee: Optional[str] = Field(
        None, max_length=9, description="Amount, transaction fee"
    )
    i_0029_amount_settlement_fee: Optional[str] = Field(
        None, max_length=9, description="Amount, settlement fee"
    )
    i_0030_amount_tx_processing_fee: Optional[str] = Field(
        None, max_length=9, description="Amount, transaction processing fee"
    )
    i_0031_amount_settlement_processing_fee: Optional[str] = Field(
        None, max_length=9, description="Amount, settlement processing fee"
    )

    # ------------------------------------------------------------------
    # DE 32–36 (32 lo usas, obligatorio)
    # ------------------------------------------------------------------
    i_0032_acquiring_inst_id: str = Field(
        None,
        max_length=11,
        description="Acquiring institution identification code",
        example="12345678901"
    )
    i_0033_forwarding_inst_id: Optional[str] = Field(
        None, max_length=11, description="Forwarding institution identification code"
    )
    i_0034_pan_extended: Optional[str] = Field(
        None, max_length=28, description="Primary account number, extended"
    )
    i_0035_track_2_data: Optional[str] = Field(
        None, max_length=37, description="Track 2 data (datos sensibles, sólo lab)"
    )
    i_0036_track_3_data: Optional[str] = Field(
        None, max_length=104, description="Track 3 data (datos sensibles, sólo lab)"
    )

    # ------------------------------------------------------------------
    # DE 37–42 (41 y 42 los usas, obligatorios)
    # ------------------------------------------------------------------
    i_0037_retrieval_reference_number: Optional[str] = Field(
        None, max_length=12, description="Retrieval reference number"
    )
    i_0038_auth_id_response: Optional[str] = Field(
        None, max_length=6, description="Authorization identification response"
    )
    i_0039_response_code: Optional[str] = Field(
        None, max_length=2, description="Response code"
    )
    i_0040_service_restriction_code: Optional[str] = Field(
        None, max_length=3, description="Service restriction code"
    )
    i_0041_card_acceptor_tid: str = Field(
        ...,
        max_length=8,
        description="Card acceptor terminal identification",
        example="ATM00001"
    )
    i_0042_card_acceptor_mid: str = Field(
        None,
        max_length=15,
        description="Card acceptor identification code (MID)",
        example="INDBANK00012345"
    )

    # ------------------------------------------------------------------
    # DE 43–49 (43,49 los usas, obligatorios)
    # ------------------------------------------------------------------
    i_0043_card_acceptor_name_loc: str = Field(
        None,
        max_length=40,
        description=(
            "Card acceptor name/location. 1–25: nombre, 26–38 ciudad, 39–40 país"
        ),
        example="HP PETROL BUNK     BANGALORE   KA IN"
    )
    i_0044_additional_response_data: Optional[str] = Field(
        None, max_length=25, description="Additional response data"
    )
    i_0045_track_1_data: Optional[str] = Field(
        None, max_length=76, description="Track 1 data (datos sensibles, sólo lab)"
    )
    i_0046_additional_data_iso: Optional[str] = Field(
        None, description="Additional data (ISO)"
    )
    i_0047_additional_data_national: Optional[str] = Field(
        None, description="Additional data (national)"
    )
    i_0048_additional_data_private: Optional[str] = Field(
        None, description="Additional data (private)"
    )
    i_0049_currency_code_tx: str = Field(
        ...,
        max_length=3,
        description="Currency code, transaction (ISO 4217 numérico)",
        example="840"
    )

    # ------------------------------------------------------------------
    # DE 50–55
    # ------------------------------------------------------------------
    i_0050_currency_code_settlement: Optional[str] = Field(
        None, max_length=3, description="Currency code, settlement"
    )
    i_0051_currency_code_cardholder_billing: Optional[str] = Field(
        None, max_length=3, description="Currency code, cardholder billing"
    )
    i_0052_pin_data: Optional[str] = Field(
        None,
        max_length=64,
        description="PIN data block (sumamente sensible, sólo lab)"
    )
    i_0053_security_control_info: Optional[str] = Field(
        None, max_length=16, description="Security related control information"
    )
    i_0054_additional_amounts: Optional[str] = Field(
        None, description="Additional amounts"
    )
    i_0055_icc_data_emv: Optional[str] = Field(
        None,
        description="ICC data – EMV having multiple tags"
    )

    # ------------------------------------------------------------------
    # DE 56–63 (reservados)
    # ------------------------------------------------------------------
    i_0056_reserved_iso: Optional[str] = Field(
        None, description="Reserved (ISO)"
    )
    i_0057_reserved_national: Optional[str] = Field(
        None, description="Reserved (national)"
    )
    i_0058_reserved: Optional[str] = Field(
        None, description="Reserved"
    )
    i_0059_reserved: Optional[str] = Field(
        None, description="Reserved"
    )
    i_0060_reserved_national: Optional[str] = Field(
        None, description="Reserved (national)"
    )
    i_0061_reserved_private: Optional[str] = Field(
        None, description="Reserved (private)"
    )
    i_0062_reserved_private_2: Optional[str] = Field(
        None, description="Reserved (private, 2)"
    )
    i_0063_reserved_private_3: Optional[str] = Field(
        None, description="Reserved (private, 3)"
    )

    # ------------------------------------------------------------------
    # DE 64
    # ------------------------------------------------------------------
    i_0064_message_authentication_code: Optional[str] = Field(
        None,
        max_length=64,
        description="Message authentication code (MAC)"
    )

    # ------------------------------------------------------------------
    # DE 65–72
    # ------------------------------------------------------------------
    i_0065_extended_bitmap_indicator: Optional[str] = Field(
        None, max_length=1, description="Extended bitmap indicator"
    )
    i_0066_settlement_code: Optional[str] = Field(
        None, max_length=1, description="Settlement code"
    )
    i_0067_extended_payment_code: Optional[str] = Field(
        None, max_length=2, description="Extended payment code"
    )
    i_0068_receiving_inst_country_code: Optional[str] = Field(
        None, max_length=3, description="Receiving institution country code"
    )
    i_0069_settlement_inst_country_code: Optional[str] = Field(
        None, max_length=3, description="Settlement institution country code"
    )
    i_0070_network_management_info_code: Optional[str] = Field(
        None, max_length=3, description="Network management information code"
    )
    i_0071_message_number: Optional[str] = Field(
        None, max_length=4, description="Message number"
    )
    i_0072_last_message_number: Optional[str] = Field(
        None, max_length=4, description="Last message number"
    )

    # ------------------------------------------------------------------
    # DE 73–79
    # ------------------------------------------------------------------
    i_0073_action_date: Optional[str] = Field(
        None, max_length=6, description="Action date (YYMMDD)"
    )
    i_0074_number_credits: Optional[str] = Field(
        None, max_length=10, description="Number of credits"
    )
    i_0075_credits_reversal_number: Optional[str] = Field(
        None, max_length=10, description="Credits, reversal number"
    )
    i_0076_number_debits: Optional[str] = Field(
        None, max_length=10, description="Number of debits"
    )
    i_0077_debits_reversal_number: Optional[str] = Field(
        None, max_length=10, description="Debits, reversal number"
    )
    i_0078_transfer_number: Optional[str] = Field(
        None, max_length=10, description="Transfer number"
    )
    i_0079_transfer_reversal_number: Optional[str] = Field(
        None, max_length=10, description="Transfer, reversal number"
    )

    # ------------------------------------------------------------------
    # DE 80–89
    # ------------------------------------------------------------------
    i_0080_number_inquiries: Optional[str] = Field(
        None, max_length=10, description="Number of inquiries"
    )
    i_0081_number_authorizations: Optional[str] = Field(
        None, max_length=10, description="Number of authorizations"
    )
    i_0082_credits_processing_fee_amount: Optional[str] = Field(
        None, max_length=12, description="Credits, processing fee amount"
    )
    i_0083_credits_transaction_fee_amount: Optional[str] = Field(
        None, max_length=12, description="Credits, transaction fee amount"
    )
    i_0084_debits_processing_fee_amount: Optional[str] = Field(
        None, max_length=12, description="Debits, processing fee amount"
    )
    i_0085_debits_transaction_fee_amount: Optional[str] = Field(
        None, max_length=12, description="Debits, transaction fee amount"
    )
    i_0086_total_amount_credits: Optional[str] = Field(
        None, max_length=16, description="Total amount of credits"
    )
    i_0087_credits_reversal_amount: Optional[str] = Field(
        None, max_length=16, description="Credits, reversal amount"
    )
    i_0088_total_amount_debits: Optional[str] = Field(
        None, max_length=16, description="Total amount of debits"
    )
    i_0089_debits_reversal_amount: Optional[str] = Field(
        None, max_length=16, description="Debits, reversal amount"
    )

    # ------------------------------------------------------------------
    # DE 90–96
    # ------------------------------------------------------------------
    i_0090_original_data_elements: Optional[str] = Field(
        None, description="Original data elements"
    )
    i_0091_file_update_code: Optional[str] = Field(
        None, max_length=1, description="File update code"
    )
    i_0092_file_security_code: Optional[str] = Field(
        None, max_length=2, description="File security code"
    )
    i_0093_response_indicator: Optional[str] = Field(
        None, max_length=5, description="Response indicator"
    )
    i_0094_service_indicator: Optional[str] = Field(
        None, max_length=7, description="Service indicator"
    )
    i_0095_replacement_amounts: Optional[str] = Field(
        None, description="Replacement amounts"
    )
    i_0096_message_security_code: Optional[str] = Field(
        None, max_length=64, description="Message security code"
    )

    # ------------------------------------------------------------------
    # DE 97–104
    # ------------------------------------------------------------------
    i_0097_net_settlement_amount: Optional[str] = Field(
        None, max_length=16, description="Net settlement amount"
    )
    i_0098_payee: Optional[str] = Field(
        None, max_length=25, description="Payee"
    )
    i_0099_settlement_inst_id_code: Optional[str] = Field(
        None, max_length=11, description="Settlement institution identification code"
    )
    i_0100_receiving_inst_id_code: Optional[str] = Field(
        None, max_length=11, description="Receiving institution identification code"
    )
    i_0101_file_name: Optional[str] = Field(
        None, max_length=17, description="File name"
    )
    i_0102_account_id_1: Optional[str] = Field(
        None, max_length=28, description="Account identification 1"
    )
    i_0103_account_id_2: Optional[str] = Field(
        None, max_length=28, description="Account identification 2"
    )
    i_0104_tx_description: Optional[str] = Field(
        None, max_length=100, description="Transaction description"
    )


class TransaccionResponse(BaseModel):
    fraude_detectado: bool
    probabilidad_fraude: float
    nivel_riesgo: str
    factores_riesgo: List[str]
    mensaje: str
    recomendacion: str
    cliente_hash: str
    score_anomalia: float
    timestamp: str
    datos_analizados: Dict
    conversion_moneda: Optional[Dict] = None
    transaction_db_id: Optional[int] = None
