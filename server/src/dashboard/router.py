"""
Dashboard Router - HTTP only (NUMA-113 P4, PLAN 2.1).

Aggregation lives in `DashboardService`; this module parses the request,
delegates, and maps the result to the cached JSON response.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..auth.dependencies import get_current_user
from .service import DashboardService, dashboard_service

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

CACHE_HEADERS = {"Cache-Control": "private, max-age=30"}


def get_dashboard_service() -> DashboardService:
    return dashboard_service


@router.get("/stats")
def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    return JSONResponse(content=service.get_stats(user_id), headers=CACHE_HEADERS)
