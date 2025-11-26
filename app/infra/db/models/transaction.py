# app/infra/db/models/transaction.py
from sqlalchemy import (
    Column, String, Integer, DateTime, Float, Boolean,
    ForeignKey, DECIMAL, UniqueConstraint, func
)
from sqlalchemy.orm import relationship

from app.infra.db.base import Base


class Transaction(Base):
    __tablename__ = "ctransactions"

    id = Column(Integer, primary_key=True)

    tx_timestamp_utc = Column(DateTime, server_default=func.now(), index=True)
    card_id = Column(Integer, ForeignKey("ccardx.id"), nullable=True, index=True)

    # MTI + bitmap
    mti = Column(String(4), index=True)
    bitmap = Column(String(32))

    # --- DE 2–4
    i_0002_pan = Column(String(19), index=True)
    i_0003_processing_code = Column(String(6))
    i_0004_amount_transaction = Column(String(12))
    i_0005_amount_settlement = Column(String(12))
    i_0006_amount_cardholder_billing = Column(String(12))

    # --- DE 7–13
    i_0007_transmission_datetime = Column(String(10))
    i_0008_amount_cardholder_billing_fee = Column(String(8))
    i_0009_conversion_rate_settlement = Column(String(8))
    i_0010_conversion_rate_cardholder_billing = Column(String(8))
    i_0011_stan = Column(String(6), index=True)
    i_0012_time_local = Column(String(6))
    i_0013_date_local = Column(String(4))

    # --- DE 14–21
    i_0014_expiration_date = Column(String(4))
    i_0015_settlement_date = Column(String(4))
    i_0016_currency_conversion_date = Column(String(4))
    i_0017_capture_date = Column(String(4))
    i_0018_merchant_type_mcc = Column(String(4))
    i_0019_acq_country_code = Column(String(3))
    i_0020_pan_extended_country_code = Column(String(3))
    i_0021_fwd_country_code = Column(String(3))

    # --- DE 22–27
    i_0022_pos_entry_mode = Column(String(3))
    i_0023_pan_sequence_number = Column(String(3))
    i_0024_function_code_nii = Column(String(3))
    i_0025_pos_condition_code = Column(String(2))
    i_0026_pos_capture_code = Column(String(2))
    i_0027_auth_id_response_length = Column(String(1))

    # --- DE 28–31
    i_0028_amount_tx_fee = Column(String(9))
    i_0029_amount_settlement_fee = Column(String(9))
    i_0030_amount_tx_processing_fee = Column(String(9))
    i_0031_amount_settlement_processing_fee = Column(String(9))

    # --- DE 32–36
    i_0032_acquiring_inst_id = Column(String(11))
    i_0033_forwarding_inst_id = Column(String(11))
    i_0034_pan_extended = Column(String(28))
    i_0035_track_2_data = Column(String(37))
    i_0036_track_3_data = Column(String(104))

    # --- DE 37–42
    i_0037_retrieval_reference_number = Column(String(12))
    i_0038_auth_id_response = Column(String(6))
    i_0039_response_code = Column(String(2))
    i_0040_service_restriction_code = Column(String(3))
    i_0041_card_acceptor_tid = Column(String(8))
    i_0042_card_acceptor_mid = Column(String(15))

    # --- DE 43–49
    i_0043_card_acceptor_name_loc = Column(String(40))
    i_0044_additional_response_data = Column(String(25))
    i_0045_track_1_data = Column(String(76))
    i_0046_additional_data_iso = Column(String)
    i_0047_additional_data_national = Column(String)
    i_0048_additional_data_private = Column(String)
    i_0049_currency_code_tx = Column(String(3))

    # --- DE 50–55
    i_0050_currency_code_settlement = Column(String(3))
    i_0051_currency_code_cardholder_billing = Column(String(3))
    i_0052_pin_data = Column(String(64))
    i_0053_security_control_info = Column(String(16))
    i_0054_additional_amounts = Column(String)
    i_0055_icc_data_emv = Column(String)

    # --- DE 56–63
    i_0056_reserved_iso = Column(String)
    i_0057_reserved_national = Column(String)
    i_0058_reserved = Column(String)
    i_0059_reserved = Column(String)
    i_0060_reserved_national = Column(String)
    i_0061_reserved_private = Column(String)
    i_0062_reserved_private_2 = Column(String)
    i_0063_reserved_private_3 = Column(String)

    # --- DE 64–72
    i_0064_message_authentication_code = Column(String(64))
    i_0065_extended_bitmap_indicator = Column(String(1))
    i_0066_settlement_code = Column(String(1))
    i_0067_extended_payment_code = Column(String(2))
    i_0068_receiving_inst_country_code = Column(String(3))
    i_0069_settlement_inst_country_code = Column(String(3))
    i_0070_network_management_info_code = Column(String(3))
    i_0071_message_number = Column(String(4))
    i_0072_last_message_number = Column(String(4))

    # --- DE 73–79
    i_0073_action_date = Column(String(6))
    i_0074_number_credits = Column(String(10))
    i_0075_credits_reversal_number = Column(String(10))
    i_0076_number_debits = Column(String(10))
    i_0077_debits_reversal_number = Column(String(10))
    i_0078_transfer_number = Column(String(10))
    i_0079_transfer_reversal_number = Column(String(10))

    # --- DE 80–89
    i_0080_number_inquiries = Column(String(10))
    i_0081_number_authorizations = Column(String(10))
    i_0082_credits_processing_fee_amount = Column(String(12))
    i_0083_credits_transaction_fee_amount = Column(String(12))
    i_0084_debits_processing_fee_amount = Column(String(12))
    i_0085_debits_transaction_fee_amount = Column(String(12))
    i_0086_total_amount_credits = Column(String(16))
    i_0087_credits_reversal_amount = Column(String(16))
    i_0088_total_amount_debits = Column(String(16))
    i_0089_debits_reversal_amount = Column(String(16))

    # --- DE 90–96
    i_0090_original_data_elements = Column(String)
    i_0091_file_update_code = Column(String(1))
    i_0092_file_security_code = Column(String(2))
    i_0093_response_indicator = Column(String(5))
    i_0094_service_indicator = Column(String(7))
    i_0095_replacement_amounts = Column(String)
    i_0096_message_security_code = Column(String(64))

    # --- DE 97–104
    i_0097_net_settlement_amount = Column(String(16))
    i_0098_payee = Column(String(25))
    i_0099_settlement_inst_id_code = Column(String(11))
    i_0100_receiving_inst_id_code = Column(String(11))
    i_0101_file_name = Column(String(17))
    i_0102_account_id_1 = Column(String(28))
    i_0103_account_id_2 = Column(String(28))
    i_0104_tx_description = Column(String(100))

    # --- Resultado de fraude
    es_fraude = Column(Boolean, default=False, index=True)
    probabilidad_fraude = Column(Float, default=0.0)
    nivel_riesgo = Column(String(10), index=True)
    factores_riesgo = Column(String(255))
    mensaje_analisis = Column(String(255))
    recomendacion_analisis = Column(String(255))
    analisis_timestamp = Column(DateTime)
    monto_dop_calculado = Column(DECIMAL(18, 2))

    # --- Historial
    historial_tx_24h = Column(Integer)
    historial_tx_7d = Column(Integer)
    monto_promedio_30d = Column(DECIMAL(18, 2))
    merchant_permitido = Column(Boolean)
    mcc_permitido = Column(Boolean)

    card = relationship("Card", back_populates="transactions")

    __table_args__ = (
        UniqueConstraint("i_0011_stan", "i_0041_card_acceptor_tid", name="uq_stan_tid"),
    )
