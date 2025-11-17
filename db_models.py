# db_models.py
from sqlalchemy import (
    Column, String, Integer, DateTime, Float, Boolean,
    ForeignKey, DECIMAL, UniqueConstraint, func
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base
import datetime


class Currency(Base):
    __tablename__ = "ccurrencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code_numeric: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    code_alpha: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    decimals: Mapped[int] = mapped_column(Integer, default=2)


class Customer(Base):
    __tablename__ = "ccustomers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_ref_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    document_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    accounts = relationship("Account", back_populates="customer")


class Account(Base):
    __tablename__ = "caccounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    account_type: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="active")
    balance: Mapped[float] = mapped_column(DECIMAL(18, 2), default=0.0)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    opened_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("ccustomers.id"), nullable=False)

    customer = relationship("Customer", back_populates="accounts")
    cards = relationship("Card", back_populates="account")


class Card(Base):
    __tablename__ = "ccardx"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pan: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    pan_last_4: Mapped[str] = mapped_column(String(4), nullable=False)
    pan_bin: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    expiry_date: Mapped[str | None] = mapped_column(String(4))
    card_type: Mapped[str | None] = mapped_column(String(20))
    brand: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active")
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("caccounts.id"), nullable=False)

    account = relationship("Account", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card")


class Mcc(Base):
    __tablename__ = "cmcc"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mcc: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    riesgo_nivel: Mapped[str] = mapped_column(String(10), default="MEDIO")
    permitido: Mapped[bool] = mapped_column(Boolean, default=True)

    merchants = relationship("Merchant", back_populates="mcc_rel")


class Merchant(Base):
    __tablename__ = "cmerchants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mid: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    nombre_comercial: Mapped[str | None] = mapped_column(String(255))
    pais: Mapped[str | None] = mapped_column(String(3))
    ciudad: Mapped[str | None] = mapped_column(String(100))
    mcc: Mapped[str | None] = mapped_column(String(4), ForeignKey("cmcc.mcc"))
    riesgo_nivel: Mapped[str] = mapped_column(String(10), default="MEDIO")
    permitido: Mapped[bool] = mapped_column(Boolean, default=True)

    mcc_rel = relationship("Mcc", back_populates="merchants")


class Transaction(Base):
    __tablename__ = "ctransactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tx_timestamp_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    card_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ccardx.id"), nullable=True)

    mti: Mapped[str | None] = mapped_column(String(4))
    bitmap: Mapped[str | None] = mapped_column(String(128))
    i_0002_pan: Mapped[str | None] = mapped_column(String(20), index=True)
    i_0003_processing_code: Mapped[str | None] = mapped_column(String(6))
    i_0004_amount_transaction: Mapped[str | None] = mapped_column(String(12))
    i_0007_transmission_datetime: Mapped[str | None] = mapped_column(String(10))
    i_0011_stan: Mapped[str | None] = mapped_column(String(6), index=True)
    i_0012_time_local: Mapped[str | None] = mapped_column(String(6))
    i_0013_date_local: Mapped[str | None] = mapped_column(String(4))
    i_0022_pos_entry_mode: Mapped[str | None] = mapped_column(String(3))
    i_0024_function_code_nii: Mapped[str | None] = mapped_column(String(3))
    i_0025_pos_condition_code: Mapped[str | None] = mapped_column(String(2))
    i_0032_acquiring_inst_id: Mapped[str | None] = mapped_column(String(11))
    i_0035_track_2_data: Mapped[str | None] = mapped_column(String(37))
    i_0041_card_acceptor_tid: Mapped[str | None] = mapped_column(String(8))
    i_0042_card_acceptor_mid: Mapped[str | None] = mapped_column(String(15))
    i_0043_card_acceptor_name_loc: Mapped[str | None] = mapped_column(String(40))
    i_0049_currency_code_tx: Mapped[str | None] = mapped_column(String(3))
    i_0062_private_use_field: Mapped[str | None] = mapped_column(String(255))
    i_0128_mac: Mapped[str | None] = mapped_column(String(64))

    es_fraude: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    probabilidad_fraude: Mapped[float] = mapped_column(Float, default=0.0)
    nivel_riesgo: Mapped[str | None] = mapped_column(String(10), index=True)
    factores_riesgo: Mapped[str | None] = mapped_column(String(255))
    mensaje_analisis: Mapped[str | None] = mapped_column(String(255))
    recomendacion_analisis: Mapped[str | None] = mapped_column(String(255))
    analisis_timestamp: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    monto_dop_calculado: Mapped[float | None] = mapped_column(DECIMAL(18, 2))

    historial_tx_24h: Mapped[int | None] = mapped_column(Integer)
    historial_tx_7d: Mapped[int | None] = mapped_column(Integer)
    monto_promedio_30d: Mapped[float | None] = mapped_column(DECIMAL(18, 2))
    merchant_permitido: Mapped[bool | None] = mapped_column(Boolean)
    mcc_permitido: Mapped[bool | None] = mapped_column(Boolean)

    card = relationship("Card", back_populates="transactions")

    __table_args__ = (
        UniqueConstraint("i_0011_stan", "i_0041_card_acceptor_tid", name="uq_stan_tid"),
    )
