import pygame
import pygame_gui
import os
import random
import time
import math
from datetime import datetime
from station import Station
from ui import UIManager
from game_logic import alien_attack, player_defend
from ai import minimax, evaluate_station
pygame.init()

WIDTH, HEIGHT = 1200, 700
FPS = 60
GAME_DURATION = 300
MAX_AI_MEMORY = 3

#Fonst
pygame.init()
station_font = pygame.font.SysFont("arial", 28, bold=True) 
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Alien Defense - Strategic Stations")

layer_images = []
for i in range(1, 4):
    path = os.path.join("assets", f"layer_{i}.png")
    img = pygame.image.load(path).convert_alpha()
    img = pygame.transform.scale(img, (WIDTH, HEIGHT))
    layer_images.append(img)

station_img = pygame.transform.scale(pygame.image.load("assets/station_1.png"), (150, 150))
alien_img = pygame.transform.scale(pygame.image.load("assets/alien.png"), (35, 35))
military_img = pygame.transform.scale(pygame.image.load("assets/military_yellow.png"), (50, 50))
earth_base_img = pygame.transform.scale(pygame.image.load("assets/resource.png"), (200, 200))

earth_base_pos = (WIDTH - 215, 20)
earth_base = type('EarthBase', (), {'pos': earth_base_pos})()

ui = UIManager((WIDTH, HEIGHT))

def generate_station_positions(count, margin=180, forbidden_zones=None):
    if forbidden_zones is None:
        forbidden_zones = [
            pygame.Rect(20, 150, 180, 300), 
            pygame.Rect(WIDTH - 215, 20, 200, 200)
        ]

    positions = []
    max_attempts = 500

    while len(positions) < count and max_attempts > 0:
        x = random.randint(100, WIDTH - 200)
        y = random.randint(50, HEIGHT - 200)
        new_rect = pygame.Rect(x, y, 150, 150)

        too_close = any(math.sqrt((x - px)**2 + (y - py)**2) < margin for px, py in positions) or \
                    any(new_rect.colliderect(zone) for zone in forbidden_zones)

        if not too_close:
            positions.append((x, y))
        max_attempts -= 1

    return positions

station_count = random.randint(6, 9)
positions = generate_station_positions(
    station_count,
    margin=180,
    forbidden_zones=ui.get_forbidden_zones()
)

stations = []

for i, pos in enumerate(positions):
    name = f"Station {chr(65 + i)}"
    # When creating stations:
    population = random.randint(200, 500)
    military = random.randint(10, 50) if random.random() < 0.7 else random.randint(0, 10)
    aliens = random.randint(50, 70) if random.random() < 0.7 else random.randint(0, 5) #Graeter cuz we are already sending troops too
    stations.append(Station(name, pos, population, military, aliens))
    stations[-1].update_damage()

base_troops = 500

game_start_time = datetime.now()
game_over = False
player_won = None
last_ai_attacks = [] 
clock = pygame.time.Clock()
running = True

turn = "ai"
ai_attack_count = 0
selected_station = None
ai_delay_timer = 0
last_ai_attack_station = None

def check_game_over():
    global game_over, player_won
    
    if all(s.population <= 0 for s in stations):
        game_over = True
        player_won = False
        return True
    
    if all(s.alien_count <= 0 for s in stations):
        game_over = True
        player_won = True
        return True
    
    if base_troops <= 0 and all(s.military_population <= 0 for s in stations):
        game_over = True
        player_won = False
        return True
    
    time_elapsed = (datetime.now() - game_start_time).total_seconds()
    if time_elapsed >= GAME_DURATION:
        game_over = True
        total_humans = sum(s.population for s in stations)
        total_aliens = sum(s.alien_count for s in stations)
        original_pop = sum(s.original_population for s in stations)
    
        player_won = (total_humans > total_aliens * 3) or (total_aliens == 0)
        return True
    
    return False

def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def draw_station_connections():
    for station in stations:
        if station.alien_count > 0:
            pygame.draw.line(window, (255, 100, 100, 150), 
                           (station.pos[0] + 75, station.pos[1] + 75),
                           (earth_base_pos[0] + 100, earth_base_pos[1] + 100), 2)
            
def minor_alien_attack(station):
    if station.population > 0 and station.alien_count > 0:
        factor=random.uniform(0.1, 0.15)  # Light attack factor
        lost = int(factor * station.population)
        station.population -= lost

        # Update damage % based on population lost
        station.update_damage()
        
        damage = random.randint(1, 3)  # Very light damage
        station.population = max(0, station.population - damage)
        station.under_attack = True
        station.original_population = station.population
        # station.damage = damage
        # station.update_damage()
        return True
    return False

while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        ui.process_events(event)

        if event.type == pygame.MOUSEBUTTONDOWN and turn == "player" and not game_over:
            mx, my = pygame.mouse.get_pos()
            for station in stations:
                x, y, w, h = station.get_rect()
                if x <= mx <= x + w and y <= my <= y + h:
                    selected_station = station
                    ui.update_info({
                        'name': selected_station.name,
                        'under_attack': selected_station.under_attack,
                        'population': selected_station.population,
                        'military': selected_station.military_population,
                        'aliens': selected_station.alien_count,
                        'damage': selected_station.damage,
                        'distance': selected_station.distance_from_base
                    })
                    break

        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == ui.elements['send_button'] and turn == "player" and not game_over:
            if selected_station:
                try:
                    reinforcements = int(ui.elements['troop_input'].get_text())
                    if reinforcements > base_troops:
                        ui.update_status("Not enough troops at base.")
                    elif reinforcements <= 0:
                        ui.update_status("Enter a positive number of troops.")
                    else:
                        if player_defend(selected_station, reinforcements, earth_base):
                            base_troops -= reinforcements
                            ui.update_info({
                                'name': selected_station.name,
                                'under_attack': selected_station.under_attack,
                                'population': selected_station.population,
                                'military': selected_station.military_population,
                                'aliens': selected_station.alien_count,
                                'damage': selected_station.damage,
                                'distance': selected_station.distance_from_base
                            })
                            ui.update_status(f"Sent {reinforcements} troops to {selected_station.name}")
                            station_center = (
                                selected_station.pos[0] + Station.WIDTH//2,
                                selected_station.pos[1] + Station.HEIGHT//2
                            )
                            ui.add_bomb_effect(station_center)
                            
                            turn = "ai"
                            ai_delay_timer = time.time() + 1
                        # else:
                        #     ui.update_status("Defense failed - no aliens at station")
                except ValueError:
                    ui.update_status("Enter a valid number of troops.")

    ui.update(dt)


    # Update timer
    time_elapsed = (datetime.now() - game_start_time).total_seconds()
    time_remaining = max(0, GAME_DURATION - time_elapsed)
    ui.update_timer(int(time_remaining))

    if not game_over and check_game_over():
        if player_won:
            ui.update_status("VICTORY! You successfully defended Earth!")
        else:
            ui.update_status("DEFEAT! The aliens have overrun our stations!")
        continue

    # # AI Turn
    # if turn == "ai" and time.time() > ai_delay_timer and not game_over:
    #     # Reset attack flags
    #     for s in stations:
    #         s.under_attack = False
            
    #     # Get AI decision with memory of last attacks
    #     ai_station, _ = minimax(stations, 4, False, float('-inf'), float('inf'), earth_base, last_ai_attacks)
        
    #     if ai_station and ai_station.population > 0 and ai_station.alien_count > 0:
    #         if alien_attack(ai_station):
    #             # Record this attack for AI memory
    #             last_ai_attacks.append(ai_station)
    #             if len(last_ai_attacks) > MAX_AI_MEMORY:
    #                 last_ai_attacks.pop(0)
                
    #             # Update station info and status
    #             ui.update_info({
    #                 'name': ai_station.name,
    #                 'under_attack': ai_station.under_attack,
    #                 'population': ai_station.population,
    #                 'military': ai_station.military_population,
    #                 'aliens': ai_station.alien_count,
    #                 'damage': ai_station.damage,
    #                 'distance': ai_station.distance_from_base
    #             })
    #             ui.update_status(f"AI attacked {ai_station.name}")
    #             last_ai_attack_station = ai_station
    #             # ui.add_click_effect(ai_station.pos)  # Visual feedback for attack
    #             # Add bomb effect at the station's center
    #             station_center = (
    #                 ai_station.pos[0] + Station.WIDTH//2,
    #                 ai_station.pos[1] + Station.HEIGHT//2
    #             )
    #             ui.add_bomb_effect(station_center)
    #         else:
    #             ui.update_status("AI attack failed")
    #     else:
    #         ui.update_status("AI is regrouping forces")
        
    #     turn = "player"
    
    # if turn == "ai" and time.time() > ai_delay_timer and not game_over and ai_attack_count==0:
        
    #     # Reset attack flags
    #     for s in stations:
    #         s.under_attack = False

    #     # Get AI decision with memory of last attacks
    #     ai_station, _ = minimax(stations, 4, False, float('-inf'), float('inf'), earth_base, last_ai_attacks)

    #     # Find all valid attack targets
    #     valid_targets = [s for s in stations if s.population > 0 and s.alien_count > 0]

    #     # Fallback if minimax fails or gives invalid target
    #     if (not ai_station or
    #         ai_station.population <= 0 or
    #         ai_station.alien_count <= 0 or
    #         ai_station not in valid_targets):

    #         if len(valid_targets) == 1:
    #             ai_station = valid_targets[0]  # Only one valid target: must attack it
    #         elif len(valid_targets) > 1:
    #             ai_station = random.choice(valid_targets)  # Random fallback target
    #         else:
    #             ai_station = None  # No valid targets left

    #     if ai_station:
    #         if alien_attack(ai_station):
    #             # Record this attack for AI memory
    #             last_ai_attacks.append(ai_station)
    #             if len(last_ai_attacks) > MAX_AI_MEMORY:
    #                 last_ai_attacks.pop(0)

    #             # Update station info and status
    #             ui.update_info({
    #                 'name': ai_station.name,
    #                 'under_attack': ai_station.under_attack,
    #                 'population': ai_station.population,
    #                 'military': ai_station.military_population,
    #                 'aliens': ai_station.alien_count,
    #                 'damage': ai_station.damage,
    #                 'distance': ai_station.distance_from_base
    #             })
    #             ui.update_status(f"AI attacked {ai_station.name}")
    #             last_ai_attack_station = ai_station

    #             # Add bomb effect
    #             station_center = (
    #                 ai_station.pos[0] + Station.WIDTH // 2,
    #                 ai_station.pos[1] + Station.HEIGHT // 2
    #             )
    #             ui.add_bomb_effect(station_center)
    #         else:
    #             ui.update_status("AI attack failed")
    #     else:
    #         ui.update_status("AI is regrouping forces")

    #     turn = "player"
    
    if turn == "ai" and time.time() > ai_delay_timer and not game_over:
            
        if ai_attack_count == 0:
            for s in stations:
                if s.population > 0 and s.alien_count > 0:
                    if minor_alien_attack(s):
                        last_ai_attacks.append(s)
                        if len(last_ai_attacks) > MAX_AI_MEMORY:
                            last_ai_attacks.pop(0)
                        
                        ui.update_info({
                            'name': s.name,
                            'under_attack': s.under_attack,
                            'population': s.population,
                            'military': s.military_population,
                            'aliens': s.alien_count,
                            'damage': s.damage,
                            'distance': s.distance_from_base
                        })
                        ui.update_status(f"AI lightly attacked {s.name} (initial wave)")

                        station_center = (
                            s.pos[0] + Station.WIDTH // 2,
                            s.pos[1] + Station.HEIGHT // 2
                        )
                        ui.add_bomb_effect(station_center)
            
            ai_attack_count += 1
            turn = "player"
            
        else:
            for s in stations:
                s.under_attack = False

            ai_station, _ = minimax(stations, 4, False, float('-inf'), float('inf'), earth_base, last_ai_attacks)

            valid_targets = [s for s in stations if s.population > 0 and s.alien_count > 0]

            if (not ai_station or
                ai_station.population <= 0 or
                ai_station.alien_count <= 0 or
                ai_station not in valid_targets):

                if len(valid_targets) == 1:
                    ai_station = valid_targets[0]
                elif len(valid_targets) > 1:
                    ai_station = random.choice(valid_targets)
                else:
                    ai_station = None

            if ai_station:
                if alien_attack(ai_station):
                    last_ai_attacks.append(ai_station)
                    if len(last_ai_attacks) > MAX_AI_MEMORY:
                        last_ai_attacks.pop(0)

                    ui.update_info({
                        'name': ai_station.name,
                        'under_attack': ai_station.under_attack,
                        'population': ai_station.population,
                        'military': ai_station.military_population,
                        'aliens': ai_station.alien_count,
                        'damage': ai_station.damage,
                        'distance': ai_station.distance_from_base
                    })
                    ui.update_status(f"AI attacked {ai_station.name}")
                    last_ai_attack_station = ai_station

                    station_center = (
                        ai_station.pos[0] + Station.WIDTH // 2,
                        ai_station.pos[1] + Station.HEIGHT // 2
                    )
                    ui.add_bomb_effect(station_center)
                else:
                    ui.update_status("AI attack failed")
            else:
                ui.update_status("AI is regrouping forces")

            turn = "player"


    ui.update_base_resources(base_troops)

    suggested_station, _ = minimax(stations, 4, True, float('-inf'), float('inf'), earth_base, last_ai_attacks)
    if suggested_station:
        ui.update_ai_suggestion(suggested_station.name, evaluate_station(suggested_station, True, earth_base, last_ai_attacks), suggested_station.alien_count)

    for layer in layer_images:
        window.blit(layer, (0, 0))

    window.blit(earth_base_img, earth_base_pos)

    draw_station_connections()

    for station in stations:
        x, y = station.pos
        window.blit(station_img, (x, y))
        
        name_surface = station_font.render(station.name, True, (255, 255, 255))
        name_rect = name_surface.get_rect(center=(x + Station.WIDTH // 2, y - 20))
        window.blit(name_surface, name_rect)
        
        if station == last_ai_attack_station:
            pygame.draw.rect(window, (255, 0, 0, 150), (x, y, Station.WIDTH, 5))
        
        if station.alien_count > 0:
            window.blit(alien_img, (x + 30, y + 90))
        if station.military_population > 0:
            window.blit(military_img, (x + 70, y + 20))
        
        if station.damage > 0:
            damage_width = int(Station.WIDTH * (station.damage / 100))
            pygame.draw.rect(window, (255, 165, 0), (x, y + Station.HEIGHT - 10, damage_width, 5))
        
        pygame.draw.line(window, (100, 100, 255, 50),
                       (x + 75, y + 75),
                       (earth_base_pos[0] + 100, earth_base_pos[1] + 100), 1)

    if game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        window.blit(overlay, (0, 0))
        
        font = pygame.font.SysFont('Arial', 72)
        if player_won:
            text = font.render("VICTORY!", True, (0, 255, 0))
        else:
            text = font.render("DEFEAT", True, (255, 0, 0))
        
        text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2))
        window.blit(text, text_rect)

        font_sm = pygame.font.SysFont('Arial', 24)
        humans = sum(s.population for s in stations)
        aliens = sum(s.alien_count for s in stations)
        summary = font_sm.render(f"Humans: {humans} | Aliens: {aliens}", True, (255, 255, 255))
        window.blit(summary, (WIDTH//2 - 100, HEIGHT//2 + 50))

    ui.draw(window)
    ui.draw_effects(window) 
    pygame.display.flip()

pygame.quit()
print("Game closed.")