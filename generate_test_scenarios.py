import json
import random
from typing import List, Dict, Any

def generate_20_scenarios() -> List[Dict[str, Any]]:
    """
    Genera un conjunto de datos sintéticos con 20 escenarios de prueba geoespaciales
    orientados a trayectos hacia la Universidad Tecnológica El Retoño (UTR), Aguascalientes.
    """
    # Coordenadas clave en la zona metropolitana de Aguascalientes y UTR
    UTR_CAMPUS = (21.8480, -102.0150)
    CENTRO_AGS = (21.8818, -102.2916)
    SALIDA_SLP = (21.8650, -102.2500)
    OJOCALIENTE = (21.8750, -102.2300)
    EL_LLANO = (21.8500, -102.0800)

    # Definición de 4 rutas fijas base representativas para los conductores
    base_routes = {
        "Ruta_1_Centro_UTR": [CENTRO_AGS, SALIDA_SLP, OJOCALIENTE, EL_LLANO, UTR_CAMPUS],
        "Ruta_2_Sur_UTR": [(21.8300, -102.2800), (21.8450, -102.2000), EL_LLANO, UTR_CAMPUS],
        "Ruta_3_Norte_UTR": [(21.9200, -102.2900), (21.8900, -102.2400), OJOCALIENTE, UTR_CAMPUS],
        "Ruta_4_Directa_SLP": [SALIDA_SLP, (21.8600, -102.1500), EL_LLANO, UTR_CAMPUS]
    }

    scenarios = []

    # Configuración controlada de los 20 escenarios de prueba
    scenario_configs = [
        # (ID, Ruta base, Offset aprox en lat/lng para la posición del pasajero, Descripción/Tipo de Caso)
        (1, "Ruta_1_Centro_UTR", 0.0005, 0.0005, "Pasajero muy cercano a inicio de ruta (~75m)"),
        (2, "Ruta_1_Centro_UTR", 0.0012, 0.0010, "Pasajero a distancia caminable media (~160m)"),
        (3, "Ruta_1_Centro_UTR", 0.0035, 0.0030, "Pasajero cerca del límite tolerable (~480m)"),
        (4, "Ruta_1_Centro_UTR", 0.0080, 0.0070, "Caso Fuera de Rango (>900m) - Debe dar 0 resultados"),
        
        (5, "Ruta_2_Sur_UTR", 0.0003, -0.0004, "Pasajero cercano en zona sur (~60m)"),
        (6, "Ruta_2_Sur_UTR", 0.0018, -0.0015, "Pasajero a distancia caminable media (~240m)"),
        (7, "Ruta_2_Sur_UTR", 0.0032, -0.0028, "Pasajero en límite de tolerancia (~430m)"),
        (8, "Ruta_2_Sur_UTR", 0.0090, -0.0080, "Caso Fuera de Rango (>1km) - Debe dar 0 resultados"),
        
        (9, "Ruta_3_Norte_UTR", -0.0004, 0.0006, "Pasajero cercano en zona norte (~80m)"),
        (10, "Ruta_3_Norte_UTR", -0.0015, 0.0012, "Pasajero caminata moderada (~200m)"),
        (11, "Ruta_3_Norte_UTR", -0.0036, 0.0031, "Pasajero cerca del umbral máximo (~490m)"),
        (12, "Ruta_3_Norte_UTR", -0.0075, 0.0065, "Caso Fuera de Rango (>850m) - Debe dar 0 resultados"),

        (13, "Ruta_4_Directa_SLP", 0.0002, 0.0003, "Pasajero sobre tramo carretera directo (~35m)"),
        (14, "Ruta_4_Directa_SLP", 0.0010, 0.0008, "Pasajero cerca de nodo Salida a SLP (~130m)"),
        (15, "Ruta_4_Directa_SLP", 0.0025, 0.0020, "Pasajero en intersección a El Llano (~320m)"),
        (16, "Ruta_4_Directa_SLP", 0.0038, 0.0035, "Pasajero en borde de carretera (~500m)"),
        
        # Escenarios especiales/borde adicionales
        (17, "Ruta_1_Centro_UTR", 0.0000, 0.0000, "Caso Ideal: Pasajero exactamente sobre la ruta (0m)"),
        (18, "Ruta_2_Sur_UTR", 0.0001, -0.0001, "Pasajero casi exacto sobre tramo (~15m)"),
        (19, "Ruta_3_Norte_UTR", 0.0039, 0.0039, "Pasajero justo en el umbral de corte de 500m"),
        (20, "Ruta_4_Directa_SLP", 0.0120, 0.0100, "Caso Extremo Fuera de Rango (>1.5km)")
    ]

    for id_esc, route_key, lat_offset, lng_offset, desc in scenario_configs:
        route_poly = base_routes[route_key]
        
        # Tomar un punto de referencia intermedio de la ruta para aplicar el offset del pasajero
        ref_lat, ref_lng = route_poly[len(route_poly) // 2]
        passenger_lat = round(ref_lat + lat_offset, 6)
        passenger_lng = round(ref_lng + lng_offset, 6)

        scenario = {
            "scenario_id": id_esc,
            "description": desc,
            "route_name": route_key,
            "driver_polyline": route_poly,
            "passenger_location": [passenger_lat, passenger_lng],
            "max_walk_tolerance_m": 500.0
        }
        scenarios.append(scenario)

    return scenarios

if __name__ == "__main__":
    test_scenarios = generate_20_scenarios()
    
    # Guardar en archivo JSON para uso en pruebas y evaluación
    output_filename = "scenarios_dataset.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(test_scenarios, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Se generaron exitosamente los {len(test_scenarios)} escenarios de prueba en '{output_filename}'.")