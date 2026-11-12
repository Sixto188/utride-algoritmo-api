import time
from typing import List, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from route_geometry import project_passenger_to_route
from ranking_engine import rank_meeting_points

app = FastAPI(
    title="API de Sugerencia de Puntos de Encuentro - UTRide",
    description="Microservicio geoespacial para la recomendación de puntos de abordaje óptimos sobre la ruta del conductor.",
    version="1.0.0"
)

# --- ESQUEMAS DE ENTRADA Y SALIDA (Pydantic) ---

class RouteRequest(BaseModel):
    driver_polyline: List[Tuple[float, float]] = Field(
        ..., 
        description="Vector de coordenadas [(lat, lng), ...] de la ruta fija del conductor.",
        example=[(21.8818, -102.2916), (21.8650, -102.2500), (21.8480, -102.0150)]
    )
    passenger_location: Tuple[float, float] = Field(
        ..., 
        description="Coordenada (lat, lng) del origen del pasajero.",
        example=(21.8660, -102.2510)
    )
    max_walk_tolerance_m: float = Field(
        default=500.0, 
        ge=50.0, 
        le=2000.0,
        description="Distancia máxima a pie tolerable en metros."
    )
    top_n: int = Field(
        default=3, 
        ge=1, 
        le=10,
        description="Cantidad máxima de recomendaciones a devolver."
    )


class MeetingPoint(BaseModel):
    latitude: float
    longitude: float


class Recommendation(BaseModel):
    rank: int
    meeting_point: MeetingPoint
    walk_distance_m: float
    driver_deviation_m: float
    segment_index: int
    match_score_pct: float


class RouteResponse(BaseModel):
    status: str
    execution_time_ms: float
    recommendations_count: int
    recommendations: List[Recommendation]


# --- ENDPOINTS ---

@app.get("/")
def root_status():
    return {
        "service": "Motor Geoespacial UTRide",
        "status": "Online",
        "version": "1.0.0"
    }


@app.post("/api/v1/recommend-meeting-points", response_model=RouteResponse)
def recommend_meeting_points(payload: RouteRequest):
    start_time = time.time()
    
    if len(payload.driver_polyline) < 2:
        raise HTTPException(
            status_code=400, 
            detail="La ruta del conductor debe contener al menos 2 puntos de coordenadas."
        )

    try:
        # 1. Proyección ortogonal geométrica
        raw_candidates = project_passenger_to_route(
            route_polyline=payload.driver_polyline,
            passenger_location=payload.passenger_location,
            max_walk_distance_m=payload.max_walk_tolerance_m
        )

        # 2. Ranking multicriterio y evaluación de Scores
        top_recommendations = rank_meeting_points(
            raw_candidates=raw_candidates,
            max_tolerance_m=payload.max_walk_tolerance_m,
            top_n=payload.top_n
        )

        execution_time_ms = round((time.time() - start_time) * 1000, 3)

        return RouteResponse(
            status="success",
            execution_time_ms=execution_time_ms,
            recommendations_count=len(top_recommendations),
            recommendations=top_recommendations
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en procesamiento geoespacial: {str(e)}")