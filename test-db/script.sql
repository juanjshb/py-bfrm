-- Borrar tablas si ya existen (para pruebas limpias)
DROP TABLE IF EXISTS ctransactions;
DROP TABLE IF EXISTS cmerchants;
DROP TABLE IF EXISTS cmcc;
DROP TABLE IF EXISTS ccardx;
DROP TABLE IF EXISTS caccounts;
DROP TABLE IF EXISTS ccustomers;
DROP TABLE IF EXISTS ccurrencies;

-----------------------------------------
-- SECCIÓN 1: CREACIÓN DE TABLAS
-----------------------------------------

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
    FOREIGN KEY (account_id) REFERENCES caccounts(id)
);
CREATE INDEX idx_ccardx_pan ON ccardx(pan);
CREATE INDEX idx_ccardx_pan_bin ON ccardx(pan_bin);

-- Tabla de códigos MCC
CREATE TABLE cmcc (
    id SERIAL PRIMARY KEY,
    mcc VARCHAR(4) UNIQUE NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    riesgo_nivel VARCHAR(10) DEFAULT 'MEDIO',  -- BAJO/MEDIO/ALTO
    permitido BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_cmcc_mcc ON cmcc(mcc);

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

-- Tabla de Transacciones (ISO 8583 + Resultados de Fraude)
CREATE TABLE ctransactions (
    id SERIAL PRIMARY KEY,
    tx_timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- ID de la tarjeta en nuestra DB.
    -- Es NULLABLE porque una transacción puede venir de una tarjeta
    -- que (aún) no tenemos registrada.
    card_id INTEGER, 
    
    -- Campos ISO 8583
    mti VARCHAR(4),
    bitmap VARCHAR(128),
    i_0002_pan VARCHAR(20),
    i_0003_processing_code VARCHAR(6),
    i_0004_amount_transaction VARCHAR(12),
    i_0007_transmission_datetime VARCHAR(10),
    i_0011_stan VARCHAR(6),
    i_0012_time_local VARCHAR(6),
    i_0013_date_local VARCHAR(4),
    i_0022_pos_entry_mode VARCHAR(3),
    i_0024_function_code_nii VARCHAR(3),
    i_0025_pos_condition_code VARCHAR(2),
    i_0032_acquiring_inst_id VARCHAR(11),
    i_0035_track_2_data VARCHAR(37),
    i_0041_card_acceptor_tid VARCHAR(8),
    i_0042_card_acceptor_mid VARCHAR(15),
    i_0043_card_acceptor_name_loc VARCHAR(40),
    i_0049_currency_code_tx VARCHAR(3),
    i_0062_private_use_field VARCHAR(255),
    i_0128_mac VARCHAR(64),
    
    -- Resultados del Análisis de Fraude
    es_fraude BOOLEAN DEFAULT FALSE,
    probabilidad_fraude FLOAT DEFAULT 0.0,
    nivel_riesgo VARCHAR(10),
    factores_riesgo VARCHAR(255),
    mensaje_analisis VARCHAR(255),
    recomendacion_analisis VARCHAR(255),
    analisis_timestamp TIMESTAMP,
    monto_dop_calculado DECIMAL(18, 2),
    
    -- Constraints & Indexes
    FOREIGN KEY (card_id) REFERENCES ccardx(id),
    UNIQUE (i_0011_stan, i_0041_card_acceptor_tid) -- Transacción única por STAN y Terminal
);
CREATE INDEX idx_ctransactions_tx_time ON ctransactions(tx_timestamp_utc);
CREATE INDEX idx_ctransactions_card_id ON ctransactions(card_id);
CREATE INDEX idx_ctransactions_pan ON ctransactions(i_0002_pan);
CREATE INDEX idx_ctransactions_stan ON ctransactions(i_0011_stan);
CREATE INDEX idx_ctransactions_es_fraude ON ctransactions(es_fraude);
CREATE INDEX idx_ctransactions_nivel_riesgo ON ctransactions(nivel_riesgo);

-----------------------------------------
-- SECCIÓN 2: DATOS DE PRUEBA
-----------------------------------------

-- Insertar Monedas
INSERT INTO ccurrencies (code_numeric, code_alpha, name, decimals) VALUES
('214', 'DOP', 'Peso Dominicano', 2),
('840', 'USD', 'Dólar Estadounidense', 2),
('978', 'EUR', 'Euro', 2);

-- Insertar Clientes
INSERT INTO ccustomers (customer_ref_id, first_name, last_name, email, document_id) VALUES
('CL-123456', 'Juan', 'Pérez', 'juan.perez@email.com', '001-1234567-8'),
('CL-789012', 'Maria', 'Gomez', 'maria.gome
