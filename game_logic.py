import random
import math

# Combat multipliers
ALIEN_STRENGTH = 1.5
MILITARY_STRENGTH = 1.0  
CIVILIAN_STRENGTH = 0.2
DISTANCE_PENALTY = 2500

# Population limits
MAX_POPULATION = 1000
MIN_POPULATION = 0
MAX_MILITARY = 100
MAX_ALIENS = 200

# higher the defender-to-attacker ratio, the higher the result
def calculate_combat_strength(attackers, defenders, has_military=True):
    if has_military:
        ratio = (defenders * MILITARY_STRENGTH) / (attackers + 1)
    else:
        ratio = (defenders * CIVILIAN_STRENGTH) / (attackers + 1)
    return 1 - math.exp(-ratio) 

def alien_attack(station):
    if station.alien_count <= 0:
        return False

    station.under_attack = True
    aliens = station.alien_count
    military = station.military_population
    civilians = station.population

    if military > 0:
        combat_strength = calculate_combat_strength(aliens, military)
        
        if random.random() < combat_strength:
            station.alien_count = 0
            station.military_population = max(0, int(military * random.uniform(0.6, 0.8)))
            station.population = max(0, int(civilians * random.uniform(0.85, 0.95)))
        else:
            station.military_population = 0
            station.alien_count = max(0, int(aliens * random.uniform(0.5, 0.7)))
            station.population = max(0, int(civilians * random.uniform(0.4, 0.6)))
    else:
        resistance_strength = calculate_combat_strength(aliens, civilians, False)
        
        if random.random() < resistance_strength * 0.3:
            station.alien_count = 0
            station.population = max(0, int(civilians * random.uniform(0.2, 0.4)))
        else:
            station.population = 0

    station.update_damage()
    return True

def player_defend(station, reinforcements, base_station):
    if reinforcements <= 0 or station.alien_count <= 0:
        return False

    distance = math.sqrt((station.pos[0]-base_station.pos[0])**2 + 
                        (station.pos[1]-base_station.pos[1])**2)
    distance_factor = max(0.4, 1 - (distance / DISTANCE_PENALTY))
    
    effective_reinforcements = min(MAX_MILITARY, 
                                 int(reinforcements * distance_factor))
    total_military = min(MAX_MILITARY,
                        station.military_population + effective_reinforcements)
    
    combat_strength = calculate_combat_strength(station.alien_count, total_military)

    if random.random() < combat_strength * 1.1:
        station.alien_count = 0
        station.military_population = min(MAX_MILITARY,
                                        max(0,
                                        int(total_military * random.uniform(0.7, 0.9))))
        station.population = min(MAX_POPULATION,
                               max(MIN_POPULATION,
                               int(station.population * random.uniform(1.05, 1.15))))
    else:
        station.alien_count = min(MAX_ALIENS,
                                 max(0,
                                 int(station.alien_count * random.uniform(0.3, 0.5))))
        station.military_population = min(MAX_MILITARY,
                                        max(0,
                                        int(total_military * random.uniform(0.5, 0.7))))
        station.population = min(MAX_POPULATION,
                               max(MIN_POPULATION,
                               int(station.population * random.uniform(0.8, 0.9))))

    station.update_damage()
    return True