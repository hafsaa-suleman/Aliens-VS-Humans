import pygame
import pygame_gui
from typing import Dict, Tuple, Any

class UIManager:
    def __init__(self, window_size: Tuple[int, int]):
        self.manager = pygame_gui.UIManager(window_size)
        self.elements = {}
        self.window_size = window_size
        self.forbidden_zones = []
        self.setup_ui()

    def setup_ui(self):
        self.elements['info_panel'] = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect((20, 150), (180, 300)),
            html_text="<b>Station Info</b><br>Click a station",
            manager=self.manager
        )
        
        self.elements['status_panel'] = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect((20, 470), (250, 100)),
            html_text="Player's Turn<br>Select a station to defend",
            manager=self.manager
        )
        
        right_x = self.window_size[0] - 250
        self.elements['base_status'] = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect((right_x, 320), (230, 100)),
            html_text="Base Resources:<br>Troops: 2000",
            manager=self.manager
        )
        
        self.elements['ai_suggestion'] = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect((right_x, 440), (230, 100)),
            html_text="AI Suggestion:<br>None",
            manager=self.manager
        )
        
        self.elements['timer_panel'] = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect((right_x, 220), (230, 80)),
            html_text="Time Remaining: 05:00",
            manager=self.manager
        )
        
        self.elements['troop_input'] = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((right_x, 550), (100, 30)),
            manager=self.manager
        )
        self.elements['troop_input'].set_text("0")
        
        self.elements['send_button'] = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((right_x + 110, 550), (120, 30)),
            text="Send Troops",
            manager=self.manager
        )

        self.forbidden_zones = [
            elem.rect for elem in self.elements.values() 
            if hasattr(elem, 'rect')
        ]
        self.forbidden_zones.append(pygame.Rect(
            self.window_size[0] - 215, 20, 200, 200
        ))

    def update_info(self, station_data: Dict[str, Any]):
        html = f"""
<b>{station_data['name']}</b>
<b>Status:</b> {'Under Attack' if station_data['under_attack'] else 'Secure'}
<b>Population:</b> {station_data['population']}
<b>Military:</b> {station_data['military']}
<b>Aliens:</b> {station_data['aliens']}
<b>Damage:</b> {station_data['damage']}%
<b>Distance:</b> {station_data['distance']}px
        """
        self.elements['info_panel'].set_text(html)

    def update_status(self, text: str):
        self.elements['status_panel'].set_text(text)

    def update_base_resources(self, troops: int):
        self.elements['base_status'].set_text(f"Base Resources:<br>Troops: {troops}")

    def update_ai_suggestion(self, station_name: str, score: float = None,station_aliens: int = None):
        
        if(station_aliens > 0):
            text = f"AI Suggestion:<br>Defend {station_name}"
            if score is not None:
                text += f"<br>Priority: {score:.1f}"
            self.elements['ai_suggestion'].set_text(text)

    def update_timer(self, seconds: int):
        mins = seconds // 60
        secs = seconds % 60
        self.elements['timer_panel'].set_text(f"Time Remaining: {mins:02d}:{secs:02d}")

    def get_forbidden_zones(self) -> list:
        return self.forbidden_zones.copy()

    def process_events(self, event):
        self.manager.process_events(event)

    def update(self, time_delta: float):
        self.manager.update(time_delta)

    def draw(self, surface):
        self.manager.draw_ui(surface)

    def add_click_effect(self, position: Tuple[int, int]):
        effect = {
            'position': position,
            'time': 0,
            'max_time': 0.5
        }
        if not hasattr(self, 'click_effects'):
            self.click_effects = []
        self.click_effects.append(effect)
        
    def add_bomb_effect(self, position: Tuple[int, int]):
        bomb_effect = {
            'position': position,
            'time': 0,
            'max_time': 1.0,
            'pulses': [
                {'radius': 10, 'alpha': 255, 'delay': 0.0, 'color': (255, 50, 50)},
                {'radius': 20, 'alpha': 200, 'delay': 0.2, 'color': (255, 100, 100)},
                {'radius': 30, 'alpha': 150, 'delay': 0.4, 'color': (255, 150, 150)}
            ]
        }
        if not hasattr(self, 'bomb_effects'):
            self.bomb_effects = []
        self.bomb_effects.append(bomb_effect)


    def draw_effects(self, surface):
        if hasattr(self, 'click_effects'):
            for effect in self.click_effects[:]:
                progress = effect['time'] / effect['max_time']
                radius = int(30 * (1 - progress))
                alpha = int(200 * (1 - progress))
                
                s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (255, 255, 0, alpha), (radius, radius), radius)
                surface.blit(s, (
                    effect['position'][0] - radius,
                    effect['position'][1] - radius
                ))
                
                effect['time'] += 0.016
                if effect['time'] >= effect['max_time']:
                    self.click_effects.remove(effect)
                    
        if hasattr(self, 'bomb_effects'):
            for effect in self.bomb_effects[:]:
                effect['time'] += 0.016 
                
                for pulse in effect['pulses']:
                    if effect['time'] >= pulse['delay']:
                        pulse_progress = min(1.0, (effect['time'] - pulse['delay']) / 0.4)
                        radius = int(pulse['radius'] * (1 + pulse_progress * 2))
                        alpha = int(pulse['alpha'] * (1 - pulse_progress))
                        
                        s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                        pygame.draw.circle(
                            s, 
                            (*pulse['color'], alpha), 
                            (radius, radius), 
                            radius
                        )
                        surface.blit(s, (
                            effect['position'][0] - radius,
                            effect['position'][1] - radius
                        ))
                
                if effect['time'] >= effect['max_time']:
                    self.bomb_effects.remove(effect)