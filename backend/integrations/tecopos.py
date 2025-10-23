"""
Funciones utilitarias para comunicarse con el API de Tecopos.

Esta capa se encarga de construir las URLs base por región, montar los
encabezados necesarios para las peticiones y exponer helpers para
consultar negocios, proveedores y reportes de ventas. Los tokens de
autenticación se pasan como parámetro y no se almacenan aquí.
"""

from __future__ import annotations

import os
import requests
from typing import Dict, List, Optional

# Configuración de regiones y URLs por defecto. Las claves corresponden
# a las regiones utilizadas en Tecopos. Se pueden redefinir mediante
# variables de entorno del estilo TECOPOS_BASE_api=https://api2.tecopos.com.
DEFAULT_BASES: Dict[str, str] = {
    "api": "https://api.tecopos.com",
    "api2": "https://api2.tecopos.com",
    "api3": "https://api3.tecopos.com",
    "api4": "https://api4.tecopos.com",
}

# Lista de regiones soportadas. Se mantiene como constante para exponer al frontend.
REGIONS: List[str] = list(DEFAULT_BASES.keys())


def base_url(region: str) -> str:
    """Devuelve la URL base para una región dada.

    Busca primero en las variables de entorno `TECOPOS_BASE_<region>`. Si no
    existe, toma el valor por defecto. El resultado siempre se devuelve
    sin barra final.
    """
    env_key = f"TECOPOS_BASE_{region}"
    custom = os.getenv(env_key)
    base = custom or DEFAULT_BASES.get(region)
    if not base:
        raise ValueError(f"Región desconocida o no configurada: {region}")
    return base.rstrip("/")


def headers_with_token(access_token: str, business_id: Optional[str] = None) -> Dict[str, str]:
    """Construye los encabezados HTTP necesarios para llamar a Tecopos."""
    headers = {
        "Authorization": access_token,
        "Content-Type": "application/json",
    }
    if business_id:
        headers["x-app-businessid"] = business_id
    return headers


def list_businesses_with_token(region: str, access_token: str) -> List[Dict[str, object]]:
    """
    Devuelve una lista de negocios asociados al token. Lanza excepciones si
    ocurre algún error de red o autenticación.

    Para mayor flexibilidad, la respuesta no se valida y se devuelve tal cual.
    """
    url = f"{base_url(region)}/api/v1/administration/my-business"
    resp = requests.get(url, headers=headers_with_token(access_token), timeout=20)
    resp.raise_for_status()
    data = resp.json() or []
    return data


def list_suppliers_with_token(region: str, business_id: str, access_token: str, name_query: str) -> List[Dict[str, object]]:
    """
    Busca proveedores por nombre en una región y negocio determinados.

    Devuelve la lista de resultados tal cual la entrega Tecopos. Si el
    endpoint cambia, ajusta aquí la URL y los parámetros.
    """
    url = f"{base_url(region)}/api/v1/administration/provider"
    params = {"page": 1, "name": name_query}
    resp = requests.get(url, headers=headers_with_token(access_token, business_id), params=params, timeout=20)
    resp.raise_for_status()
    return resp.json() or []


def get_selled_products(
    region: str,
    business_id: str,
    access_token: str,
    date_from: str,
    date_to: str,
) -> List[Dict[str, object]]:
    """
    Obtiene el reporte de productos vendidos en el rango de fechas dado.

    La API de Tecopos espera `dateFrom` y `dateTo` con formato 'YYYY-MM-DD'.
    """
    url = f"{base_url(region)}/api/v1/report/selled-products"
    payload = {
        "dateFrom": date_from,
        "dateTo": date_to,
    }
    resp = requests.post(url, json=payload, headers=headers_with_token(access_token, business_id), timeout=30)
    resp.raise_for_status()
    return resp.json() or []