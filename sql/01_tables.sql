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


-----------------------------------------
-- SECCIÓN 2: DATOS DE PRUEBA
-----------------------------------------
-- Insertar Paises
INSERT INTO countries (iso2, iso3, numeric_code, name, region, subregion) VALUES
('AF','AFG','004','Afghanistan','Asia','Southern Asia'),
('AX','ALA','248','Åland Islands','Europe','Northern Europe'),
('AL','ALB','008','Albania','Europe','Southern Europe'),
('DZ','DZA','012','Algeria','Africa','Northern Africa'),
('AS','ASM','016','American Samoa','Oceania','Polynesia'),
('AD','AND','020','Andorra','Europe','Southern Europe'),
('AO','AGO','024','Angola','Africa','Sub-Saharan Africa'),
('AI','AIA','660','Anguilla','Americas','Caribbean'),
('AQ','ATA','010','Antarctica','Antarctica','Antarctica'),
('AG','ATG','028','Antigua and Barbuda','Americas','Caribbean'),
('AR','ARG','032','Argentina','Americas','South America'),
('AM','ARM','051','Armenia','Asia','Western Asia'),
('AW','ABW','533','Aruba','Americas','Caribbean'),
('AU','AUS','036','Australia','Oceania','Australia and New Zealand'),
('AT','AUT','040','Austria','Europe','Western Europe'),
('AZ','AZE','031','Azerbaijan','Asia','Western Asia'),
('BS','BHS','044','Bahamas','Americas','Caribbean'),
('BH','BHR','048','Bahrain','Asia','Western Asia'),
('BD','BGD','050','Bangladesh','Asia','Southern Asia'),
('BB','BRB','052','Barbados','Americas','Caribbean'),
('BY','BLR','112','Belarus','Europe','Eastern Europe'),
('BE','BEL','056','Belgium','Europe','Western Europe'),
('BZ','BLZ','084','Belize','Americas','Central America'),
('BJ','BEN','204','Benin','Africa','Sub-Saharan Africa'),
('BM','BMU','060','Bermuda','Americas','Northern America'),
('BT','BTN','064','Bhutan','Asia','Southern Asia'),
('BO','BOL','068','Bolivia','Americas','South America'),
('BQ','BES','535','Bonaire, Sint Eustatius and Saba','Americas','Caribbean'),
('BA','BIH','070','Bosnia and Herzegovina','Europe','Southern Europe'),
('BW','BWA','072','Botswana','Africa','Sub-Saharan Africa'),
('BV','BVT','074','Bouvet Island','Antarctica','Antarctica'),
('BR','BRA','076','Brazil','Americas','South America'),
('IO','IOT','086','British Indian Ocean Territory','Africa','Sub-Saharan Africa'),
('BN','BRN','096','Brunei Darussalam','Asia','South-Eastern Asia'),
('BG','BGR','100','Bulgaria','Europe','Eastern Europe'),
('BF','BFA','854','Burkina Faso','Africa','Sub-Saharan Africa'),
('BI','BDI','108','Burundi','Africa','Sub-Saharan Africa'),
('CV','CPV','132','Cabo Verde','Africa','Sub-Saharan Africa'),
('KH','KHM','116','Cambodia','Asia','South-Eastern Asia'),
('CM','CMR','120','Cameroon','Africa','Sub-Saharan Africa'),
('CA','CAN','124','Canada','Americas','Northern America'),
('KY','CYM','136','Cayman Islands','Americas','Caribbean'),
('CF','CAF','140','Central African Republic','Africa','Sub-Saharan Africa'),
('TD','TCD','148','Chad','Africa','Sub-Saharan Africa'),
('CL','CHL','152','Chile','Americas','South America'),
('CN','CHN','156','China','Asia','Eastern Asia'),
('CX','CXR','162','Christmas Island','Oceania','Australia and New Zealand'),
('CC','CCK','166','Cocos (Keeling) Islands','Oceania','Australia and New Zealand'),
('CO','COL','170','Colombia','Americas','South America'),
('KM','COM','174','Comoros','Africa','Sub-Saharan Africa'),
('CD','COD','180','Congo (DRC)','Africa','Sub-Saharan Africa'),
('CG','COG','178','Congo','Africa','Sub-Saharan Africa'),
('CK','COK','184','Cook Islands','Oceania','Polynesia'),
('CR','CRI','188','Costa Rica','Americas','Central America'),
('CI','CIV','384','Côte d Ivoire','Africa','Sub-Saharan Africa'),
('HR','HRV','191','Croatia','Europe','Southern Europe'),
('CU','CUB','192','Cuba','Americas','Caribbean'),
('CW','CUW','531','Curaçao','Americas','Caribbean'),
('CY','CYP','196','Cyprus','Asia','Western Asia'),
('CZ','CZE','203','Czechia','Europe','Eastern Europe'),
('DK','DNK','208','Denmark','Europe','Northern Europe'),
('DJ','DJI','262','Djibouti','Africa','Sub-Saharan Africa'),
('DM','DMA','212','Dominica','Americas','Caribbean'),
('DO','DOM','214','Dominican Republic','Americas','Caribbean'),
('EC','ECU','218','Ecuador','Americas','South America'),
('EG','EGY','818','Egypt','Africa','Northern Africa'),
('SV','SLV','222','El Salvador','Americas','Central America'),
('GQ','GNQ','226','Equatorial Guinea','Africa','Sub-Saharan Africa'),
('ER','ERI','232','Eritrea','Africa','Sub-Saharan Africa'),
('EE','EST','233','Estonia','Europe','Northern Europe'),
('SZ','SWZ','748','Eswatini','Africa','Sub-Saharan Africa'),
('ET','ETH','231','Ethiopia','Africa','Sub-Saharan Africa'),
('FK','FLK','238','Falkland Islands','Americas','South America'),
('FO','FRO','234','Faroe Islands','Europe','Northern Europe'),
('FJ','FJI','242','Fiji','Oceania','Melanesia'),
('FI','FIN','246','Finland','Europe','Northern Europe'),
('FR','FRA','250','France','Europe','Western Europe'),
('GF','GUF','254','French Guiana','Americas','South America'),
('PF','PYF','258','French Polynesia','Oceania','Polynesia'),
('TF','ATF','260','French Southern Territories','Antarctica','Antarctica'),
('GA','GAB','266','Gabon','Africa','Sub-Saharan Africa'),
('GM','GMB','270','Gambia','Africa','Sub-Saharan Africa'),
('GE','GEO','268','Georgia','Asia','Western Asia'),
('DE','DEU','276','Germany','Europe','Western Europe'),
('GH','GHA','288','Ghana','Africa','Sub-Saharan Africa'),
('GI','GIB','292','Gibraltar','Europe','Southern Europe'),
('GR','GRC','300','Greece','Europe','Southern Europe'),
('GL','GRL','304','Greenland','Americas','Northern America'),
('GD','GRD','308','Grenada','Americas','Caribbean'),
('GP','GLP','312','Guadeloupe','Americas','Caribbean'),
('GU','GUM','316','Guam','Oceania','Micronesia'),
('GT','GTM','320','Guatemala','Americas','Central America'),
('GG','GGY','831','Guernsey','Europe','Northern Europe'),
('GN','GIN','324','Guinea','Africa','Sub-Saharan Africa'),
('GW','GNB','624','Guinea-Bissau','Africa','Sub-Saharan Africa'),
('GY','GUY','328','Guyana','Americas','South America'),
('HT','HTI','332','Haiti','Americas','Caribbean'),
('HM','HMD','334','Heard Island and McDonald Islands','Antarctica','Antarctica'),
('VA','VAT','336','Holy See','Europe','Southern Europe'),
('HN','HND','340','Honduras','Americas','Central America'),
('HK','HKG','344','Hong Kong','Asia','Eastern Asia'),
('HU','HUN','348','Hungary','Europe','Eastern Europe'),
('IS','ISL','352','Iceland','Europe','Northern Europe'),
('IN','IND','356','India','Asia','Southern Asia'),
('ID','IDN','360','Indonesia','Asia','South-Eastern Asia'),
('IR','IRN','364','Iran','Asia','Southern Asia'),
('IQ','IRQ','368','Iraq','Asia','Western Asia'),
('IE','IRL','372','Ireland','Europe','Northern Europe'),
('IM','IMN','833','Isle of Man','Europe','Northern Europe'),
('IL','ISR','376','Israel','Asia','Western Asia'),
('IT','ITA','380','Italy','Europe','Southern Europe'),
('JM','JAM','388','Jamaica','Americas','Caribbean'),
('JP','JPN','392','Japan','Asia','Eastern Asia'),
('JE','JEY','832','Jersey','Europe','Northern Europe'),
('JO','JOR','400','Jordan','Asia','Western Asia'),
('KZ','KAZ','398','Kazakhstan','Asia','Central Asia'),
('KE','KEN','404','Kenya','Africa','Sub-Saharan Africa'),
('KI','KIR','296','Kiribati','Oceania','Micronesia'),
('KP','PRK','408','Korea (North)','Asia','Eastern Asia'),
('KR','KOR','410','Korea (South)','Asia','Eastern Asia'),
('KW','KWT','414','Kuwait','Asia','Western Asia'),
('KG','KGZ','417','Kyrgyzstan','Asia','Central Asia'),
('LA','LAO','418','Lao People''s Democratic Republic','Asia','South-Eastern Asia'),
('LV','LVA','428','Latvia','Europe','Northern Europe'),
('LB','LBN','422','Lebanon','Asia','Western Asia'),
('LS','LSO','426','Lesotho','Africa','Sub-Saharan Africa'),
('LR','LBR','430','Liberia','Africa','Sub-Saharan Africa'),
('LY','LBY','434','Libya','Africa','Northern Africa'),
('LI','LIE','438','Liechtenstein','Europe','Western Europe'),
('LT','LTU','440','Lithuania','Europe','Northern Europe'),
('LU','LUX','442','Luxembourg','Europe','Western Europe'),
('MO','MAC','446','Macao','Asia','Eastern Asia'),
('MG','MDG','450','Madagascar','Africa','Sub-Saharan Africa'),
('MW','MWI','454','Malawi','Africa','Sub-Saharan Africa'),
('MY','MYS','458','Malaysia','Asia','South-Eastern Asia'),
('MV','MDV','462','Maldives','Asia','Southern Asia'),
('ML','MLI','466','Mali','Africa','Sub-Saharan Africa'),
('MT','MLT','470','Malta','Europe','Southern Europe'),
('MH','MHL','584','Marshall Islands','Oceania','Micronesia'),
('MQ','MTQ','474','Martinique','Americas','Caribbean'),
('MR','MRT','478','Mauritania','Africa','Sub-Saharan Africa'),
('MU','MUS','480','Mauritius','Africa','Sub-Saharan Africa'),
('YT','MYT','175','Mayotte','Africa','Sub-Saharan Africa'),
('MX','MEX','484','Mexico','Americas','Central America'),
('FM','FSM','583','Micronesia (Federated States of)','Oceania','Micronesia'),
('MD','MDA','498','Moldova','Europe','Eastern Europe'),
('MC','MCO','492','Monaco','Europe','Western Europe'),
('MN','MNG','496','Mongolia','Asia','Eastern Asia'),
('ME','MNE','499','Montenegro','Europe','Southern Europe'),
('MS','MSR','500','Montserrat','Americas','Caribbean'),
('MA','MAR','504','Morocco','Africa','Northern Africa'),
('MZ','MOZ','508','Mozambique','Africa','Sub-Saharan Africa'),
('MM','MMR','104','Myanmar','Asia','South-Eastern Asia'),
('NA','NAM','516','Namibia','Africa','Sub-Saharan Africa'),
('NR','NRU','520','Nauru','Oceania','Micronesia'),
('NP','NPL','524','Nepal','Asia','Southern Asia'),
('NL','NLD','528','Netherlands','Europe','Western Europe'),
('NC','NCL','540','New Caledonia','Oceania','Melanesia'),
('NZ','NZL','554','New Zealand','Oceania','Australia and New Zealand'),
('NI','NIC','558','Nicaragua','Americas','Central America'),
('NE','NER','562','Niger','Africa','Sub-Saharan Africa'),
('NG','NGA','566','Nigeria','Africa','Sub-Saharan Africa'),
('NU','NIU','570','Niue','Oceania','Polynesia'),
('NF','NFK','574','Norfolk Island','Oceania','Australia and New Zealand'),
('MP','MNP','580','Northern Mariana Islands','Oceania','Micronesia'),
('NO','NOR','578','Norway','Europe','Northern Europe'),
('OM','OMN','512','Oman','Asia','Western Asia'),
('PK','PAK','586','Pakistan','Asia','Southern Asia'),
('PW','PLW','585','Palau','Oceania','Micronesia'),
('PS','PSE','275','Palestine, State of','Asia','Western Asia'),
('PA','PAN','591','Panama','Americas','Central America'),
('PG','PNG','598','Papua New Guinea','Oceania','Melanesia'),
('PY','PRY','600','Paraguay','Americas','South America'),
('PE','PER','604','Peru','Americas','South America'),
('PH','PHL','608','Philippines','Asia','South-Eastern Asia'),
('PN','PCN','612','Pitcairn','Oceania','Polynesia'),
('PL','POL','616','Poland','Europe','Eastern Europe'),
('PT','PRT','620','Portugal','Europe','Southern Europe'),
('PR','PRI','630','Puerto Rico','Americas','Caribbean'),
('QA','QAT','634','Qatar','Asia','Western Asia'),
('MK','MKD','807','North Macedonia','Europe','Southern Europe'),
('RO','ROU','642','Romania','Europe','Eastern Europe'),
('RU','RUS','643','Russian Federation','Europe','Eastern Europe'),
('RW','RWA','646','Rwanda','Africa','Sub-Saharan Africa'),
('RE','REU','638','Réunion','Africa','Sub-Saharan Africa'),
('BL','BLM','652','Saint Barthélemy','Americas','Caribbean'),
('SH','SHN','654','Saint Helena','Africa','Sub-Saharan Africa'),
('KN','KNA','659','Saint Kitts and Nevis','Americas','Caribbean'),
('LC','LCA','662','Saint Lucia','Americas','Caribbean'),
('MF','MAF','663','Saint Martin (French part)','Americas','Caribbean'),
('PM','SPM','666','Saint Pierre and Miquelon','Americas','Northern America'),
('VC','VCT','670','Saint Vincent and the Grenadines','Americas','Caribbean'),
('WS','WSM','882','Samoa','Oceania','Polynesia'),
('SM','SMR','674','San Marino','Europe','Southern Europe'),
('ST','STP','678','Sao Tome and Principe','Africa','Sub-Saharan Africa'),
('SA','SAU','682','Saudi Arabia','Asia','Western Asia'),
('SN','SEN','686','Senegal','Africa','Sub-Saharan Africa'),
('RS','SRB','688','Serbia','Europe','Southern Europe'),
('SC','SYC','690','Seychelles','Africa','Sub-Saharan Africa'),
('SL','SLE','694','Sierra Leone','Africa','Sub-Saharan Africa'),
('SG','SGP','702','Singapore','Asia','South-Eastern Asia'),
('SX','SXM','534','Sint Maarten (Dutch part)','Americas','Caribbean'),
('SK','SVK','703','Slovakia','Europe','Eastern Europe'),
('SI','SVN','705','Slovenia','Europe','Southern Europe'),
('SB','SLB','090','Solomon Islands','Oceania','Melanesia'),
('SO','SOM','706','Somalia','Africa','Sub-Saharan Africa'),
('ZA','ZAF','710','South Africa','Africa','Sub-Saharan Africa'),
('GS','SGS','239','South Georgia and the South Sandwich Islands','Antarctica','Antarctica'),
('SS','SSD','728','South Sudan','Africa','Sub-Saharan Africa'),
('ES','ESP','724','Spain','Europe','Southern Europe'),
('LK','LKA','144','Sri Lanka','Asia','Southern Asia'),
('SD','SDN','729','Sudan','Africa','Northern Africa'),
('SR','SUR','740','Suriname','Americas','South America'),
('SJ','SJM','744','Svalbard and Jan Mayen','Europe','Northern Europe'),
('SE','SWE','752','Sweden','Europe','Northern Europe'),
('CH','CHE','756','Switzerland','Europe','Western Europe'),
('SY','SYR','760','Syrian Arab Republic','Asia','Western Asia'),
('TW','TWN','158','Taiwan','Asia','Eastern Asia'),
('TJ','TJK','762','Tajikistan','Asia','Central Asia'),
('TZ','TZA','834','Tanzania','Africa','Sub-Saharan Africa'),
('TH','THA','764','Thailand','Asia','South-Eastern Asia'),
('TL','TLS','626','Timor-Leste','Asia','South-Eastern Asia'),
('TG','TGO','768','Togo','Africa','Sub-Saharan Africa'),
('TK','TKL','772','Tokelau','Oceania','Polynesia'),
('TO','TON','776','Tonga','Oceania','Polynesia'),
('TT','TTO','780','Trinidad and Tobago','Americas','Caribbean'),
('TN','TUN','788','Tunisia','Africa','Northern Africa'),
('TR','TUR','792','Turkey','Asia','Western Asia'),
('TM','TKM','795','Turkmenistan','Asia','Central Asia'),
('TC','TCA','796','Turks and Caicos Islands','Americas','Caribbean'),
('TV','TUV','798','Tuvalu','Oceania','Polynesia'),
('UG','UGA','800','Uganda','Africa','Sub-Saharan Africa'),
('UA','UKR','804','Ukraine','Europe','Eastern Europe'),
('AE','ARE','784','United Arab Emirates','Asia','Western Asia'),
('GB','GBR','826','United Kingdom','Europe','Northern Europe'),
('UM','UMI','581','United States Minor Outlying Islands','Oceania','Micronesia'),
('US','USA','840','United States of America','Americas','Northern America'),
('UY','URY','858','Uruguay','Americas','South America'),
('UZ','UZB','860','Uzbekistan','Asia','Central Asia'),
('VU','VUT','548','Vanuatu','Oceania','Melanesia'),
('VE','VEN','862','Venezuela','Americas','South America'),
('VN','VNM','704','Viet Nam','Asia','South-Eastern Asia'),
('VG','VGB','092','Virgin Islands (British)','Americas','Caribbean'),
('VI','VIR','850','Virgin Islands (U.S.)','Americas','Caribbean'),
('WF','WLF','876','Wallis and Futuna','Oceania','Polynesia'),
('EH','ESH','732','Western Sahara','Africa','Northern Africa'),
('YE','YEM','887','Yemen','Asia','Western Asia'),
('ZM','ZMB','894','Zambia','Africa','Sub-Saharan Africa'),
('ZW','ZWE','716','Zimbabwe','Africa','Sub-Saharan Africa');

-- Update Risk Level
UPDATE countries SET risk_level = 'HIGH' WHERE iso2 IN ('VE','HT');
UPDATE countries SET risk_level = 'MEDIUM'
WHERE iso2 NOT IN ('VE','HT','DO','US');
UPDATE countries SET risk_level = 'LOW'
WHERE iso2 IN ('DO','US');

-- Insertar Monedas
INSERT INTO ccurrencies (code_numeric, code_alpha, name, decimals) VALUES
('214', 'DOP', 'Peso Dominicano', 2),
('840', 'USD', 'Dólar Estadounidense', 2),
('978', 'EUR', 'Euro', 2);

-- Insertar MCC
INSERT INTO cmcc (mcc, descripcion, riesgo_nivel, permitido) VALUES
('5411', 'Supermercados y tiendas de comestibles', 'BAJO', TRUE),
('6011', 'Cajeros automáticos (ATM)', 'MEDIO', TRUE),
('7011', 'Hoteles y moteles', 'MEDIO', TRUE),
('7995', 'Apuestas y casinos', 'ALTO', FALSE);

-- Insertar Clientes
INSERT INTO ccustomers (customer_ref_id, first_name, last_name, email, document_id) VALUES
('CL-123456', 'Juan', 'Pérez', 'juan.perez@email.com', '001-1234567-8'),
('CL-789012', 'Maria', 'Gomez', 'maria.gomez@email.com', '001-9876543-2');

-- Insertar Cuentas
INSERT INTO caccounts (account_number, account_type, currency_code, customer_id) VALUES
('100020003000', 'Ahorros', 'DOP', (SELECT id FROM ccustomers WHERE customer_ref_id = 'CL-123456')),
('400050006000', 'Corriente', 'USD', (SELECT id FROM ccustomers WHERE customer_ref_id = 'CL-123456')),
('700080009000', 'Ahorros', 'DOP', (SELECT id FROM ccustomers WHERE customer_ref_id = 'CL-789012'));

-- Insertar Tarjetas
INSERT INTO ccardx (pan, pan_last_4, pan_bin, expiry_date, card_type, brand, status, account_id) VALUES
('4000123456789012', '9012', '400012', '1228', 'Débito', 'Visa', 'active', (SELECT id FROM caccounts WHERE account_number = '400050006000')),
('5100123456780001', '0001', '510012', '0627', 'Crédito', 'Mastercard', 'active', (SELECT id FROM caccounts WHERE account_number = '700080009000'));

-- Insertar Comercios
INSERT INTO cmerchants (mid, nombre_comercial, pais, ciudad, mcc, riesgo_nivel, permitido) VALUES
(1234567, 'Mi Tienda, Santo Domingo', 'DO', 'Santo Domingo', '5411', 'BAJO', TRUE);
INSERT INTO cmerchants (mid, nombre_comercial, pais, ciudad, mcc, riesgo_nivel, permitido) VALUES
(9876543, 'Hotel Caracas', 'VE', 'Caracas', '7011', 'MEDIO', TRUE);
INSERT INTO cmerchants (mid, nombre_comercial, pais, ciudad, mcc, riesgo_nivel, permitido) VALUES
(333444, 'Colmado Don Jose', 'DO', 'Santo Domingo', '5411', 'BAJO', TRUE);
INSERT INTO cmerchants (mid, nombre_comercial, pais, ciudad, mcc, riesgo_nivel, permitido) VALUES
(01, 'Casino Las Vegas', 'US', 'Las Vegas', '7995', 'ALTO', FALSE);

-- Insertar Transacciones de prueba (similar a tu script original)

-- Transacción 1: Normal - BAJO RIESGO
INSERT INTO ctransactions (
    card_id, mti, i_0002_pan, i_0003_processing_code, i_0004_amount_transaction,
    i_0007_transmission_datetime, i_0011_stan, i_0012_time_local, i_0013_date_local,
    i_0022_pos_entry_mode, i_0024_function_code_nii, i_0025_pos_condition_code,
    i_0032_acquiring_inst_id, i_0041_card_acceptor_tid, i_0042_card_acceptor_mid,
    i_0043_card_acceptor_name_loc, i_0049_currency_code_tx,
    es_fraude, probabilidad_fraude, nivel_riesgo, factores_riesgo,
    mensaje_analisis, recomendacion_analisis, analisis_timestamp, monto_dop_calculado,
    historial_tx_24h, historial_tx_7d, monto_promedio_30d, merchant_permitido, mcc_permitido
) VALUES (
    (SELECT id FROM ccardx WHERE pan = '4000123456789012'),
    '0100', '4000123456789012', '000000', '000000015050',
    '1114130930', '123456', '130930', '1114',
    '051', '200', '00',
    '123456', 'TERM0001', 'MERCHANT1234567',
    'Mi Tienda, Santo Domingo, DO', '840',
    FALSE, 0.15, 'BAJO', '',
    'Transacción dentro de parámetros normales', 'Recomendación: Transacción aprobada automáticamente',
    CURRENT_TIMESTAMP - INTERVAL '1 day', 8877.75,
    2, 5, 7500.00, TRUE, TRUE
);

-- Transacción 2: Alto Riesgo - USD, noche, Venezuela, hotel
INSERT INTO ctransactions (
    card_id, mti, i_0002_pan, i_0003_processing_code, i_0004_amount_transaction,
    i_0007_transmission_datetime, i_0011_stan, i_0012_time_local, i_0013_date_local,
    i_0022_pos_entry_mode, i_0024_function_code_nii, i_0025_pos_condition_code,
    i_0032_acquiring_inst_id, i_0041_card_acceptor_tid, i_0042_card_acceptor_mid,
    i_0043_card_acceptor_name_loc, i_0049_currency_code_tx,
    es_fraude, probabilidad_fraude, nivel_riesgo, factores_riesgo,
    mensaje_analisis, recomendacion_analisis, analisis_timestamp, monto_dop_calculado,
    historial_tx_24h, historial_tx_7d, monto_promedio_30d, merchant_permitido, mcc_permitido
) VALUES (
    (SELECT id FROM ccardx WHERE pan = '4000123456789012'),
    '0100', '4000123456789012', '000000', '000000100000',
    '1114030510', '123457', '030510', '1114',
    '051', '200', '00',
    '987654', 'TERM0002', 'MERCHANT9876543',
    'Hotel Caracas, VE', '840',
    TRUE, 0.85, 'ALTO', 'MONTO_ELEVADO,HORARIO_NOCTURNO,PAIS_ALTO_RIESGO,TRANSACCION_DIVISA,DIVISA_MONTO_ELEVADO',
    'ALERTA: Transacción identificada como fraudulenta por modelo ML y reglas de negocio',
    'Recomendación: Revisar transacción manualmente y contactar al cliente',
    CURRENT_TIMESTAMP - INTERVAL '1 hour', 59000.00,
    1, 3, 20000.00, TRUE, TRUE
);

-- Transacción 3: Tarjeta desconocida - ALTO RIESGO
INSERT INTO ctransactions (
    card_id, mti, i_0002_pan, i_0003_processing_code, i_0004_amount_transaction,
    i_0007_transmission_datetime, i_0011_stan, i_0012_time_local, i_0013_date_local,
    i_0022_pos_entry_mode, i_0024_function_code_nii, i_0025_pos_condition_code,
    i_0032_acquiring_inst_id, i_0041_card_acceptor_tid, i_0042_card_acceptor_mid,
    i_0043_card_acceptor_name_loc, i_0049_currency_code_tx,
    es_fraude, probabilidad_fraude, nivel_riesgo, factores_riesgo,
    mensaje_analisis, recomendacion_analisis, analisis_timestamp, monto_dop_calculado,
    historial_tx_24h, historial_tx_7d, monto_promedio_30d, merchant_permitido, mcc_permitido
) VALUES (
    NULL,
    '0100', '9999000011112222', '000000', '00000000500000',
    '1114021530', '555444', '021530', '1114',
    '021', '200', '00',
    '111222', 'TERM0003', 'MERCHANT333444',
    'Colmado Don Jose, Santo Domingo, DO', '214',
    TRUE, 0.70, 'ALTO', 'MONTO_ELEVADO,HORARIO_NOCTURNO,MONTO_ALTO_HORARIO_SOSPECHOSO',
    'ALERTA: Múltiples factores de riesgo identificados',
    'Recomendación: Revisar transacción manualmente y contactar al cliente',
    CURRENT_TIMESTAMP - INTERVAL '30 minutes', 5000.00,
    4, 10, 4500.00, TRUE, TRUE
);

-- Verificación rápida
SELECT 'ccurrencies' as tabla, COUNT(*) FROM ccurrencies
UNION ALL
SELECT 'ccustomers', COUNT(*) FROM ccustomers
UNION ALL
SELECT 'caccounts', COUNT(*) FROM caccounts
UNION ALL
SELECT 'ccardx', COUNT(*) FROM ccardx
UNION ALL
SELECT 'cmcc', COUNT(*) FROM cmcc
UNION ALL
SELECT 'cmerchants', COUNT(*) FROM cmerchants
UNION ALL
SELECT 'ctransactions', COUNT(*) FROM ctransactions;