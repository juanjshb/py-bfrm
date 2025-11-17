-- Borrar tablas si ya existen (para pruebas limpias)
DROP TABLE IF EXISTS ctransactions;
DROP TABLE IF EXISTS ccardx;
DROP TABLE IF EXISTS caccounts;
DROP TABLE IF EXISTS ccustomers;
DROP TABLE IF EXISTS ccurrencies;
DROP TABLE IF EXISTS cmcc_codes;
DROP TABLE IF EXISTS cmonitored_merchants;

-- ... (Creación de ccurrencies, ccustomers, caccounts, ccardx sin cambios) ...

-- --- NUEVAS TABLAS ---

-- Tabla de MCCs
CREATE TABLE cmcc_codes (
    id SERIAL PRIMARY KEY,
    mcc VARCHAR(4) UNIQUE NOT NULL,
    description VARCHAR(255),
    risk_level VARCHAR(20) NOT NULL DEFAULT 'medium'
);
CREATE INDEX idx_cmcc_codes_mcc ON cmcc_codes(mcc);
CREATE INDEX idx_cmcc_codes_risk_level ON cmcc_codes(risk_level);

-- Tabla de Comerciantes Monitoreados
CREATE TABLE cmonitored_merchants (
    id SERIAL PRIMARY KEY,
    mid VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'watch',
    reason VARCHAR(255)
);
CREATE INDEX idx_cmonitored_merchants_mid ON cmonitored_merchants(mid);
CREATE INDEX idx_cmonitored_merchants_status ON cmonitored_merchants(status);


-- Tabla de Transacciones (Actualizada con i_0026_mcc)
CREATE TABLE ctransactions (
    id SERIAL PRIMARY KEY,
    tx_timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    card_id INTEGER, 
    
    mti VARCHAR(4),
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
    
    i_0026_mcc VARCHAR(4), -- <-- CAMPO AÑADIDO
    
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
    
    FOREIGN KEY (card_id) REFERENCES ccardx(id),
    UNIQUE (i_0011_stan, i_0041_card_acceptor_tid)
);
-- ... (Índices de ctransactions sin cambios) ...

-----------------------------------------
-- SECCIÓN 2: DATOS DE PRUEBA (ACTUALIZADOS)
-----------------------------------------

-- ... (Inserciones en ccurrencies, ccustomers, caccounts, ccardx sin cambios) ...

-- --- NUEVOS DATOS DE PRUEBA ---

-- Insertar MCCs de riesgo
INSERT INTO cmcc_codes (mcc, description, risk_level) VALUES
('5411', 'Supermercados', 'low'),
('5812', 'Restaurantes', 'low'),
('5541', 'Estaciones de Servicio', 'medium'),
('4722', 'Agencias de Viaje', 'medium'),
('5912', 'Farmacias', 'low'),
('7995', 'Apuestas/Juegos de Azar', 'high'),       -- ALTO RIESGO
('5967', 'Ventas Directas (Ej. Multinivel)', 'high'), -- ALTO RIESGO
('6051', 'Quasi-Cash (No financiero)', 'blocked'); -- BLOQUEADO

-- Insertar Comerciantes
INSERT INTO cmonitored_merchants (mid, name, status, reason) VALUES
('MERCHANT1234567', 'Mi Tienda (Ejemplo)', 'watch', 'Comercio normal'),
('MERCHANT_SEGURO', 'Amazon Web Services', 'allowed', 'Comercio confiable conocido (Lista Blanca)'),
('MERCHANT_MALO99', 'Apuestas Ilegales LLC', 'denied', 'Conocido por fraude (Lista Negra)');

-- Actualizar Transacciones de prueba para incluir MCC
INSERT INTO ctransactions (
    card_id, mti, i_0002_pan, i_0003_processing_code, i_0004_amount_transaction,
    i_0007_transmission_datetime, i_0011_stan, i_0012_time_local, i_0013_date_local,
    i_0026_mcc, -- <-- CAMPO AÑADIDO
    i_0041_card_acceptor_tid, i_0042_card_acceptor_mid,
    i_0043_card_acceptor_name_loc, i_0049_currency_code_tx,
    es_fraude, probabilidad_fraude, nivel_riesgo, factores_riesgo,
    mensaje_analisis, recomendacion_analisis, analisis_timestamp, monto_dop_calculado
) VALUES (
    (SELECT id FROM ccardx WHERE pan = '4000123456789012'), '0100', '4000123456789012', '000000', '000000015050',
    '1114130930', '123456', '130930', '1114',
    '5812', -- Restaurante
    'TERM0001', 'MERCHANT1234567',
    'Mi Tienda, Santo Domingo, DO', '840',
    FALSE, 0.15, 'BAJO', '',
    'Transacción dentro de parámetros normales', 'Recomendación: Transacción aprobada automáticamente',
    CURRENT_TIMESTAMP - INTERVAL '1 day', 8877.75
);

-- Transacción de prueba 2 (Alto Riesgo + MCC Alto Riesgo)
INSERT INTO ctransactions (
    card_id, mti, i_0002_pan, i_0003_processing_code, i_0004_amount_transaction,
    i_0007_transmission_datetime, i_0011_stan, i_0012_time_local, i_0013_date_local,
    i_0026_mcc, -- <-- CAMPO AÑADIDO
    i_0041_card_acceptor_tid, i_0042_card_acceptor_mid,
    i_0043_card_acceptor_name_loc, i_0049_currency_code_tx,
    es_fraude, probabilidad_fraude, nivel_riesgo, factores_riesgo,
    mensaje_analisis, recomendacion_analisis, analisis_timestamp, monto_dop_calculado
) VALUES (
    (SELECT id FROM ccardx WHERE pan = '4000123456789012'), '0100', '4000123456789012', '000000', '000000100000',
    '1114030510', '123457', '030510', '1114',
    '7995', -- Apuestas (Alto Riesgo)
    'TERM0002', 'MERCHANT_MALO99', -- Comercio en Lista Negra
    'Hotel Caracas, VE', '840',
    TRUE, 0.85, 'ALTO', 'MONTO_ELEVADO,HORARIO_NOCTURNO,PAIS_ALTO_RIESGO,MCC_ALTO_RIESGO,COMERCIO_BLOQUEADO',
    'ALERTA: Patrón anómalo (ML) y múltiples factores de riesgo (Reglas) detectados', 
    'Recomendación: Revisar transacción manualmente y contactar al cliente',
    CURRENT_TIMESTAMP - INTERVAL '1 hour', 59000.00
);
