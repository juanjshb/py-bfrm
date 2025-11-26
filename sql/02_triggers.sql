-- Create function to trigger on event detected
CREATE OR REPLACE FUNCTION set_card_id_from_pan()
RETURNS TRIGGER AS $$
DECLARE
    v_card_id INTEGER;
BEGIN
    -- Buscar tarjeta por PAN
    SELECT id INTO v_card_id
    FROM ccardx
    WHERE pan = NEW.i_0002_pan
    LIMIT 1;

    -- Si NO existe → crear tarjeta automáticamente
    IF v_card_id IS NULL THEN
        INSERT INTO ccardx (account_id, pan_token, last4, brand)
        VALUES (
            NULL,
            NEW.i_0002_pan,
            RIGHT(NEW.i_0002_pan, 4),
            'UNKNOWN'
        )
        RETURNING id INTO v_card_id;
    END IF;

    -- Asignar card_id
    NEW.card_id = v_card_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- Trigger fucntion on new transaction received
CREATE TRIGGER trg_set_card_id_from_pan
BEFORE INSERT ON ctransactions
FOR EACH ROW
EXECUTE FUNCTION set_card_id_from_pan();
