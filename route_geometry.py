import math
import numpy as np
from shapely.geometry import Point, LineString
from typing import List, Tuple, Dict, Any

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia Haversine en metros entre dos puntos geográficos.
    """
    R = 6371000.0  # Radio de la Tierra en metros
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c

def project_passenger_to_route(
    route_polyline: List[Tuple[float, float]], 
    passenger_location: Tuple[float, float],
    max_walk_distance_m: float = 500.0
) -> List[Dict[str, Any]]:
    """
    Proyecta la ubicación del pasajero sobre el vector de puntos (polilínea) de la ruta del conductor.
    
    :param route_polyline: Lista de tuplas (lat, lng) que representan la ruta preestablecida.
    :param passenger_location: Tupla (lat, lng) con la posición del pasajero.
    :param max_walk_distance_m: Radio máximo caminable aceptable para el pasajero (por defecto 500m).
    :return: Lista de puntos candidatos ordenados por menor distancia a pie.
    """
    if len(route_polyline) < 2:
        raise ValueError("La ruta del conductor debe contener al menos 2 puntos.")

    # Shapely trabaja en formato (longitude, latitude) -> (x, y)
    route_points_xy = [(lng, lat) for lat, lng in route_polyline]
    line = LineString(route_points_xy)
    passenger_point_xy = Point(passenger_location[1], passenger_location[0])

    candidates = []

    # Evaluar proyección sobre cada segmento de la polilínea
    for i in range(len(route_polyline) - 1):
        p1_xy = route_points_xy[i]
        p2_xy = route_points_xy[i+1]
        segment = LineString([p1_xy, p2_xy])

        # Proyección ortogonal del punto sobre el segmento actual
        projected_dist_ratio = segment.project(passenger_point_xy, normalized=True)
        projected_point_xy = segment.interpolate(projected_dist_ratio, normalized=True)

        proj_lat = projected_point_xy.y
        proj_lng = projected_point_xy.x

        # Calcular distancia exacta a pie (Haversine) desde la posición del pasajero al punto proyectado
        walk_distance_m = haversine_distance(
            passenger_location[0], passenger_location[1],
            proj_lat, proj_lng
        )

        # Filtrar solo si está dentro del rango de tolerancia peatonal
        if walk_distance_m <= max_walk_distance_m:
            candidates.append({
                "segment_index": i,
                "meeting_point": (round(proj_lat, 6), round(proj_lng, 6)),
                "walk_distance_m": round(walk_distance_m, 2),
                "driver_deviation_m": 0.0  # Cero desvío para el conductor
            })

    # Ordenar candidatos priorizando la menor distancia a pie para el pasajero
    candidates.sort(key=lambda x: x["walk_distance_m"])

    return candidates

# --- PRUEBA RÁPIDA DE FUNCIONAMIENTO ---
if __name__ == "__main__":
    # Ruta simulada del conductor (Trayecto hacia la UTR)
    driver_route = [
        (21.8818, -102.2916), # Punto A: Centro de Aguascalientes
        (21.8650, -102.2500), # Punto B: Salida a SLP
        (21.8480, -102.0150)  # Punto C: UTR El Retoño
    ]

    # Ubicación del pasajero (Cerca de la Salida a SLP)
    passenger_pos = (21.8660, -102.2510)

    sugerencias = project_passenger_to_route(driver_route, passenger_pos, max_walk_distance_m=600.0)
    
    print("--- RESULTADO DE PROYECCIÓN GEOMÉTRICA DE PRUEBA ---")
    for idx, sug in enumerate(sugerencias, 1):
        print(f"Opción {idx}: Punto Encuentro: {sug['meeting_point']} | Distancia a pie: {sug['walk_distance_m']} m | Desvío Conductor: {sug['driver_deviation_m']} m")