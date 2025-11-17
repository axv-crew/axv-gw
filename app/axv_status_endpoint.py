"""
[K4.1] AXV Status Endpoint - Single Source of Truth
====================================================

Endpoint: GET /axv/status

Zwraca ujednolicony status wszystkich komponentów AXV:
- api: stan samego axv_api
- gateway: stan axv_gw (healthz check)
- n8n: stan n8n workflow engine
- rag: stan Atlas EDGE RAG

Strategia overall_status:
- ok=true: wszystkie komponenty są "ok" lub "unknown"
- ok=false: jeśli którykolwiek komponent jest "down"
- Dla "degraded": ok=true, ale dodajemy overall_status="degraded"
  (pozwala to na alarm, ale nie full outage)

Timeout policy: 2s na każdy healthcheck (fail-fast)
"""

import time
import httpx
import logging
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

# ============================================================================
# Models
# ============================================================================

StatusValue = Literal["ok", "degraded", "down", "unknown"]

class NodeStatus(BaseModel):
    """Status pojedynczego node'a w klastrze AXV"""
    id: str
    role: str = Field(description="np. 'edge', 'compute', 'monitor'")
    host: Optional[str] = None
    ok: bool
    status: StatusValue
    age_s: int = Field(description="Wiek danych w sekundach (od ostatniego update)")
    last_seen: Optional[int] = Field(default=None, description="Unix timestamp ostatniego kontaktu")


class AXVStatusResponse(BaseModel):
    """Główny response /axv/status"""
    now: int = Field(description="Current unix timestamp")
    ok: bool = Field(description="True jeśli wszystkie komponenty OK lub unknown")
    version: str = Field(description="Wersja API")
    overall_status: Optional[StatusValue] = Field(
        default=None,
        description="Obecne gdy system jest degraded (ok=true ale z problemami)"
    )
    status: Dict[str, StatusValue] = Field(
        description="Status poszczególnych komponentów: api, gateway, n8n, rag"
    )
    nodes: List[NodeStatus] = Field(
        default_factory=list,
        description="Lista nodów klastra (z /axv/status/nodes)"
    )


# ============================================================================
# Health Check Functions
# ============================================================================

logger = logging.getLogger(__name__)

# Konfiguracja - w produkcji z env/config
GATEWAY_URL = "http://127.0.0.1:8000/axv/healthz"
N8N_HEALTHZ_URL = "http://n8n.axv.life/healthz"  # lub inne
HEALTHCHECK_TIMEOUT = 2.0  # seconds


async def check_api_health() -> StatusValue:
    """
    Sprawdza stan samego axv_api.
    
    Możliwe rozszerzenia:
    - Ping do bazy danych
    - Sprawdzenie core dependencies
    - Weryfikacja filesystem/storage
    
    Returns:
        "ok" jeśli API działa poprawnie
    """
    # TODO: Dodaj sprawdzenie DB connection pool
    # TODO: Weryfikuj dostęp do critical resources
    
    try:
        # Placeholder - w rzeczywistości sprawdź DB lub inne zależności
        # Przykład: await db.execute("SELECT 1")
        return "ok"
    except Exception as e:
        logger.error(f"API health check failed: {e}")
        return "degraded"


async def check_gateway_health() -> StatusValue:
    """
    Sprawdza stan axv_gw poprzez HTTP healthz endpoint.
    
    Returns:
        "ok": gateway odpowiada poprawnie
        "degraded": gateway odpowiada z błędami lub wolno
        "down": gateway nie odpowiada
        "unknown": brak konfiguracji endpointu
    """
    if not GATEWAY_URL:
        return "unknown"
    
    try:
        async with httpx.AsyncClient(timeout=HEALTHCHECK_TIMEOUT) as client:
            response = await client.get(GATEWAY_URL)
            
            if response.status_code == 200:
                return "ok"
            elif response.status_code >= 500:
                return "down"
            else:
                return "degraded"
                
    except httpx.TimeoutException:
        logger.warning(f"Gateway health check timeout ({HEALTHCHECK_TIMEOUT}s)")
        return "degraded"
    except httpx.ConnectError:
        logger.error("Gateway health check failed: connection error")
        return "down"
    except Exception as e:
        logger.error(f"Gateway health check failed: {e}")
        return "degraded"


async def check_n8n_health() -> StatusValue:
    """
    Sprawdza stan n8n workflow engine.
    
    Note: Jeśli n8n nie ma endpointu /healthz, można:
    - Pingować główną stronę n8n
    - Sprawdzić dostępność webhook endpoint
    - Na razie zwrócić "unknown"
    
    Returns:
        Status n8n instance
    """
    if not N8N_HEALTHZ_URL:
        return "unknown"
    
    try:
        async with httpx.AsyncClient(timeout=HEALTHCHECK_TIMEOUT) as client:
            response = await client.get(N8N_HEALTHZ_URL)
            
            if response.status_code == 200:
                return "ok"
            elif response.status_code >= 500:
                return "down"
            else:
                return "degraded"
                
    except httpx.TimeoutException:
        logger.warning(f"n8n health check timeout ({HEALTHCHECK_TIMEOUT}s)")
        return "degraded"
    except httpx.ConnectError:
        logger.error("n8n health check failed: connection error")
        return "down"
    except Exception as e:
        logger.error(f"n8n health check failed: {e}")
        # Na razie n8n może nie mieć /healthz - graceful degradation
        return "unknown"


async def check_rag_health() -> StatusValue:
    """
    Sprawdza stan RAG (Atlas EDGE).
    
    TODO: Zaimplementować po ustawieniu RAG healthz endpoint
    
    Returns:
        "unknown" - stub, do implementacji
    """
    # TODO: Implement RAG health check
    # - Sprawdź dostępność Atlas EDGE
    # - Zweryfikuj connection do vector store
    # - Opcjonalnie: test query
    return "unknown"


async def get_nodes_status() -> List[NodeStatus]:
    """
    Pobiera status nodów z istniejącej logiki /axv/status/nodes.
    
    Integration point: Ta funkcja powinna wykorzystać
    istniejącą logikę z /axv/status/nodes aby uniknąć duplikacji.
    
    TODO: Zintegrować z rzeczywistą implementacją nodes tracking
    
    Returns:
        Lista NodeStatus objects
    """
    # TODO: Import i użyj istniejącej logiki z /axv/status/nodes
    # Przykład integracji:
    # from .nodes import get_all_nodes
    # nodes_data = await get_all_nodes()
    # return [NodeStatus(**node) for node in nodes_data]
    
    # Placeholder - zwróć pustą listę lub przykładowe dane
    # W produkcji: pobierz z Redis/DB/memory store
    return []


def calculate_overall_status(
    status_dict: Dict[str, StatusValue]
) -> tuple[bool, Optional[StatusValue]]:
    """
    Oblicza overall status na podstawie statusów komponentów.
    
    Strategia:
    1. Jeśli którykolwiek komponent jest "down" → ok=False, overall=None
    2. Jeśli którykolwiek jest "degraded" → ok=True, overall="degraded"
    3. Jeśli wszystkie są "ok" lub "unknown" → ok=True, overall=None
    
    Args:
        status_dict: Słownik {component: status}
    
    Returns:
        (ok: bool, overall_status: Optional[StatusValue])
    """
    statuses = list(status_dict.values())
    
    # Check for critical failures
    if "down" in statuses:
        return False, None
    
    # Check for degraded services
    if "degraded" in statuses:
        return True, "degraded"
    
    # All ok or unknown
    return True, None


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/axv", tags=["status"])


@router.get("/status", response_model=AXVStatusResponse)
async def get_axv_status(
    # Możesz dodać opcjonalne parametry, np:
    # include_nodes: bool = True,
    # verbose: bool = False
):
    """
    **[K4.1] Single Source of Truth dla stanu AXV**
    
    Zwraca skonsolidowany status wszystkich komponentów systemu AXV:
    
    - **api**: Stan axv_api (ten serwis)
    - **gateway**: Stan axv_gw (reverse proxy/router)
    - **n8n**: Stan n8n workflow engine
    - **rag**: Stan Atlas EDGE RAG system
    
    ### Status Values:
    - `ok`: Komponent działa poprawnie
    - `degraded`: Komponent działa, ale z problemami
    - `down`: Komponent nie odpowiada
    - `unknown`: Brak informacji o komponencie
    
    ### Overall Status Logic:
    - `ok=true`: Wszystkie komponenty są "ok" lub "unknown"
    - `ok=false`: Którykolwiek komponent jest "down"
    - `ok=true` + `overall_status="degraded"`: System działa, ale z problemami
    
    Ten endpoint jest zaprojektowany do częstego odpytywania (co 15-60s)
    przez monitoring, status page i Grafanę.
    """
    now = int(time.time())
    
    # Parallel health checks dla lepszej performance
    import asyncio
    
    api_status_task = check_api_health()
    gateway_status_task = check_gateway_health()
    n8n_status_task = check_n8n_health()
    rag_status_task = check_rag_health()
    nodes_status_task = get_nodes_status()
    
    # Await all checks concurrently
    api_status, gateway_status, n8n_status, rag_status, nodes = await asyncio.gather(
        api_status_task,
        gateway_status_task,
        n8n_status_task,
        rag_status_task,
        nodes_status_task,
        return_exceptions=True  # Don't fail if one check raises
    )
    
    # Handle potential exceptions from gather
    if isinstance(api_status, Exception):
        logger.error(f"API health check exception: {api_status}")
        api_status = "degraded"
    if isinstance(gateway_status, Exception):
        logger.error(f"Gateway health check exception: {gateway_status}")
        gateway_status = "degraded"
    if isinstance(n8n_status, Exception):
        logger.error(f"n8n health check exception: {n8n_status}")
        n8n_status = "unknown"
    if isinstance(rag_status, Exception):
        logger.error(f"RAG health check exception: {rag_status}")
        rag_status = "unknown"
    if isinstance(nodes, Exception):
        logger.error(f"Nodes status exception: {nodes}")
        nodes = []
    
    # Build status dict
    status_dict = {
        "api": api_status,
        "gateway": gateway_status,
        "n8n": n8n_status,
        "rag": rag_status,
    }
    
    # Calculate overall status
    ok, overall_status = calculate_overall_status(status_dict)
    
    # Get version from config/env
    # TODO: Import from actual config
    version = "0.1.9"  # Placeholder
    
    return AXVStatusResponse(
        now=now,
        ok=ok,
        version=version,
        overall_status=overall_status,
        status=status_dict,
        nodes=nodes,
    )


# ============================================================================
# Configuration Helper (dla main.py)
# ============================================================================

def configure_status_endpoint(app, config: dict):
    """
    Helper do konfiguracji endpointu status w main.py
    
    Usage:
        from axv_status_endpoint import router as status_router, configure_status_endpoint
        
        # Load config
        config = load_config()
        
        # Configure globals
        configure_status_endpoint(app, config)
        
        # Include router
        app.include_router(status_router)
    
    Args:
        app: FastAPI app instance
        config: Dict z konfiguracją (gateway_url, n8n_url, etc.)
    """
    global GATEWAY_URL, N8N_HEALTHZ_URL, HEALTHCHECK_TIMEOUT
    
    GATEWAY_URL = config.get("gateway_healthz_url", GATEWAY_URL)
    N8N_HEALTHZ_URL = config.get("n8n_healthz_url", N8N_HEALTHZ_URL)
    HEALTHCHECK_TIMEOUT = config.get("healthcheck_timeout", HEALTHCHECK_TIMEOUT)
    
    logger.info(f"Status endpoint configured: gateway={GATEWAY_URL}, n8n={N8N_HEALTHZ_URL}")
