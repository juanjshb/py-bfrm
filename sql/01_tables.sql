-- Borrar tablas si ya existen (para pruebas limpias)
DROP TABLE IF EXISTS ctransactions;
DROP TABLE IF EXISTS ccardx;
DROP TABLE IF EXISTS caccounts;
DROP TABLE IF EXISTS ccustomers;
DROP TABLE IF EXISTS ccurrencies;
DROP TABLE IF EXISTS cmerchants;
DROP TABLE IF EXISTS cmcc;
DROP TABLE IF EXISTS ctransactions;

-----------------------------------------
-- SECCIÓN 1: CREACIÓN DE TABLAS
-----------------------------------------

-- Tabla de Paises (ISO 3166)
CREATE TABLE countries (
    country_id SERIAL PRIMARY KEY,
    iso2 CHAR(2) NOT NULL UNIQUE,
    iso3 CHAR(3) NOT NULL UNIQUE,
    numeric_code CHAR(3) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    region VARCHAR(80),
    subregion VARCHAR(80),
    isk_level VARCHAR(20) DEFAULT 'LOW',
    is_high_risk BOOLEAN GENERATED ALWAYS AS (risk_level = 'HIGH') STORED,
    is_medium_risk BOOLEAN GENERATED ALWAYS AS (risk_level = 'MEDIUM') STORED

);

ALTER TABLE countries
ADD COLUMN risk_level VARCHAR(20) DEFAULT 'LOW',
ADD COLUMN is_high_risk BOOLEAN GENERATED ALWAYS AS (risk_level = 'HIGH') STORED,
ADD COLUMN is_medium_risk BOOLEAN GENERATED ALWAYS AS (risk_level = 'MEDIUM') STORED;

-- Tabla de Monedas (ISO 4217)
CREATE TABLE ccurrencies (
    id SERIAL PRIMARY KEY,
    code_numeric VARCHAR(3) UNIQUE NOT NULL,
    code_alpha VARCHAR(3) UNIQUE NOT NULL,
    name VARCHAR(100),
    decimals INTEGER DEFAULT 2
);
CREATE INDEX idx_ccurrencies_code_numeric ON ccurrencies(code_numeric);
CREATE INDEX idx_ccurrencies_code_alpha ON ccurrencies(code_alpha);

-- Tabla de Clientes
CREATE TABLE ccustomers (
    id SERIAL PRIMARY KEY,
    customer_ref_id VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(150) UNIQUE,
    phone VARCHAR(20),
    document_id VARCHAR(50) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ccustomers_ref_id ON ccustomers(customer_ref_id);

-- Tabla de Cuentas Bancarias
CREATE TABLE caccounts (
    id SERIAL PRIMARY KEY,
    account_number VARCHAR(30) UNIQUE NOT NULL,
    account_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    balance DECIMAL(18, 2) DEFAULT 0.00,
    currency_code VARCHAR(3) NOT NULL,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    customer_id INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES ccustomers(id)
);
CREATE INDEX idx_caccounts_account_number ON caccounts(account_number);
CREATE INDEX idx_caccounts_customer_id ON caccounts(customer_id);

-- Tabla de Tarjetas
CREATE TABLE ccardx (
    id SERIAL PRIMARY KEY,
    pan VARCHAR(20) UNIQUE NOT NULL,
    pan_last_4 VARCHAR(4) NOT NULL,
    pan_bin VARCHAR(8) NOT NULL,
    expiry_date VARCHAR(4),
    card_type VARCHAR(20),
    brand VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active',
    account_id INTEGER NOT NULL,
    pan_token VARCHAR(32),
    last4 VARCHAR(4),
    creado_en TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES caccounts(id)
);
CREATE INDEX idx_ccardx_pan ON ccardx(pan);
CREATE INDEX idx_ccardx_pan_bin ON ccardx(pan_bin);
CREATE INDEX idx_ccardx_account_id ON ccardx(account_id);

-- Tabla de MCC (Merchant Category Code)
CREATE TABLE cmcc (
    id SERIAL PRIMARY KEY,
    mcc VARCHAR(4) UNIQUE NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    riesgo_nivel VARCHAR(10) DEFAULT 'MEDIO', -- BAJO / MEDIO / ALTO
    permitido BOOLEAN DEFAULT TRUE
);

-- Tabla de Comercios (Merchants)
CREATE TABLE cmerchants (
    id SERIAL PRIMARY KEY,
    mid VARCHAR(15) UNIQUE NOT NULL,
    nombre_comercial VARCHAR(255),
    pais VARCHAR(3),
    ciudad VARCHAR(100),
    mcc VARCHAR(4),
    riesgo_nivel VARCHAR(10) DEFAULT 'MEDIO',
    permitido BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (mcc) REFERENCES cmcc(mcc)
);
CREATE INDEX idx_cmerchants_mid ON cmerchants(mid);
CREATE INDEX idx_cmerchants_mcc ON cmerchants(mcc);
CREATE INDEX idx_cmerchants_pais ON cmerchants(pais);

-- Tabla de Transacciones (ISO 8583 + Resultados de Fraude)
CREATE TABLE ctransactions (
    id SERIAL PRIMARY KEY,

    -- Metadatos locales
    tx_timestamp_utc TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Llave foránea a la tarjeta
    card_id INTEGER NOT NULL REFERENCES ccardx(id),

    -------------------------------------------------
    -- CAMPOS ISO 8583 (nombres i_00xx_*)
    -------------------------------------------------
    -- Bitmap & MTI
    mti VARCHAR(4),
    bitmap VARCHAR(32),

    -- DE 2–4
    i_0002_pan VARCHAR(19),
    i_0003_processing_code VARCHAR(6),
    i_0004_amount_transaction VARCHAR(12),
    i_0005_amount_settlement VARCHAR(12),
    i_0006_amount_cardholder_billing VARCHAR(12),

    -- DE 7–13
    i_0007_transmission_datetime VARCHAR(10),
    i_0008_amount_cardholder_billing_fee VARCHAR(8),
    i_0009_conversion_rate_settlement VARCHAR(8),
    i_0010_conversion_rate_cardholder_billing VARCHAR(8),
    i_0011_stan VARCHAR(6),
    i_0012_time_local VARCHAR(6),
    i_0013_date_local VARCHAR(4),

    -- DE 14–21
    i_0014_expiration_date VARCHAR(4),
    i_0015_settlement_date VARCHAR(4),
    i_0016_currency_conversion_date VARCHAR(4),
    i_0017_capture_date VARCHAR(4),
    i_0018_merchant_type_mcc VARCHAR(4),
    i_0019_acq_country_code VARCHAR(3),
    i_0020_pan_extended_country_code VARCHAR(3),
    i_0021_fwd_country_code VARCHAR(3),

    -- DE 22–27
    i_0022_pos_entry_mode VARCHAR(3),
    i_0023_pan_sequence_number VARCHAR(3),
    i_0024_function_code_nii VARCHAR(3),
    i_0025_pos_condition_code VARCHAR(2),
    i_0026_pos_capture_code VARCHAR(2),
    i_0027_auth_id_response_length VARCHAR(1),

    -- DE 28–31 (x+n 8 → lo guardamos como string)
    i_0028_amount_tx_fee VARCHAR(9),
    i_0029_amount_settlement_fee VARCHAR(9),
    i_0030_amount_tx_processing_fee VARCHAR(9),
    i_0031_amount_settlement_processing_fee VARCHAR(9),

    -- DE 32–36
    i_0032_acquiring_inst_id VARCHAR(11),
    i_0033_forwarding_inst_id VARCHAR(11),
    i_0034_pan_extended VARCHAR(28),
    i_0035_track_2_data VARCHAR(37),
    i_0036_track_3_data VARCHAR(104),

    -- DE 37–42
    i_0037_retrieval_reference_number VARCHAR(12),
    i_0038_auth_id_response VARCHAR(6),
    i_0039_response_code VARCHAR(2),
    i_0040_service_restriction_code VARCHAR(3),
    i_0041_card_acceptor_tid VARCHAR(8),
    i_0042_card_acceptor_mid VARCHAR(15),

    -- DE 43–49
    i_0043_card_acceptor_name_loc VARCHAR(40),
    i_0044_additional_response_data VARCHAR(25),
    i_0045_track_1_data VARCHAR(76),
    i_0046_additional_data_iso TEXT,
    i_0047_additional_data_national TEXT,
    i_0048_additional_data_private TEXT,
    i_0049_currency_code_tx VARCHAR(3),

    -- DE 50–55
    i_0050_currency_code_settlement VARCHAR(3),
    i_0051_currency_code_cardholder_billing VARCHAR(3),
    i_0052_pin_data VARCHAR(64),
    i_0053_security_control_info VARCHAR(16),
    i_0054_additional_amounts TEXT,
    i_0055_icc_data_emv TEXT,

    -- DE 56–63
    i_0056_reserved_iso TEXT,
    i_0057_reserved_national TEXT,
    i_0058_reserved TEXT,
    i_0059_reserved TEXT,
    i_0060_reserved_national TEXT,
    i_0061_reserved_private TEXT,
    i_0062_reserved_private_2 TEXT,
    i_0063_reserved_private_3 TEXT,

    -- DE 64
    i_0064_message_authentication_code VARCHAR(64),

    -- DE 65–72
    i_0065_extended_bitmap_indicator VARCHAR(1),
    i_0066_settlement_code VARCHAR(1),
    i_0067_extended_payment_code VARCHAR(2),
    i_0068_receiving_inst_country_code VARCHAR(3),
    i_0069_settlement_inst_country_code VARCHAR(3),
    i_0070_network_management_info_code VARCHAR(3),
    i_0071_message_number VARCHAR(4),
    i_0072_last_message_number VARCHAR(4),

    -- DE 73–79
    i_0073_action_date VARCHAR(6),
    i_0074_number_credits VARCHAR(10),
    i_0075_credits_reversal_number VARCHAR(10),
    i_0076_number_debits VARCHAR(10),
    i_0077_debits_reversal_number VARCHAR(10),
    i_0078_transfer_number VARCHAR(10),
    i_0079_transfer_reversal_number VARCHAR(10),

    -- DE 80–89
    i_0080_number_inquiries VARCHAR(10),
    i_0081_number_authorizations VARCHAR(10),
    i_0082_credits_processing_fee_amount VARCHAR(12),
    i_0083_credits_transaction_fee_amount VARCHAR(12),
    i_0084_debits_processing_fee_amount VARCHAR(12),
    i_0085_debits_transaction_fee_amount VARCHAR(12),
    i_0086_total_amount_credits VARCHAR(16),
    i_0087_credits_reversal_amount VARCHAR(16),
    i_0088_total_amount_debits VARCHAR(16),
    i_0089_debits_reversal_amount VARCHAR(16),

    -- DE 90–96
    i_0090_original_data_elements TEXT,
    i_0091_file_update_code VARCHAR(1),
    i_0092_file_security_code VARCHAR(2),
    i_0093_response_indicator VARCHAR(5),
    i_0094_service_indicator VARCHAR(7),
    i_0095_replacement_amounts TEXT,
    i_0096_message_security_code VARCHAR(64),

    -- DE 97–104
    i_0097_net_settlement_amount VARCHAR(16),
    i_0098_payee VARCHAR(25),
    i_0099_settlement_inst_id_code VARCHAR(11),
    i_0100_receiving_inst_id_code VARCHAR(11),
    i_0101_file_name VARCHAR(17),
    i_0102_account_id_1 VARCHAR(28),
    i_0103_account_id_2 VARCHAR(28),
    i_0104_tx_description VARCHAR(100),

    -------------------------------------------------
    -- CAMPOS PARA ANÁLISIS DE FRAUDE
    -------------------------------------------------
    es_fraude BOOLEAN DEFAULT FALSE,
    probabilidad_fraude FLOAT DEFAULT 0.0,
    nivel_riesgo VARCHAR(10),
    factores_riesgo VARCHAR(255),
    mensaje_analisis VARCHAR(255),
    recomendacion_analisis VARCHAR(255),
    analisis_timestamp TIMESTAMP,
    monto_dop_calculado DECIMAL(18, 2),

    -- Historial cliente / merchant
    historial_tx_24h INTEGER,
    historial_tx_7d INTEGER,
    monto_promedio_30d DECIMAL(18, 2),
    merchant_permitido BOOLEAN,
    mcc_permitido BOOLEAN
);

-- Índices recomendados
CREATE INDEX idx_ctransactions_tx_time ON ctransactions(tx_timestamp_utc);
CREATE INDEX idx_ctransactions_card_id ON ctransactions(card_id);
CREATE INDEX idx_ctransactions_pan ON ctransactions(i_0002_pan);
CREATE INDEX idx_ctransactions_stan ON ctransactions(i_0011_stan);
CREATE INDEX idx_ctransactions_tid ON ctransactions(i_0041_card_acceptor_tid);
CREATE INDEX idx_ctransactions_mid ON ctransactions(i_0042_card_acceptor_mid);
CREATE INDEX idx_ctransactions_es_fraude ON ctransactions(es_fraude);
CREATE INDEX idx_ctransactions_nivel_riesgo ON ctransactions(nivel_riesgo);


-- Entidades SDN principales
CREATE TABLE ofac_entity (
    id              BIGSERIAL PRIMARY KEY,
    ent_num         INT NOT NULL UNIQUE,  -- ENT_NUM de OFAC
    sdn_name        TEXT NOT NULL,
    sdn_type        VARCHAR(50),          -- Individual, Entity, Vessel, etc.
    program         TEXT,                 -- Programas de sanción
    title           TEXT,
    remarks         TEXT,
    is_individual   BOOLEAN,              -- flag util para screening de personas
    last_updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Aliases (ALT.CSV)
CREATE TABLE ofac_alias (
    id          BIGSERIAL PRIMARY KEY,
    ent_num     INT NOT NULL REFERENCES ofac_entity(ent_num) ON DELETE CASCADE,
    alt_name    TEXT NOT NULL,
    alt_type    VARCHAR(50),              -- strong/weak, etc. si lo quieres mapear
    remarks     TEXT
);

-- Direcciones (ADD.CSV)
CREATE TABLE ofac_address (
    id          BIGSERIAL PRIMARY KEY,
    ent_num     INT NOT NULL REFERENCES ofac_entity(ent_num) ON DELETE CASCADE,
    address1    TEXT,
    address2    TEXT,
    city        TEXT,
    state       TEXT,
    postal_code TEXT,
    country     TEXT
);

-- Opcional: metadatos de sincronización
CREATE TABLE ofac_metadata (
    id              INT PRIMARY KEY DEFAULT 1,
    last_sync_at    TIMESTAMP,
    last_source_hash TEXT
);

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_ofac_sdn_name_trgm
ON ofac_entity
USING gin (sdn_name gin_trgm_ops);

CREATE INDEX idx_ofac_alias_name_trgm
ON ofac_alias
USING gin (alt_name gin_trgm_ops);

CREATE TABLE risk_factors (
    id SERIAL PRIMARY KEY,
    code VARCHAR(80) UNIQUE NOT NULL,      -- HIGH_AMOUNT, NIGHT_TIME, etc.
    description VARCHAR(255) NOT NULL,     -- texto entendible para auditoría
    weight NUMERIC(6,3) NOT NULL,          -- peso numérico
    category VARCHAR(50) NOT NULL,         -- AMOUNT, GEO, TIME, AML, KYC
    severity VARCHAR(20) NOT NULL,         -- LOW, MEDIUM, HIGH, CRITICAL
    enabled BOOLEAN DEFAULT TRUE,          -- por si quieres desactivar un factor sin borrarlo
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE risk_factor_rules (
    id SERIAL PRIMARY KEY,
    trigger_factors TEXT[] NOT NULL,      -- ['HIGH_AMOUNT','NIGHT_TIME']
    result_factor VARCHAR(80) NOT NULL,   -- HIGH_AMOUNT_SUSPICIOUS_TIME
    weight_override NUMERIC(6,3),         -- opcional
    enabled BOOLEAN DEFAULT TRUE
);

CREATE TABLE risk_factor_critical (
    factor_code VARCHAR(80) PRIMARY KEY,  -- OFAC_FULL_MATCH, DEVICE_COMPROMISED
    auto_fail BOOLEAN DEFAULT TRUE         -- si true => fraude automático
);

CREATE TABLE risk_factor_versions (
    id SERIAL PRIMARY KEY,
    factor_code VARCHAR(80) NOT NULL,
    old_weight NUMERIC(6,3),
    new_weight NUMERIC(6,3),
    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by VARCHAR(80)
);

