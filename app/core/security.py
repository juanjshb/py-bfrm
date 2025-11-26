# app/core/security.py
from fastapi import Header, HTTPException, status
from typing import Optional


async def get_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """
    Hook para futura autenticación por API Key.
    De momento no valida nada; lo dejamos como placeholder.
    """
    # Aquí podrías validar la API key contra BD o config.
    return
