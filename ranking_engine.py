from typing import List, Dict, Any

def calculate_match_score(walk_distance_m: float, max_tolerance_m: float = 500.0) -> float:
    """
    Calcula una puntuación de compatibilidad (Score 0 - 100%) en función de la distancia a pie.
    
    - 0 metros de caminata -> Score 100%
    - Distancia igual al límite de tolerancia -> Score 0%
    """
    if walk_distance_m >= max_tolerance_m:
        return 0.0
    
    # Función lineal inversa de score
    score = (1.0 - (walk_distance_m / max_tolerance_m)) * 100.0
    return round(score, 2)


def rank_meeting_points(
    raw_candidates: List[Dict[str, Any]], 
    max_tolerance_m: float = 500.0,
    top_n: int = 3
) -> List[Dict[str, Any]]:
    """
    Filtra, pondera y ordena los candidatos a puntos de encuentro.
    
    :param raw_candidates: Lista de candidatos generados por la proyección geométrica.
    :param max_tolerance_m: Radio máximo caminable.
    :param top_n: Número máximo de sugerencias a devolver (por defecto 3).
    :return: Lista de las mejores N sugerencias con su Score de viabilidad.
    """
    ranked_results = []

    for cand in raw_candidates:
        walk_dist = cand["walk_distance_m"]
        
        # Omitir cualquier punto fuera de tolerancia
        if walk_dist > max_tolerance_m:
            continue
            
        score = calculate_match_score(walk_dist, max_tolerance_m)
        
        ranked_item = {
            "rank": 0,  # Se asigna al ordenar
            "meeting_point": {
                "latitude": cand["meeting_point"][0],
                "longitude": cand["meeting_point"][1]
            },
            "walk_distance_m": walk_dist,
            "driver_deviation_m": cand["driver_deviation_m"],
            "segment_index": cand["segment_index"],
            "match_score_pct": score
        }
        ranked_results.append(ranked_item)

    # Ordenar por mayor Score de compatibilidad (y en caso de empate por menor distancia caminable)
    ranked_results.sort(key=lambda x: (-x["match_score_pct"], x["walk_distance_m"]))

    # Limitar al TOP N asignando posiciones de ranking
    final_top_list = ranked_results[:top_n]
    for idx, item in enumerate(final_top_list, 1):
        item["rank"] = idx

    return final_top_list


# --- PRUEBA INDEPENDIENTE DEL MOTOR DE RANKING ---
if __name__ == "__main__":
    candidates_sample = [
        {"segment_index": 0, "meeting_point": (21.8655, -102.2505), "walk_distance_m": 250.0, "driver_deviation_m": 0.0},
        {"segment_index": 1, "meeting_point": (21.8651, -102.2501), "walk_distance_m": 45.0,  "driver_deviation_m": 0.0},
        {"segment_index": 2, "meeting_point": (21.8640, -102.2490), "walk_distance_m": 480.0, "driver_deviation_m": 0.0},
        {"segment_index": 3, "meeting_point": (21.8600, -102.2400), "walk_distance_m": 620.0, "driver_deviation_m": 0.0}
    ]

    ranked = rank_meeting_points(candidates_sample, max_tolerance_m=500.0, top_n=3)

    print("--- PRUEBA DEL MOTOR DE RANKING MULTICRITERIO ---")
    for r in ranked:
        print(f"Top #{r['rank']} | Score: {r['match_score_pct']}% | Lat/Lng: ({r['meeting_point']['latitude']}, {r['meeting_point']['longitude']}) | Caminata: {r['walk_distance_m']} m")