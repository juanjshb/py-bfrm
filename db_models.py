# db_models.py
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    DECIMAL,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Currency(Base):
    """Tabla de códigos de moneda ISO 4217"""
    __tablename__ = "ccurrencies"

    id = Column(Integer, primary_key=True)
    code_numeric = Column(String(3), unique=True, nullable=False, index=True)
    code_alpha = Column(String(3), unique=True, nullable=False, index=True)
    name = Column(String(100))
    decimals = Column(Integer, default=2)


class Customer(Base):
    """Tabla de Clientes (ccustomers)"""
    __tablename__ = "ccustomers"

    id = Column(Integer, primary_key=True)
    customer_ref_id = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(150), unique=True)
    phone = Column(String(20))
    document_id = Column(String(50), unique=True)
    created_at = Column(DateTime, server_default=func.now())

    accounts = relationship("Account", back_populates="customer")


class Account(Base):
    """Tabla de Cuentas Bancarias (caccounts)"""
    __tablename__ = "caccounts"

    id = Column(Integer, primary_key=True)
    account_number = Column(String(30), unique=True, nullable=False, index=True)
    account_type = Column(String(50))
    status = Column(String(20), default="active")
    balance = Column(DECIMAL(18, 2), default=0.00)
    currency_code = Column(String(3), nullable=False)
    opened_at = Column(DateTime, server_default=func.now())

    customer_id = Column(Integer, ForeignKey("ccustomers.id"), nullable=False)

    customer = relationship("Customer", back_populates="accounts")
    cards = relationship("Card", back_populates="account")


class Card(Base):
    """Tabla de Tarjetas (ccardx)"""
    __tablename__ = "ccardx"

    id = Column(Integer, primary_key=True)
    pan = Column(String(20), unique=True, nullable=False, index=True)
    pan_last_4 = Column(String(4), nullable=False)
    pan_bin = Column(String(8), nullable=False)
    expiry_date = Column(String(4))
    card_type = Column(String(20))
    brand = Column(String(20))
    status = Column(String(20), default="active")

    account_id = Column(Integer, ForeignKey("caccounts.id"), nullable=False)

    account = relationship("Account", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card")


class MCC(Base):
    """Tabla de códigos MCC (cmcc)"""
    __tablename__ = "cmcc"

    id = Column(Integer, primary_key=True)
    mcc = Column(String(4), unique=True, nullable=False, index=True)
    descripcion = Column(String(255), nullable=False)
    riesgo_nivel = Column(String(10), default="MEDIO")  # BAJO/MEDIO/ALTO
    permitido = Column(Boolean, default=True)

    merchants = relationship("Merchant", back_populates="mcc_rel")


class Merchant(Base):
    """Tabla de Comercios (cmerchants)"""
    __tablename__ = "cmerchants"

    id = Column(Integer, primary_key=True)
    mid = Column(String(15), unique=True, nullable=False, index=True)
    nombre_comercial = Column(String(255))
    pais = Column(String(3))
    ciudad = Column(String(100))
    mcc = Column(String(4), ForeignKey("cmcc.mcc"))
    riesgo_nivel = Column(String(10), default="MEDIO")
    permitido = Column(Boolean, default=True)

    mcc_rel = relationship("MCC", back_populates="merchants")


class Transaction(Base):
    """Tabla de Transacciones (ctransactions) en formato ISO 8583"""
    __tablename__ = "ctransactions"

    id = Column(Integer, primary_key=True)

    tx_timestamp_utc = Column(DateTime, server_default=func.now(), index=True)

    card_id = Column(Integer, ForeignKey("ccardx.id"), nullable=True, index=True)

    mti = Column(String(4), index=True)
    bitmap = Column(String(128))
    i_0002_pan = Column(String(20), index=True)
    i_0003_processing_code = Column(String(6))
    i_0004_amount_transaction = Column(String(12))
    i_0007_transmission_datetime = Column(String(10))
    i_0011_stan = Column(String(6), index=True)
    i_0012_time_local = Column(String(6))
    i_0013_date_local = Column(String(4))
    i_0022_pos_entry_mode = Column(String(3))
    i_0024_function_code_nii = Column(String(3))
    i_0025_pos_condition_code = Column(String(2))
    i_0032_acquiring_inst_id = Column(String(11))
    i_0035_track_2_data = Column(String(37))
    i_0041_card_acceptor_tid = Column(String(8))
    i_0042_card_acceptor_mid = Column(String(15))
    i_0043_card_acceptor_name_loc = Column(String(40))
    i_0049_currency_code_tx = Column(String(3))
    i_0062_private_use_field = Column(String(255))
    i_0128_mac = Column(String(64))

    es_fraude = Column(Boolean, default=False, index=True)
    probabilidad_fraude = Column(Float, default=0.0)
    nivel_riesgo = Column(String(10), index=True)
    factores_riesgo = Column(String(255))
    mensaje_analisis = Column(String(255))
    recomendacion_analisis = Column(String(255))

    analisis_timestamp = Column(DateTime)
    monto_dop_calculado = Column(DECIMAL(18, 2))

    card = relationship("Card", back_populates="transactions")

    __table_args__ = (
        UniqueConstraint(
            "i_0011_stan",
            "i_0041_card_acceptor_tid",
            name="uq_stan_tid",
        ),
    )
