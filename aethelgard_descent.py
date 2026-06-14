#!/usr/bin/env python3
"""
AETHELGARD'S DESCENT – COMPLETE EDITION v4.6
- Fixed shopkeeper buy/sell and quests
- Added missing methods for NPC interactions
- Main Menu button now returns to main menu instead of quitting
- All UI methods fully implemented
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import json
import random
import os
import traceback
import sys

try:
    import requests
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ============================== CONSTANTS ==============================
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
MAP_WIDTH = 40
MAP_HEIGHT = 30
MAX_LEVEL = 20
COLORS = {
    "bg_dark": "#1e1e2e", "bg_light": "#2a2a3a", "text": "#c0c0c0",
    "highlight": "#6c91ff", "health": "#ff6b6b", "mana": "#6bffc4",
    "gold": "#ffd966", "heat": "#ff8c00", "grey": "#888888",
    "green": "#55aa55", "blue": "#5588ff", "purple": "#aa55ff",
    "gold_rare": "#ffaa33", "brown": "#8B4513", "cyan": "#00FFFF",
    "orange": "#FFA500", "red": "#FF0000",
    "visited_cleared": "#4a6e8c", "visited_not_cleared": "#8c4a4a",
    "unvisited": "#2a2a3a", "boss": "#8b0000", "treasure": "#daa520",
    "shop": "#2e8b57", "current": "#6c91ff"
}
RARITY_COLOR = {"Basic": "grey", "Enchanted": "green", "Rare": "blue", "Epic": "purple", "Artifact": "gold_rare"}
ICONS = {
    "normal": "⬜", "boss": "👑", "treasure": "💰", "shop": "🏪",
    "monster": "👾", "door": "🚪", "chest": "🎁", "unknown": "❓",
    "current": "🧙", "cleared": "✓"
}

# ============================== SETTINGS MANAGER ==============================
class Settings:
    SETTINGS_FILE = "game_settings.json"
    def __init__(self):
        self.use_ollama = False
        self.ollama_model = "llama3.2:3b"
        self.ollama_timeout = 3
        self.load()
    def load(self):
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.use_ollama = data.get("use_ollama", False)
                    self.ollama_model = data.get("ollama_model", "llama3.2:3b")
                    self.ollama_timeout = data.get("ollama_timeout", 3)
            except: pass
    def save(self):
        try:
            with open(self.SETTINGS_FILE, "w") as f:
                json.dump({"use_ollama": self.use_ollama, "ollama_model": self.ollama_model, "ollama_timeout": self.ollama_timeout}, f, indent=2)
        except: pass

# ============================== PRESET STORIES ==============================
PRESET_STORIES = {
    "enter_room": ["You step into a dusty chamber...", "The air grows cold..."],
    "combat_start": ["A {monster} lunges at you!"],
    "defeat_monster": ["The {monster} collapses."],
    "boss_defeated": ["The {boss} screams as it falls!"],
    "treasure": ["You find {gold} gold and a {item}!"],
    "trap": ["You trigger a trap! {damage} damage."],
    "flee_success": ["You manage to escape."],
    "flee_fail": ["The monster blocks your escape!"],
    "loot_item": ["You find a {item}!"]
}

# ============================== STORY GENERATOR ==============================
class StoryGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ollama_url = "http://localhost:11434/api/generate"
    def _call_ollama(self, prompt: str) -> str:
        if not self.settings.use_ollama or not OLLAMA_AVAILABLE:
            return None
        try:
            response = requests.post(self.ollama_url, json={"model": self.settings.ollama_model, "prompt": prompt, "stream": False, "options": {"num_ctx": 256}}, timeout=self.settings.ollama_timeout)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except: pass
        return None
    def get_story(self, category: str, **kwargs) -> str:
        if not self.settings.use_ollama:
            return self._get_preset(category, **kwargs)
        prompt = self._build_prompt(category, kwargs)
        story = self._call_ollama(prompt)
        if story:
            return story
        return self._get_preset(category, **kwargs)
    def get_flee_result(self, success: bool) -> str:
        if success:
            return random.choice(PRESET_STORIES["flee_success"])
        else:
            return random.choice(PRESET_STORIES["flee_fail"])
    def get_loot_story(self, item_name: str) -> str:
        return random.choice(PRESET_STORIES["loot_item"]).format(item=item_name)
    def get_lore(self, subject: str) -> str:
        if self.settings.use_ollama:
            prompt = f"Write one sentence of dark fantasy lore about a {subject} in a cursed dungeon. Max 20 words."
            return self._call_ollama(prompt) or f"The {subject} stirs ancient dread."
        else:
            return f"The {subject} has been seen in these halls since the Lich King's fall."
    def _build_prompt(self, category, kwargs):
        if category == "enter_room":
            return "Write one very short atmospheric sentence about entering a dungeon room. Max 10 words."
        elif category == "combat_start":
            return f"Write one short exciting sentence about a {kwargs.get('monster', 'monster')} attacking. Max 8 words."
        elif category == "defeat_monster":
            return f"Write one short triumphant sentence about defeating a {kwargs.get('monster', 'monster')}. Max 8 words."
        elif category == "boss_defeated":
            return f"Write one short epic sentence about slaying a {kwargs.get('boss', 'boss')}. Max 10 words."
        elif category == "treasure":
            return f"Write one short excited sentence about finding {kwargs.get('gold', 'gold')} gold and an item in a chest. Max 10 words."
        elif category == "trap":
            return f"Write one short painful sentence about a trap dealing {kwargs.get('damage', 0)} damage. Max 8 words."
        return "Tell a short story about a dungeon adventure."
    def _get_preset(self, category, **kwargs):
        if category in PRESET_STORIES:
            try:
                return random.choice(PRESET_STORIES[category]).format(**kwargs)
            except KeyError:
                return random.choice(PRESET_STORIES[category])
        return "Something happens."

# ============================== META PROGRESSION ==============================
class MetaProgression:
    UPGRADES = {
        "Vitality of the Ancients": {"description": "+5% Base HP per tier", "max_tier": 5, "cost_per_tier": [5,10,15,20,25], "effect": "hp_mult", "value_per_tier": 0.05},
        "Well of Souls": {"description": "+5% Base MP per tier", "max_tier": 5, "cost_per_tier": [5,10,15,20,25], "effect": "mp_mult", "value_per_tier": 0.05},
        "Blacksmith's Blessing": {"description": "Weapons lose durability 15% slower", "max_tier": 1, "cost_per_tier": [20], "effect": "durability_reduction", "value_per_tier": 0.15},
        "Merchant's Favor": {"description": "Safe Zone shop has 1 guaranteed Minor Health Potion", "max_tier": 1, "cost_per_tier": [15], "effect": "guaranteed_potion", "value_per_tier": True},
        "The Forbidden Arts": {"description": "Unlocks the Necromancer hero class", "max_tier": 1, "cost_per_tier": [50], "effect": "unlock_necromancer", "value_per_tier": True}
    }
    def __init__(self):
        self.total_shards = 0
        self.unlocked_upgrades = {}
        self.bloodstains = []
        self.last_death = None
        self.load()
    def get_save_path(self) -> str:
        return "global_save.json"
    def load(self):
        if os.path.exists(self.get_save_path()):
            try:
                with open(self.get_save_path(), "r") as f:
                    data = json.load(f)
                    self.total_shards = data.get("total_shards", 0)
                    self.unlocked_upgrades = data.get("unlocked_upgrades", {})
                    self.bloodstains = data.get("bloodstains", [])
                    self.last_death = data.get("last_death", None)
            except: self._init_defaults()
        else:
            self._init_defaults()
    def _init_defaults(self):
        self.total_shards = 0
        for up in self.UPGRADES:
            self.unlocked_upgrades[up] = 0
        self.bloodstains = []
        self.last_death = None
    def save(self):
        try:
            with open(self.get_save_path(), "w") as f:
                json.dump({"total_shards": self.total_shards, "unlocked_upgrades": self.unlocked_upgrades,
                           "bloodstains": self.bloodstains, "last_death": self.last_death}, f, indent=2)
        except: pass
    def add_shards(self, amount: int):
        self.total_shards += amount
        self.save()
    def get_upgrade_tier(self, upgrade_name: str) -> int:
        return self.unlocked_upgrades.get(upgrade_name, 0)
    def get_upgrade_cost(self, upgrade_name: str) -> int:
        current = self.get_upgrade_tier(upgrade_name)
        up = self.UPGRADES[upgrade_name]
        if current >= up["max_tier"]:
            return -1
        return up["cost_per_tier"][current]
    def purchase_upgrade(self, upgrade_name: str) -> bool:
        cost = self.get_upgrade_cost(upgrade_name)
        if cost == -1 or self.total_shards < cost:
            return False
        self.total_shards -= cost
        self.unlocked_upgrades[upgrade_name] += 1
        self.save()
        return True
    def get_hp_multiplier(self) -> float:
        return 1.0 + (self.get_upgrade_tier("Vitality of the Ancients") * 0.05)
    def get_mp_multiplier(self) -> float:
        return 1.0 + (self.get_upgrade_tier("Well of Souls") * 0.05)
    def get_durability_reduction(self) -> float:
        return 0.15 if self.get_upgrade_tier("Blacksmith's Blessing") > 0 else 0.0
    def has_guaranteed_potion(self) -> bool:
        return self.get_upgrade_tier("Merchant's Favor") > 0
    def is_necromancer_unlocked(self) -> bool:
        return self.get_upgrade_tier("The Forbidden Arts") > 0
    def record_bloodstain(self, stain):
        self.bloodstains.append(stain)
        self.save()
    def get_bloodstain_at(self, level, x, y):
        for s in self.bloodstains:
            if s["floor"] == level and s["x"] == x and s["y"] == y:
                return s
        return None
    def remove_bloodstain(self, stain):
        if stain in self.bloodstains:
            self.bloodstains.remove(stain)
            self.save()
    def set_last_death(self, hero_dict):
        self.last_death = hero_dict
        self.save()

class AncestralHallUI:
    def __init__(self, parent, meta: MetaProgression, on_close_callback=None):
        self.parent = parent
        self.meta = meta
        self.on_close_callback = on_close_callback
        self.create_window()
    def create_window(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("The Ancestral Hall - Eternal Upgrades")
        self.window.geometry("600x500")
        self.window.configure(bg=COLORS["bg_dark"])
        self.window.transient(self.parent)
        self.window.grab_set()
        tk.Label(self.window, text="THE ANCESTRAL HALL", font=("Georgia", 20, "bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack(pady=15)
        shard_frame = tk.Frame(self.window, bg=COLORS["bg_dark"])
        shard_frame.pack(pady=10)
        tk.Label(shard_frame, text="💎", font=("Arial", 24), fg=COLORS["gold_rare"], bg=COLORS["bg_dark"]).pack(side=tk.LEFT, padx=5)
        self.shard_label = tk.Label(shard_frame, text=f"Aethelgard's Shards: {self.meta.total_shards}", font=("Arial", 16, "bold"), fg=COLORS["gold"], bg=COLORS["bg_dark"])
        self.shard_label.pack(side=tk.LEFT, padx=5)
        desc = tk.Label(self.window, text="Spend shards to unlock permanent upgrades that persist across all descents.\nShards are earned by defeating powerful bosses on floors 5, 10, 15, and 20.", font=("Arial", 10), fg=COLORS["text"], bg=COLORS["bg_dark"], wraplength=550, justify="center")
        desc.pack(pady=10)
        tk.Frame(self.window, height=2, bg=COLORS["highlight"]).pack(fill=tk.X, padx=20, pady=10)
        canvas = tk.Canvas(self.window, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.window, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.upgrade_buttons = {}
        for name, data in self.meta.UPGRADES.items():
            self._add_upgrade_widget(scrollable_frame, name, data)
        tk.Button(self.window, text="Return to Halls", command=self.close, bg=COLORS["bg_light"], fg=COLORS["text"], font=("Arial",12)).pack(pady=15)
    def _add_upgrade_widget(self, parent, name, data):
        frame = tk.Frame(parent, bg=COLORS["bg_light"], relief=tk.RAISED, bd=1)
        frame.pack(fill=tk.X, padx=10, pady=5)
        current = self.meta.get_upgrade_tier(name)
        max_tier = data["max_tier"]
        cost = self.meta.get_upgrade_cost(name)
        tk.Label(frame, text=name, font=("Arial",12,"bold"), fg=COLORS["highlight"], bg=COLORS["bg_light"]).pack(anchor=tk.W, padx=10, pady=(5,0))
        tier_label = tk.Label(frame, text=f"Tier: {current}/{max_tier}", font=("Arial",10), fg=COLORS["text"], bg=COLORS["bg_light"])
        tier_label.pack(anchor=tk.W, padx=10)
        tk.Label(frame, text=data["description"], font=("Arial",9), fg=COLORS["grey"], bg=COLORS["bg_light"]).pack(anchor=tk.W, padx=10)
        btn_frame = tk.Frame(frame, bg=COLORS["bg_light"])
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        btn = tk.Button(btn_frame, text=f"Purchase (Cost: {cost} Shards)" if cost>0 else "MAXED", command=lambda n=name: self._purchase(n), bg=COLORS["gold_rare"] if cost>0 and self.meta.total_shards>=cost else COLORS["grey"], fg=COLORS["bg_dark"] if cost>0 and self.meta.total_shards>=cost else COLORS["text"], state=tk.NORMAL if cost>0 and self.meta.total_shards>=cost else tk.DISABLED, width=25)
        btn.pack(side=tk.RIGHT)
        if current >= max_tier:
            btn.config(text="MAXED", state=tk.DISABLED, bg=COLORS["green"])
        self.upgrade_buttons[name] = {"button": btn, "tier_label": tier_label}
    def _purchase(self, name):
        if self.meta.purchase_upgrade(name):
            current = self.meta.get_upgrade_tier(name)
            data = self.meta.UPGRADES[name]
            max_tier = data["max_tier"]
            cost = self.meta.get_upgrade_cost(name)
            self.upgrade_buttons[name]["tier_label"].config(text=f"Tier: {current}/{max_tier}")
            btn = self.upgrade_buttons[name]["button"]
            if current >= max_tier:
                btn.config(text="MAXED", state=tk.DISABLED, bg=COLORS["green"])
            else:
                btn.config(text=f"Purchase (Cost: {cost} Shards)", bg=COLORS["gold_rare"] if self.meta.total_shards>=cost else COLORS["grey"], state=tk.NORMAL if self.meta.total_shards>=cost else tk.DISABLED)
            self.shard_label.config(text=f"Aethelgard's Shards: {self.meta.total_shards}")
            self._refresh_all_buttons()
            messagebox.showinfo("Upgrade Purchased", f"You have acquired {name}!\nTier {current}/{max_tier} unlocked.")
        else:
            messagebox.showerror("Purchase Failed", "Not enough Aethelgard's Shards.")
    def _refresh_all_buttons(self):
        for name, data in self.meta.UPGRADES.items():
            current = self.meta.get_upgrade_tier(name)
            max_tier = data["max_tier"]
            cost = self.meta.get_upgrade_cost(name)
            btn = self.upgrade_buttons[name]["button"]
            if current >= max_tier:
                btn.config(text="MAXED", state=tk.DISABLED, bg=COLORS["green"])
            else:
                btn.config(text=f"Purchase (Cost: {cost} Shards)", bg=COLORS["gold_rare"] if self.meta.total_shards>=cost else COLORS["grey"], state=tk.NORMAL if self.meta.total_shards>=cost else tk.DISABLED)
    def close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.window.destroy()

# ============================== HERO TYPES ==============================
HERO_TYPES = {
    "Orc Berserker": {"desc": "Uses health for Blood Rage – double attack + lifesteal for 3 turns.", "base_stats": {"hp":70,"mp":0,"attack":12,"defense":4,"magic":2}, "resource_name":"Health","color":"#cc3300"},
    "Elf Aether-Mage": {"desc": "Massive mana pool. Aetherial Shift – ethereal + mana restore.", "base_stats": {"hp":40,"mp":60,"attack":5,"defense":2,"magic":15}, "resource_name":"Mana","color":"#33ccff"},
    "Dwarf Runesmith": {"desc": "Place Rune of Warding – stone pillar absorbs damage.", "base_stats": {"hp":65,"mp":20,"attack":8,"defense":12,"magic":5}, "resource_name":"Mana","color":"#cc9933"},
    "Nightblade": {"desc": "Shadow Step – teleport + backstab = auto crit.", "base_stats": {"hp":50,"mp":30,"attack":10,"defense":3,"magic":6}, "resource_name":"Mana","color":"#9933cc"},
    "Automaton Sentinel": {"desc": "Overdrive Beam – pierces all enemies, maxes Heat gauge.", "base_stats": {"hp":80,"mp":0,"attack":9,"defense":8,"magic":4}, "resource_name":"Heat","color":"#ffaa00"},
    "Necromancer": {"desc": "Raise fallen enemies as minions. Soul Harvest restores HP on kill.", "base_stats": {"hp":45,"mp":50,"attack":6,"defense":3,"magic":14}, "resource_name":"Mana","color":"#993399"}
}

# ============================== WEAPON TYPES ==============================
WEAPON_TYPES = {
    "Kinetic Greatmace": {"base_damage":12, "durability_max":80, "value":150, "mechanic":"impact", "magic_pool":["Earthquake"]},
    "Phase Dagger": {"base_damage":8, "durability_max":60, "value":140, "mechanic":"backstab", "magic_pool":["Ghost-Cut"]},
    "Repeating Crossbow": {"base_damage":7, "durability_max":50, "value":130, "mechanic":"volley", "magic_pool":["Seeking Bolts"]},
    "Living Vine-Whip": {"base_damage":9, "durability_max":70, "value":145, "mechanic":"reach", "magic_pool":["Life-Drain"]},
    "Runed Claymore": {"base_damage":14, "durability_max":90, "value":160, "mechanic":"heavy_swing", "magic_pool":["Spell-Parry"]},
    "Prism Staff": {"base_damage":10, "durability_max":65, "value":155, "mechanic":"refraction", "magic_pool":["Elemental Chaos"]},
    "Steam-Powered Saw": {"base_damage":13, "durability_max":55, "value":135, "mechanic":"bleed", "magic_pool":["Overheat"]},
    "Gravity Orb": {"base_damage":6, "durability_max":75, "value":125, "mechanic":"pull", "magic_pool":["Singularity"]},
    "Cursed Scythe": {"base_damage":11, "durability_max":60, "value":170, "mechanic":"reap", "magic_pool":["Soul Harvest"]},
    "Shield-Lance": {"base_damage":9, "durability_max":100, "value":150, "mechanic":"bulwark", "magic_pool":["Phalanx Charge"]},
    "Chipped Bone Dagger": {"base_damage":4, "durability_max":30, "value":60, "mechanic":"undead_bane", "magic_pool":[]},
    "Militia Pike": {"base_damage":6, "durability_max":70, "value":80, "mechanic":"reach", "magic_pool":[]},
    "Oak Cudgel": {"base_damage":8, "durability_max":100, "value":90, "mechanic":"stun_chance", "magic_pool":[]},
    "Storm-Forged Spear": {"base_damage":12, "durability_max":85, "value":220, "mechanic":"storm_bonus", "magic_pool":[]},
    "Blood-Letting Cleaver": {"base_damage":10, "durability_max":60, "value":200, "mechanic":"bleed_repair", "magic_pool":[]},
    "Mage-Bane Bow": {"base_damage":9, "durability_max":55, "value":210, "mechanic":"mana_drain", "magic_pool":[]},
    "Whispering Blade": {"base_damage":5, "durability_max":999, "value":500, "mechanic":"soul_eater", "magic_pool":[]},
    "Aethelgard's Regret": {"base_damage":40, "durability_max":0, "value":800, "mechanic":"life_drain", "magic_pool":[]},
    "Paradox Scepter": {"base_damage":0, "durability_max":200, "value":750, "mechanic":"paradox", "magic_pool":[]}
}

# ============================== SPELLS ==============================
SPELLS = {
    "Fireball": {"cost":15, "effect":"aoe_damage", "base_damage":20, "cooldown":0, "upgrade_cost":100},
    "Ice Lance": {"cost":20, "effect":"damage_slow", "base_damage":25, "slow_turns":3, "cooldown":0, "upgrade_cost":120},
    "Chain Lightning": {"cost":25, "effect":"chain_damage", "base_damage":18, "max_targets":3, "cooldown":1, "upgrade_cost":150},
    "Earth Spike": {"cost":18, "effect":"armor_penetration", "base_damage":22, "penetration":0.5, "cooldown":0, "upgrade_cost":110},
    "Wind Gust": {"cost":12, "effect":"push_back", "push_distance":3, "cooldown":1, "upgrade_cost":90},
    "Acid Spray": {"cost":14, "effect":"reduce_defense", "defense_reduction":5, "duration":5, "cooldown":0, "upgrade_cost":100},
    "Solar Flare": {"cost":20, "effect":"blind", "blind_turns":1, "cooldown":2, "upgrade_cost":130},
    "Vortex": {"cost":30, "effect":"pull_all", "cooldown":3, "upgrade_cost":180},
    "Magma Vein": {"cost":25, "effect":"fire_trail", "duration":5, "cooldown":2, "upgrade_cost":160},
    "Frost Nova": {"cost":22, "effect":"freeze_adjacent", "freeze_turns":1, "cooldown":2, "upgrade_cost":140},
    "Shadow Step": {"cost":10, "effect":"teleport", "range":5, "cooldown":1, "upgrade_cost":80},
    "Soul Drain": {"cost":15, "effect":"drain_hp_from_mana", "drain_ratio":0.5, "cooldown":0, "upgrade_cost":100},
    "Terror": {"cost":18, "effect":"flee", "duration":3, "cooldown":2, "upgrade_cost":110},
    "Confusion": {"cost":20, "effect":"confuse", "duration":2, "cooldown":2, "upgrade_cost":120},
    "Hemorrhage": {"cost":12, "effect":"bleed_double", "base_bleed":5, "cooldown":1, "upgrade_cost":90},
    "Silence": {"cost":15, "effect":"silence", "duration":3, "cooldown":2, "upgrade_cost":100},
    "Abyssal Grip": {"cost":12, "effect":"root", "duration":3, "cooldown":1, "upgrade_cost":90},
    "Death Mark": {"cost":10, "effect":"double_damage_next", "duration":1, "cooldown":1, "upgrade_cost":80},
    "Raise Sclera": {"cost":20, "effect":"reveal_map", "cooldown":0, "upgrade_cost":120},
    "Doom Tick": {"cost":25, "effect":"delayed_damage", "delay_turns":5, "damage":50, "cooldown":3, "upgrade_cost":150},
    "Lesser Heal": {"cost":10, "effect":"heal", "heal_amount":30, "cooldown":0, "upgrade_cost":80},
    "Mana Tap": {"cost":0, "effect":"hp_to_mana", "hp_percent":20, "mana_percent":40, "cooldown":1, "upgrade_cost":70},
    "Holy Shield": {"cost":20, "effect":"absorb_shield", "absorb_hits":2, "cooldown":3, "upgrade_cost":130},
    "Haste": {"cost":15, "effect":"haste", "duration":10, "cooldown":2, "upgrade_cost":100},
    "Cleanse": {"cost":12, "effect":"cleanse", "cooldown":1, "upgrade_cost":90},
    "Regeneration": {"cost":15, "effect":"regen", "heal_per_turn":5, "duration":10, "cooldown":1, "upgrade_cost":100},
    "Iron Body": {"cost":20, "effect":"damage_reduction", "reduction":0.3, "duration":5, "cooldown":2, "upgrade_cost":130},
    "Reflect Skin": {"cost":18, "effect":"reflect_melee", "reflect_percent":25, "duration":4, "cooldown":2, "upgrade_cost":110},
    "Guardian Angel": {"cost":30, "effect":"revive_buff", "duration":3, "cooldown":5, "upgrade_cost":180},
    "Smite": {"cost":15, "effect":"missing_hp_damage", "cooldown":1, "upgrade_cost":100},
    "Transmute": {"cost":20, "effect":"item_to_gold", "cooldown":0, "upgrade_cost":120},
    "Time Stop": {"cost":80, "effect":"time_stop", "duration":2, "cooldown":5, "upgrade_cost":300},
    "Mirror Image": {"cost":25, "effect":"decoy", "duration":3, "cooldown":3, "upgrade_cost":150},
    "Gravity Well": {"cost":15, "effect":"negate_projectiles", "duration":4, "cooldown":2, "upgrade_cost":100},
    "Blink Strike": {"cost":15, "effect":"teleport_attack", "cooldown":1, "upgrade_cost":100},
    "Gold Magnet": {"cost":10, "effect":"auto_loot", "cooldown":0, "upgrade_cost":70},
    "Petrify": {"cost":25, "effect":"petrify", "duration":10, "cooldown":3, "upgrade_cost":150},
    "Echo": {"cost":20, "effect":"double_cast_next", "duration":1, "cooldown":3, "upgrade_cost":130},
    "Shockwave": {"cost":18, "effect":"stun_line", "stun_turns":1, "cooldown":2, "upgrade_cost":110},
    "Final Gambit": {"cost":0, "effect":"all_mana_damage", "cooldown":4, "upgrade_cost":200}
}

# ============================== PASSIVES ==============================
PASSIVES = {
    "Mana Well": {"effect":"max_mana_mult","value":1.5},
    "Blood Magic": {"effect":"hp_instead_mp","value":True},
    "Thorns": {"effect":"thorns_damage","value":5},
    "Scavenger": {"effect":"gold_mult","value":1.2},
    "Eagle Eye": {"effect":"weapon_range","value":1},
    "Hardened Scales": {"effect":"flat_defense","value":10},
    "Wizard's Flow": {"effect":"mana_cost_reduction","value":0.2},
    "Adrenaline": {"effect":"speed_low_hp","value":0.25},
    "Scholar": {"effect":"xp_mult","value":1.15},
    "Toughness": {"effect":"max_hp_mult","value":1.5},
    "Second Wind": {"effect":"boss_kill_mana","value":0.2},
    "Firewalker": {"effect":"fire_immunity","value":True},
    "Heavy Hitter": {"effect":"crit_mult","value":3},
    "Light Foot": {"effect":"dodge_chance","value":0.1},
    "Alchemist": {"effect":"potion_effectiveness","value":1.5},
    "Soul Siphon": {"effect":"heal_on_kill","value":2},
    "Iron Will": {"effect":"immunity_silence_terror","value":True},
    "Dual-Core": {"effect":"extra_rune_slot","value":True},
    "Berserker's Spirit": {"effect":"attack_low_hp","value":True},
    "Treasure Hunter": {"effect":"loot_rarity","value":1}
}

# ============================== RUNES ==============================
RUNES = {
    "Rune of Potency": {"spell_damage_mult":1.1},
    "Rune of Thrift": {"mana_cost_reduction":5},
    "Rune of Haste": {"cooldown_reduction":1},
    "Rune of the Titan": {"stat_bonus":{"attack":2,"magic":2,"defense":2}}
}

# ============================== ACCESSORIES ==============================
class Accessory:
    def __init__(self, name, tier, effect_func, description, value, stat_bonus=None):
        self.name=name; self.tier=tier; self.effect_func=effect_func; self.description=description; self.value=value; self.stat_bonus=stat_bonus or {}
    def to_dict(self): return {"name":self.name,"tier":self.tier,"description":self.description,"value":self.value,"stat_bonus":self.stat_bonus}
    @classmethod
    def from_dict(cls, data): return cls(data["name"], data["tier"], None, data["description"], data["value"], data["stat_bonus"])

ACCESSORIES = {
    "Copper Ring of Vitality": Accessory("Copper Ring of Vitality", "Basic", lambda h,g: setattr(h,"bonus_hp",15), "+15 Max HP", 80, {"hp":15}),
    "Brass Amulet of Focus": Accessory("Brass Amulet of Focus", "Basic", lambda h,g: setattr(h,"bonus_mp",10), "+10 Max MP", 80, {"mp":10}),
    "Scavenger's Charm": Accessory("Scavenger's Charm", "Basic", lambda h,g: setattr(h,"scavenger_bonus",0.1), "10% more scrap drops", 100, {}),
    "Ring of the Salamander": Accessory("Ring of the Salamander", "Special", lambda h,g: (setattr(h,"fire_resist",0.25), setattr(h,"ignite_on_hit",0.2)), "25% fire resist, 20% ignite", 250, {"fire_resist":25}),
    "Amulet of Greed": Accessory("Amulet of Greed", "Special", lambda h,g: (setattr(h,"gold_mult",1.5), setattr(h,"shop_markup",1.2)), "+50% gold, +20% shop prices", 300, {}),
    "Bandit's Coin": Accessory("Bandit's Coin", "Special", lambda h,g: setattr(h,"bandit_coin",True), "Leave enemy with 1 HP makes them flee", 280, {}),
    "The Ouroboros Signet": Accessory("The Ouroboros Signet", "Unique", lambda h,g: setattr(h,"ouroboros",True), "Swap HP/MP potion effects", 600, {}),
    "The Beating Heart Amulet": Accessory("The Beating Heart Amulet", "Unique", lambda h,g: setattr(h,"heart_revive",True), "Revive once but lose 10 max HP", 800, {}),
    "Shackle of the Void": Accessory("Shackle of the Void", "Unique", lambda h,g: setattr(h,"void_teleport",True), "Movement becomes 3-tile teleport", 700, {})
}

# ============================== ARMOR PIECES ==============================
class Armor:
    def __init__(self, name, slot, phys_def, mag_res, movement_mod, property_func, description, tier):
        self.name=name; self.slot=slot; self.phys_def=phys_def; self.mag_res=mag_res; self.movement_mod=movement_mod; self.property_func=property_func; self.description=description; self.tier=tier
    def to_dict(self): return {"name":self.name,"slot":self.slot,"phys_def":self.phys_def,"mag_res":self.mag_res,"movement_mod":self.movement_mod,"description":self.description,"tier":self.tier}
    @classmethod
    def from_dict(cls, data): return cls(data["name"], data["slot"], data["phys_def"], data["mag_res"], data["movement_mod"], None, data["description"], data["tier"])

ARMOR_PIECES = {
    "Miner's Hardhat": Armor("Miner's Hardhat","head",2,1,0,lambda h,g:setattr(g,"vision_radius",1),"Increases map vision radius", "Basic"),
    "Crown of the Mad King": Armor("Crown of the Mad King","head",0,0,0,lambda h,g:setattr(h,"mad_crown",True),"Doubles damage but confuses movement", "Unique"),
    "Hood of Shadows": Armor("Hood of Shadows","head",1,2,0,lambda h,g:setattr(h,"stealth",0.3),"Reduces aggro radius", "Special"),
    "Helm of the Iron Will": Armor("Helm of the Iron Will","head",8,5,-1,lambda h,g:setattr(h,"iron_will",True),"Immunity to fear", "Special"),
    "Cowl of the Necromancer": Armor("Cowl of the Necromancer","head",3,8,0,lambda h,g:setattr(h,"necromancy_power",True),"+8 magic resist", "Special"),
    "Leather Cap": Armor("Leather Cap","head",3,1,0,lambda h,g:None,"Simple leather cap", "Basic"),
    "Steel Helm": Armor("Steel Helm","head",6,2,-1,lambda h,g:None,"Standard steel helm", "Basic"),
    "Wizard's Hat": Armor("Wizard's Hat","head",1,6,0,lambda h,g:setattr(h,"spell_power",5),"+6 magic resist, +5 spell power", "Special"),
    "Boiled Leather Tunic": Armor("Boiled Leather Tunic","chest",5,2,0,lambda h,g:None,"Standard leather armor", "Basic"),
    "Spiked Spaulders": Armor("Spiked Spaulders","chest",8,3,-1,lambda h,g:setattr(h,"thorn_percent",0.1),"Returns 10% melee damage", "Special"),
    "Glacial Plate": Armor("Glacial Plate","chest",15,10,-2,lambda h,g:setattr(h,"chill_on_hit",True),"Slows enemies that hit you", "Special"),
    "Carapace of the Hive Mother": Armor("Carapace of the Hive Mother","chest",10,5,-1,lambda h,g:setattr(h,"spawn_grub",True),"Spawns a grub ally", "Unique"),
    "Chainmail Shirt": Armor("Chainmail Shirt","chest",8,3,-1,lambda h,g:None,"Standard chainmail", "Basic"),
    "Plate Cuirass": Armor("Plate Cuirass","chest",12,4,-2,lambda h,g:None,"Heavy plate armor", "Basic"),
    "Robe of the Archmage": Armor("Robe of the Archmage","chest",2,12,0,lambda h,g:setattr(h,"mage_robe",True),"+12 magic resist", "Special"),
    "Dragon Scale Mail": Armor("Dragon Scale Mail","chest",18,8,-2,lambda h,g:setattr(h,"fire_resist",0.5),"+18 defense, 50% fire resist", "Rare"),
    "Worn Marching Boots": Armor("Worn Marching Boots","legs",2,1,0,lambda h,g:setattr(h,"stamina_save",True),"Reduces exploration fatigue", "Basic"),
    "Muffled Treads": Armor("Muffled Treads","legs",4,2,1,lambda h,g:setattr(h,"stealth",0.5),"Reduces aggro radius", "Special"),
    "Boots of the Chronomancer": Armor("Boots of the Chronomancer","legs",5,5,1,lambda h,g:setattr(g,"chrono_boots",True),"Allows rewinding last 3 turns", "Unique"),
    "Greaves of the Sentinel": Armor("Greaves of the Sentinel","legs",10,4,-1,lambda h,g:setattr(h,"sentinel_greaves",True),"+10 defense, reduces knockback", "Special"),
    "Leather Leggings": Armor("Leather Leggings","legs",4,1,0,lambda h,g:None,"Simple leather leggings", "Basic"),
    "Plate Greaves": Armor("Plate Greaves","legs",8,2,-1,lambda h,g:None,"Heavy plate greaves", "Basic"),
    "Assassin's Treads": Armor("Assassin's Treads","legs",3,3,2,lambda h,g:setattr(h,"move_speed",0.2),"Increases movement speed", "Special"),
    "Boots of Levitation": Armor("Boots of Levitation","legs",2,4,0,lambda h,g:setattr(h,"levitate",True),"Allows hovering over traps", "Rare")
}

# ============================== CONSUMABLES ==============================
class Consumable:
    def __init__(self, name, tier, effect_func, description, value, stat_bonus=None):
        self.name=name; self.tier=tier; self.effect_func=effect_func; self.description=description; self.value=value; self.stat_bonus=stat_bonus or {}
    def to_dict(self): return {"name":self.name,"tier":self.tier,"description":self.description,"value":self.value,"stat_bonus":self.stat_bonus}
    @classmethod
    def from_dict(cls, data): return cls(data["name"], data["tier"], None, data["description"], data["value"], data["stat_bonus"])

def repair_kit_effect(hero, game_engine):
    if hero.weapon and hero.weapon.max_durability > 0:
        hero.weapon.current_durability = min(hero.weapon.max_durability, hero.weapon.current_durability + 25)
        game_engine.ui.log_message(f"Repair Kit restored 25 durability to {hero.weapon.weapon_type}.")
    else:
        game_engine.ui.log_message("No repairable weapon equipped.")

def mana_elixir_effect(hero, game_engine):
    if hero.max_mp > 0:
        hero.restore_mp(15)
        game_engine.ui.log_message(f"Restored 15 MP. Current MP: {hero.mp}/{hero.max_mp}")
    else:
        hero.heal(15)
        game_engine.ui.log_message("You have no mana pool. The elixir restores 15 HP instead.")

CONSUMABLES = {
    "Minor Health Potion": Consumable("Minor Health Potion", "Basic", lambda h,g: h.heal(20), "Restores 20 HP.", 30, {"hp":20}),
    "Minor Mana Elixir": Consumable("Minor Mana Elixir", "Basic", mana_elixir_effect, "Restores 15 MP (or 15 HP if no mana).", 25, {"mp":15}),
    "Repair Kit": Consumable("Repair Kit", "Basic", repair_kit_effect, "Restores 25 durability to equipped weapon.", 80, {}),
    "Charcoal Antidote": Consumable("Charcoal Antidote", "Basic", lambda h,g: setattr(g,"poison_cure",True), "Cures Poison and Bleed.", 40, {}),
    "Vial of Giant's Blood": Consumable("Vial of Giant's Blood", "Basic", lambda h,g: setattr(g,"giant_strength",10), "+5 Physical Damage for 10 turns.", 50, {}),
    "Troll-Blood Flask": Consumable("Troll-Blood Flask", "Special", lambda h,g: setattr(g,"regen_buff",(10,5)), "Heals 5 HP per turn for 10 turns.", 120, {}),
    "Aetherial Draught": Consumable("Aetherial Draught", "Special", lambda h,g: (h.restore_mp(int(h.max_mp*0.5)), setattr(g,"physical_nerf",3)), "Restores 50% MP, reduces physical damage by 50% for 3 turns.", 150, {}),
    "Flask of the Basilisk": Consumable("Flask of the Basilisk", "Special", lambda h,g: setattr(g,"basilisk_root",3), "Roots enemies in a 3x3 area for 3 turns.", 200, {}),
    "Potion of Displacement": Consumable("Potion of Displacement", "Special", lambda h,g: (setattr(g,"dodge_buff",(5,0.5)), setattr(g,"displacement_teleport",5)), "+50% dodge for 5 turns, random teleport each turn.", 180, {}),
    "Elixir of the Phoenix": Consumable("Elixir of the Phoenix", "Unique", lambda h,g: setattr(g,"phoenix_blessing",20), "Revive with 50% HP and damage enemies if you die within 20 turns.", 500, {}),
    "Liquid Void": Consumable("Liquid Void", "Unique", lambda h,g: setattr(g,"void_mana",3), "Spells cost 0 MP for 3 turns, then mana drained to 0.", 450, {}),
    "Bottled Miasma": Consumable("Bottled Miasma", "Unique", lambda h,g: setattr(g,"miasma_store",True), "Cures all debuffs and applies them to next enemy hit.", 400, {}),
    "Liquid Gold": Consumable("Liquid Gold", "Unique", lambda h,g: (setattr(g,"gold_skin",10), setattr(g,"gold_bonus",100)), "+50 Defense, immobile for 10 turns, then gain 100 gold.", 600, {}),
    "Recall Scroll": Consumable("Recall Scroll", "Special", lambda h,g: setattr(g,"recall_cast",2), "Returns to Safe Zone after 2 turns (interruptible).", 150, {}),
    "Scholar's Monocle": Consumable("Scholar's Monocle", "Special", lambda h,g: setattr(g,"identify_items",True), "Identifies all unidentified items in inventory.", 200, {}),
    "Skeleton Key": Consumable("Skeleton Key", "Special", lambda h,g: setattr(g,"skeleton_key_used",True), "Opens any locked door or treasure chest.", 100, {}),
    "Miner's Dynamite": Consumable("Miner's Dynamite", "Special", lambda h,g: setattr(g,"dynamite_used",True), "Destroys cracked walls or deals 30 AoE damage.", 120, {}),
    "Panacea Ointment": Consumable("Panacea Ointment", "Special", lambda h,g: setattr(g,"panacea_used",True), "Cures all physical status effects.", 180, {}),
    "Void Chalk": Consumable("Void Chalk", "Special", lambda h,g: setattr(g,"void_chalk_mode",True), "Draws glyphs (3 charges).", 250, {}),
    "Blank Rune Slab": Consumable("Blank Rune Slab", "Unique", lambda h,g: setattr(g,"rune_slab_available",True), "Used at blacksmith to transfer enchantments.", 500, {}),
    "Healing Salve": Consumable("Healing Salve", "Basic", lambda h,g: h.heal(15), "Restores 15 HP gradually.", 20, {"hp":15}),
    "Stamina Draft": Consumable("Stamina Draft", "Basic", lambda h,g: setattr(g,"stamina_buff",20), "Reduces movement penalty from armor for 20 turns.", 35, {}),
    "Mana Crystal": Consumable("Mana Crystal", "Basic", lambda h,g: h.restore_mp(10), "Restores 10 MP.", 40, {"mp":10}),
    "Berserker Brew": Consumable("Berserker Brew", "Special", lambda h,g: setattr(g,"berserk_buff",5), "+50% damage, -50% defense for 5 turns.", 100, {}),
    "Invisibility Potion": Consumable("Invisibility Potion", "Special", lambda h,g: setattr(g,"invisible",3), "Invisible for 3 turns (attacks break invisibility).", 150, {})
}

# ============================== STATUS EFFECT ENGINE ==============================
class StatusEffect:
    def __init__(self, name, duration, magnitude=0, extra=None):
        self.name=name; self.duration=duration; self.magnitude=magnitude; self.extra=extra

class StatusAware:
    def __init__(self):
        self.active_statuses = {}
        self.last_action = None
        self.echo_pending = False
    def apply_status(self, name, duration, magnitude=0, extra=None):
        if name in self.active_statuses:
            old = self.active_statuses[name]
            old.duration = max(old.duration, duration)
            if name == "Bleed": old.magnitude = max(old.magnitude, magnitude)
            else: old.magnitude = magnitude
        else: self.active_statuses[name] = StatusEffect(name, duration, magnitude, extra)
    def remove_status(self, name):
        if name in self.active_statuses: del self.active_statuses[name]
    def has_status(self, name): return name in self.active_statuses
    def process_statuses(self, game_engine=None):
        messages = []
        for name in list(self.active_statuses.keys()):
            status = self.active_statuses[name]
            if name == "Bleed":
                dmg = status.magnitude
                self.take_damage(dmg)
                messages.append(f"{self.name} bleeds for {dmg} damage!")
                status.magnitude *= 2
            elif name == "Soul-Burn":
                if hasattr(self, 'mp'):
                    mp_loss = min(status.magnitude, self.mp)
                    self.mp -= mp_loss
                    remaining = status.magnitude - mp_loss
                    if remaining > 0:
                        self.take_damage(remaining)
                        messages.append(f"{self.name} takes {remaining} Soul-Burn damage to HP!")
                    else: messages.append(f"{self.name} loses {mp_loss} MP from Soul-Burn.")
                else:
                    self.take_damage(status.magnitude)
                    messages.append(f"{self.name} suffers {status.magnitude} Soul-Burn damage!")
            elif name == "Regeneration":
                heal = status.magnitude
                self.heal(heal) if hasattr(self, 'heal') else None
                messages.append(f"{self.name} regenerates {heal} HP.")
            elif name == "Rooted": pass
            elif name == "Stunned": pass
            elif name == "Levitating": pass
            elif name == "Crystallized": pass
            elif name == "Doom":
                if status.extra is None: status.extra = 0
                status.extra += 1
                if status.extra >= 4:
                    self.hp = 1
                    messages.append(f"{self.name} is doomed! HP drops to 1!")
                    del self.active_statuses[name]
                    continue
            elif name == "Temporal Echo":
                if self.echo_pending and self.last_action:
                    if self.last_action == "attack":
                        dmg = max(1, getattr(self, 'attack', 5) // 2)
                        messages.append(f"Temporal echo ripples, but no target.")
                    self.echo_pending = False
                else: self.echo_pending = True
            status.duration -= 1
            if status.duration <= 0:
                del self.active_statuses[name]
                messages.append(f"{self.name} is no longer {name.lower()}.")
        return messages

# ============================== ITEM, WEAPON, SPELL, RUNE CLASSES ==============================
class Item:
    def __init__(self, id, name, type, value, stat_bonus=None, description=""):
        self.id=id; self.name=name; self.type=type; self.value=value; self.stat_bonus=stat_bonus or {}; self.description=description; self.equipped=False; self.identified=True
    def to_dict(self): return {"id":self.id,"name":self.name,"type":self.type,"value":self.value,"stat_bonus":self.stat_bonus,"description":self.description,"equipped":self.equipped,"identified":self.identified}
    @classmethod
    def from_dict(cls, data): return cls(data["id"], data["name"], data["type"], data["value"], data["stat_bonus"], data["description"])

class Weapon:
    def __init__(self, weapon_type, upgrade_level=0, magic_abilities=None):
        self.weapon_type = weapon_type
        self.upgrade_level = upgrade_level
        self.magic_abilities = magic_abilities or []
        self.base = WEAPON_TYPES[weapon_type]
        self.current_durability = self.base["durability_max"] + upgrade_level*5 if self.base["durability_max"]>0 else 999
        self.max_durability = self.base["durability_max"] + upgrade_level*5 if self.base["durability_max"]>0 else 999
        self.damage = self.base["base_damage"] + upgrade_level*2
        self.mechanic = self.base["mechanic"]
        self.value = self.base["value"] + upgrade_level*20
    def get_rarity(self):
        if any(x in self.weapon_type for x in ["Whispering Blade","Aethelgard's Regret","Paradox Scepter"]): return "Artifact"
        elif self.upgrade_level >= 10: return "Artifact"
        elif self.upgrade_level >= 7: return "Epic"
        elif self.upgrade_level >= 4: return "Rare"
        elif self.upgrade_level >= 1 or self.magic_abilities: return "Enchanted"
        else: return "Basic"
    def get_color(self): return RARITY_COLOR[self.get_rarity()]
    def use_durability(self, mult=1):
        if self.max_durability == 0: return
        self.current_durability -= mult
        if self.current_durability < 0: self.current_durability = 0
    def is_broken(self): return self.current_durability <= 0 and self.max_durability > 0
    def repair(self, amount):
        if self.max_durability > 0: self.current_durability = min(self.max_durability, self.current_durability + amount)
    def to_dict(self): return {"weapon_type":self.weapon_type,"upgrade_level":self.upgrade_level,"magic_abilities":self.magic_abilities,"current_durability":self.current_durability,"max_durability":self.max_durability,"damage":self.damage}
    @classmethod
    def from_dict(cls, data):
        w = cls(data["weapon_type"], data["upgrade_level"], data["magic_abilities"])
        w.current_durability = data["current_durability"]; w.max_durability = data["max_durability"]; w.damage = data["damage"]
        return w

class Spell:
    def __init__(self, name, level=1):
        self.name = name; self.level = level; self.data = SPELLS[name].copy(); self.current_cooldown = 0
    def get_cost(self): return max(5, self.data["cost"] - (self.level-1)*2)
    def get_damage(self): return self.data.get("base_damage",0) + (self.level-1)*5
    def upgrade_cost(self): return self.data["upgrade_cost"] * self.level
    def get_description(self):
        data = self.data
        effect_names = {
            "aoe_damage": "Area damage", "damage_slow": "Damage + Slow", "chain_damage": "Chain lightning",
            "armor_penetration": "Ignores armor", "push_back": "Knocks back", "reduce_defense": "Reduces defense",
            "blind": "Blinds enemy", "pull_all": "Pulls enemies", "freeze_adjacent": "Freezes nearby",
            "teleport": "Teleports you", "drain_hp_from_mana": "Drains HP from mana", "flee": "Makes enemy flee",
            "confuse": "Confuses enemy", "bleed_double": "Causes bleeding", "silence": "Silences enemy",
            "root": "Roots enemy", "double_damage_next": "Marks for double damage", "reveal_map": "Reveals map",
            "delayed_damage": "Delayed explosion", "heal": "Heals you", "hp_to_mana": "Converts HP to MP",
            "absorb_shield": "Creates shield", "haste": "Doubles movement", "cleanse": "Removes debuffs",
            "regen": "Regeneration", "damage_reduction": "Damage reduction", "reflect_melee": "Reflects melee",
            "revive_buff": "Auto-revive", "missing_hp_damage": "Scales with missing HP", "item_to_gold": "Transmutes item",
            "time_stop": "Stops time", "decoy": "Creates decoy", "negate_projectiles": "Negates projectiles",
            "teleport_attack": "Teleport + attack", "auto_loot": "Auto-loot gold", "petrify": "Turns to stone",
            "double_cast_next": "Double next spell", "stun_line": "Stuns line", "all_mana_damage": "Consumes all mana"
        }
        effect_desc = effect_names.get(data["effect"], data["effect"])
        return f"Effect: {effect_desc}\nMana cost: {self.get_cost()} | Cooldown: {data.get('cooldown',0)}\nBase damage: {self.get_damage()}"
    def to_dict(self): return {"name":self.name,"level":self.level,"current_cooldown":self.current_cooldown}
    @classmethod
    def from_dict(cls, data): s=cls(data["name"],data["level"]); s.current_cooldown=data["current_cooldown"]; return s

class Rune:
    def __init__(self, name): self.name=name; self.effect=RUNES[name]
    def to_dict(self): return {"name":self.name}
    @classmethod
    def from_dict(cls, data): return cls(data["name"])

# ============================== MONSTER & BOSS ==============================
class Monster(StatusAware):
    def __init__(self, name, mtype, level, hp, atk, defense, xp, gold, ability, params, loot):
        super().__init__()
        self.name=name; self.monster_type=mtype; self.level=level
        self.max_hp=hp; self.hp=hp; self.attack=atk; self.defense=defense
        self.xp_reward=xp; self.gold_reward=gold; self.ability=ability; self.ability_params=params; self.loot_table=loot; self.ability_cooldown=0
    def take_damage(self, dmg):
        actual = max(1, dmg - self.defense//2)
        self.hp -= actual
        if self.hp < 0: self.hp = 0
        return actual
    def is_alive(self): return self.hp > 0
    def heal(self, amount): self.hp = min(self.max_hp, self.hp+amount)

BOSSES = {
    1: {"name": "Grave-Warden Aegis", "property": "invulnerable_front", "drop_core": "Warden's Iron Skin", "hp": 150, "attack": 20, "defense": 15, "xp": 500, "gold": 300},
    2: {"name": "Pyrophage, the Living Forge", "property": "heat_sink", "drop_core": "Cinder Heart", "hp": 180, "attack": 22, "defense": 12, "xp": 600, "gold": 350},
    3: {"name": "Skitter-Queen Silk-Veil", "property": "web_tether", "drop_core": "Spider-Silk Boots", "hp": 160, "attack": 18, "defense": 10, "xp": 550, "gold": 320},
    4: {"name": "The Alchemist's Failure", "property": "unstable_mutation", "drop_core": "Shifting Catalyst", "hp": 200, "attack": 15, "defense": 8, "xp": 700, "gold": 400},
    5: {"name": "High Inquisitor Malphas", "property": "holy_retribution", "drop_core": "Inquisitor's Eye", "hp": 190, "attack": 25, "defense": 14, "xp": 750, "gold": 450},
    6: {"name": "The Clockwork Centurion", "property": "pressure_valve", "drop_core": "Piston Core", "hp": 220, "attack": 28, "defense": 18, "xp": 800, "gold": 500},
    7: {"name": "Glaciara, the Frozen Heart", "property": "deep_freeze", "drop_core": "Glacial Focus", "hp": 170, "attack": 20, "defense": 11, "xp": 650, "gold": 380},
    8: {"name": "General Drax the Conqueror", "property": "call_to_arms", "drop_core": "Conqueror's Banner", "hp": 210, "attack": 24, "defense": 16, "xp": 850, "gold": 520},
    9: {"name": "The Mirage Weaver", "property": "hallucination", "drop_core": "Cloak of Deception", "hp": 140, "attack": 30, "defense": 5, "xp": 900, "gold": 600},
    10: {"name": "Gorgon-Queen Stheno", "property": "stone_casing", "drop_core": "Medusa Shield", "hp": 230, "attack": 26, "defense": 20, "xp": 1000, "gold": 700},
    11: {"name": "The Abyssal Leviathan", "property": "flood", "drop_core": "Aquatic Rune", "hp": 250, "attack": 30, "defense": 12, "xp": 1100, "gold": 800},
    12: {"name": "Lord Volos the Vampire King", "property": "sanguine_link", "drop_core": "Vampiric Fang", "hp": 200, "attack": 35, "defense": 10, "xp": 1200, "gold": 900},
    13: {"name": "The Rust-Monster Alpha", "property": "equipment_rot", "drop_core": "Acid-Proof Coating", "hp": 180, "attack": 22, "defense": 8, "xp": 950, "gold": 650},
    14: {"name": "The Necromancer's Amalgam", "property": "graveyard_shift", "drop_core": "Soul Jar", "hp": 260, "attack": 28, "defense": 14, "xp": 1300, "gold": 1000},
    15: {"name": "Ra-Hotep the Blighted Mummy", "property": "curse_of_agony", "drop_core": "Golden Ankh", "hp": 210, "attack": 32, "defense": 18, "xp": 1400, "gold": 1100},
    16: {"name": "The Storm-Herald Avian", "property": "high_ground", "drop_core": "Storm-Caller's Ring", "hp": 190, "attack": 34, "defense": 6, "xp": 1500, "gold": 1200},
    17: {"name": "The Emerald Hydra", "property": "regrowth", "drop_core": "Hydra Scale", "hp": 300, "attack": 25, "defense": 20, "xp": 1600, "gold": 1300},
    18: {"name": "Xar-Thul the Void Horror", "property": "sanity_drain", "drop_core": "Void Pendant", "hp": 240, "attack": 40, "defense": 10, "xp": 1800, "gold": 1500},
    19: {"name": "The Iron-Bound Behemoth", "property": "momentum", "drop_core": "Titan's Belt", "hp": 350, "attack": 30, "defense": 25, "xp": 2000, "gold": 1800},
    20: {"name": "The Lich King Aethelgard", "property": "final_judgement", "drop_core": "The Aethelgard Crown", "hp": 500, "attack": 45, "defense": 30, "xp": 5000, "gold": 5000}
}

class Boss(Monster):
    def __init__(self, level):
        data = BOSSES[level]
        super().__init__(data["name"], "boss", level, data["hp"], data["attack"], data["defense"], data["xp"], data["gold"], data["property"], {}, [])
        self.property = data["property"]
        self.core_drop = data["drop_core"]
        self.turn_counter = 0
        self.clone_list = []
        self.flight_timer = 0
        self.steam_counter = 0
        self.water_level = 0
        self.mutation_hp_threshold = self.max_hp * 0.75
        self.shard_reward = self._get_shard_reward(level)
    def _get_shard_reward(self, level):
        if level == 5: return 1
        elif level == 10: return 2
        elif level == 15: return 3
        elif level == 20: return 5
        else: return 0
    def take_damage(self, dmg, from_side=False, is_magic=False):
        if self.has_status("Crystallized") and is_magic: dmg = int(dmg*0.5)
        if self.property == "invulnerable_front" and not from_side: return 0
        if self.property == "holy_retribution" and is_magic:
            reflect = int(dmg*0.2)
            if reflect > 0: return reflect
        actual = max(1, dmg - self.defense//2)
        self.hp -= actual
        if self.hp < 0: self.hp = 0
        if self.property == "unstable_mutation" and self.hp <= self.mutation_hp_threshold:
            self.mutation_hp_threshold -= self.max_hp * 0.25
        return actual
    def use_boss_ability(self, hero, game_engine):
        self.turn_counter += 1
        msg = ""
        if self.property == "heat_sink": game_engine.floor_on_fire = True; msg += "The floor ignites! "
        if self.property == "web_tether" and self.turn_counter % 3 == 0: game_engine.player_rooted = 2; msg += "You are pulled and rooted! "
        if self.property == "call_to_arms" and self.turn_counter % 3 == 0:
            for _ in range(2):
                skel = Monster("Skeletal Hoplite","undead",self.level,30+self.level*2,12+self.level,8,50,30,"Phalanx",{},[])
                game_engine.combat_monsters.append(skel)
            msg += "Two hoplites summoned! "
        if self.property == "hallucination" and self.turn_counter == 1:
            for _ in range(3):
                clone = Boss(self.level)
                clone.name = "Mirage Clone"
                clone.hp = 1
                clone.property = "clone"
                game_engine.combat_monsters.append(clone)
            msg += "Three clones appear! "
        if self.property == "stone_casing" and random.random() < 0.3: game_engine.player_stunned = 3; msg += "You are petrified! "
        if self.property == "flood":
            self.water_level += 1
            if self.water_level > 20: hero.take_damage(15); msg += "Drowning damage! "
        if self.property == "graveyard_shift":
            heal = 20
            self.hp = min(self.max_hp, self.hp+heal)
            msg += f"Amalgam heals {heal} HP! "
        if self.property == "high_ground":
            self.flight_timer += 1
            if self.flight_timer >= 3: game_engine.boss_flying = True; msg += "Avian flies high! "; self.flight_timer = 0
        if self.property == "regrowth" and not game_engine.fire_damage_dealt_this_turn:
            heal = 20
            self.hp = min(self.max_hp, self.hp+heal)
            msg += f"Hydra regenerates {heal} HP! "
        if self.property == "sanity_drain" and self.turn_counter % 4 == 0: game_engine.scrambled_movement = 2; msg += "Controls scrambled! "
        if self.property == "final_judgement" and self.hp <= self.max_hp * 0.1: hero.mp = 0; msg += "Mana wiped! "
        if self.property == "pressure_valve":
            self.steam_counter += 1
            if self.steam_counter >= 5: hero.take_damage(40); msg += "Steam explosion! "; self.steam_counter = 0
        if self.property == "deep_freeze": game_engine.mana_regen_penalty += 2
        return msg

# ============================== QUEST SYSTEM ==============================
class Quest:
    def __init__(self, quest_id, name, description, objectives, rewards, npc, prerequisite=None):
        self.quest_id = quest_id
        self.name = name
        self.description = description
        self.objectives = objectives
        self.rewards = rewards
        self.npc = npc
        self.prerequisite = prerequisite
        self.completed = False
    def to_dict(self):
        return {"id": self.quest_id, "name": self.name, "description": self.description,
                "objectives": self.objectives, "rewards": self.rewards, "npc": self.npc,
                "prerequisite": self.prerequisite, "completed": self.completed}
    @classmethod
    def from_dict(cls, data):
        q = cls(data["id"], data["name"], data["description"], data["objectives"],
                data["rewards"], data["npc"], data.get("prerequisite"))
        q.completed = data.get("completed", False)
        return q

class QuestManager:
    def __init__(self):
        self.active_quests = []
        self.completed_quests = []
        self.quests_db = self._build_quest_db()
    def _build_quest_db(self):
        return {
            "truffle_smuggler": Quest(
                "truffle_smuggler", "The Truffle Smuggler",
                "Gather 3 Cave-Truffles from smashed barrels on floors 1-5.",
                [{"type": "gather", "target": "Cave-Truffle", "amount": 3, "current": 0}],
                [{"type": "discount", "value": 20}, {"type": "item", "item": "Truffle Brew"}],
                "shopkeeper"
            ),
            "reclaim_ledger": Quest(
                "reclaim_ledger", "Reclaiming the Ledger",
                "Kill the Goblin Footpad (elite goblin) on the next floor.",
                [{"type": "kill", "target": "Goblin Footpad", "amount": 1, "current": 0}],
                [{"type": "gold", "value": 200}, {"type": "item", "item": "Skeleton Key"}],
                "shopkeeper"
            ),
            "taste_for_venom": Quest(
                "taste_for_venom", "A Taste for Venom",
                "Bring 5 Poison Glands from Putrid Shamblers.",
                [{"type": "gather", "target": "Poison Gland", "amount": 5, "current": 0}],
                [{"type": "item", "item": "Antidote Pouch"}],
                "shopkeeper"
            ),
            "perfect_alloy": Quest(
                "perfect_alloy", "The Perfect Alloy",
                "Bring 10 Scrap Metal and 1 Living Coal (from Cinder Sprites on floors 6-10).",
                [{"type": "gather", "target": "Scrap Metal", "amount": 10, "current": 0},
                 {"type": "gather", "target": "Living Coal", "amount": 1, "current": 0}],
                [{"type": "weapon_upgrade", "value": 3}],
                "blacksmith"
            ),
            "field_testing": Quest(
                "field_testing", "Field Testing",
                "Kill 10 enemies with the Prototype Blade before it breaks.",
                [{"type": "special", "target": "prototype_kills", "amount": 10, "current": 0}],
                [{"type": "item", "item": "Masterwork Whetstone"}],
                "blacksmith"
            ),
            "shattered_pride": Quest(
                "shattered_pride", "Shattered Pride",
                "Find the Rusted Hammer Head in an Ornate Chest on floors 11-15.",
                [{"type": "gather", "target": "Rusted Hammer Head", "amount": 1, "current": 0}],
                [{"type": "service", "service": "hone"}],
                "blacksmith"
            ),
            "echoes_void": Quest(
                "echoes_void", "Echoes of the Void",
                "Defeat 3 enemies on the next floor using only spells (no physical attacks).",
                [{"type": "special", "target": "spell_only_kills", "amount": 3, "current": 0}],
                [{"type": "item", "item": "Rune of Thrift"}, {"type": "unlock_spell", "spell": "Time Stop"}],
                "magic_altar"
            ),
            "thirst_altar": Quest(
                "thirst_altar", "Thirst of the Altar",
                "Permanently sacrifice 15 Max MP at the Altar.",
                [{"type": "special", "target": "sacrifice_mp", "amount": 15, "current": 0}],
                [{"type": "passive", "passive": "Archmage's Flow"}],
                "magic_altar"
            ),
            "soul_capture": Quest(
                "soul_capture", "Soul Capture",
                "Use an Empty Soul Gem to kill a boss while stunned or frozen.",
                [{"type": "special", "target": "soul_gem_kill", "amount": 1, "current": 0}],
                [{"type": "item", "item": "Soul Gem Amulet"}],
                "magic_altar"
            ),
            "blood_money": Quest(
                "blood_money", "Blood Money",
                "Steal from the Storekeeper's private chest in the Safe Zone.",
                [{"type": "special", "target": "steal_chest", "amount": 1, "current": 0}],
                [{"type": "item", "item": "Random Epic Weapon"}],
                "black_market"
            ),
            "cursed_wager": Quest(
                "cursed_wager", "The Cursed Wager",
                "Clear the entire next floor while wearing the Cursed Ring of Fragility (max HP = 10).",
                [{"type": "special", "target": "clear_floor_with_ring", "amount": 1, "current": 0}],
                [{"type": "gold", "value": 1000}, {"type": "item", "item": "Ring of the Survivor"}],
                "black_market"
            ),
            "smuggler_run": Quest(
                "smuggler_run", "Smuggler's Run",
                "Carry the Heavy Illicit Package to the hidden statue on Floor 15.",
                [{"type": "special", "target": "deliver_package", "amount": 1, "current": 0}],
                [{"type": "shards", "value": 3}],
                "black_market"
            ),
        }
    def get_available_quests(self, npc_id, completed_ids):
        available = []
        for qid, quest in self.quests_db.items():
            if quest.npc == npc_id and not quest.completed and qid not in completed_ids:
                if qid not in [q.quest_id for q in self.active_quests]:
                    if quest.prerequisite is None or quest.prerequisite in completed_ids:
                        available.append(quest)
        return available
    def accept_quest(self, quest_id):
        quest = self.quests_db[quest_id]
        if quest not in self.active_quests:
            self.active_quests.append(quest)
        return quest
    def update_progress(self, event_type, target=None, amount=1, **kwargs):
        for quest in self.active_quests[:]:
            updated = False
            for obj in quest.objectives:
                if obj["type"] == event_type:
                    if target is None or obj["target"] == target:
                        obj["current"] += amount
                        updated = True
                elif event_type == "special" and obj["type"] == "special" and obj["target"] == target:
                    obj["current"] += amount
                    updated = True
            if updated:
                if all(obj["current"] >= obj["amount"] for obj in quest.objectives):
                    self.complete_quest(quest)
    def complete_quest(self, quest):
        quest.completed = True
        self.active_quests.remove(quest)
        self.completed_quests.append(quest.quest_id)
        return quest.rewards
    def to_dict(self):
        return {
            "active": [q.to_dict() for q in self.active_quests],
            "completed": self.completed_quests
        }
    def from_dict(self, data):
        self.completed_quests = data.get("completed", [])
        self.active_quests = []
        for qd in data.get("active", []):
            q = Quest.from_dict(qd)
            if q.quest_id in self.quests_db:
                dbq = self.quests_db[q.quest_id]
                dbq.objectives = q.objectives
                dbq.completed = q.completed
                self.active_quests.append(dbq)
            else:
                self.active_quests.append(q)

# ============================== HERO CLASS ==============================
class Hero(StatusAware):
    SET_BONUSES = {
        ("Hood of Shadows", "Muffled Treads", "Phase Dagger"): {
            "name": "Ghost of Aethelgard",
            "effect": {"dodge_chance": 0.15, "alarm_immunity": True}
        },
        ("Glacial Plate", "Boots of Levitation", "Ice Lance"): {
            "name": "Permafrost",
            "effect": {"chill_on_hit": True, "freeze_resist": 0.5}
        },
        ("Crown of the Mad King", "Aethelgard's Regret", "The Beating Heart Amulet"): {
            "name": "Fallen King's Torment",
            "effect": {"damage_mult": 1.25, "health_drain": 0.02}
        },
        ("Dragon Scale Mail", "Ring of the Salamander", "Fireball"): {
            "name": "Inferno Heart",
            "effect": {"fire_resist": 0.75, "fire_damage_mult": 1.5}
        }
    }

    def __init__(self, name, hero_type, meta: MetaProgression = None):
        super().__init__()
        self.name = name
        self.hero_type = hero_type
        self.level = 1
        self.xp = 0
        self.xp_to_next = 100
        self.gold = 300
        self.scrap_metal = 5
        self.meta = meta
        base = HERO_TYPES[hero_type]["base_stats"]
        self.base_hp = base["hp"]
        self.base_mp = base["mp"]
        self.base_attack = base["attack"]
        self.base_defense = base["defense"]
        self.base_magic = base["magic"]
        if meta:
            self.base_hp = int(self.base_hp * meta.get_hp_multiplier())
            self.base_mp = int(self.base_mp * meta.get_mp_multiplier())
        self.max_hp = self.base_hp
        self.hp = self.max_hp
        self.max_mp = self.base_mp
        self.mp = self.max_mp
        self.attack = self.base_attack
        self.defense = self.base_defense
        self.magic = self.base_magic
        self.magic_resist = self.base_magic
        self.heat = 0
        self.berserker_rage_turns = 0
        self.ethereal_turns = 0
        self.inventory = []
        self.weapon = None
        self.armor = None
        self.accessory = None
        self.head_armor = None
        self.chest_armor = None
        self.legs_armor = None
        self.boss_cores = []
        self.locker = []
        self.weapons_inventory = []
        self.spellbook = [Spell("Fireball"), Spell("Lesser Heal")]
        self.active_spells = [self.spellbook[0], self.spellbook[1]]
        self.active_passive = None
        self.runes = []
        self.movement_penalty = 0
        self.dodge_chance = 0.05
        self.giant_strength_turns = 0
        self.physical_nerf_turns = 0
        self.phoenix_blessing_turns = 0
        self.void_mana_turns = 0
        self.gold_skin_turns = 0
        self.dodge_buff_turns = 0
        self.dodge_buff_amount = 0
        self.displacement_teleport_turns = 0
        self.miasma_store = False
        self.bonus_hp = 0
        self.bonus_mp = 0
        self.scavenger_bonus = 0
        self.fire_resist = 0
        self.ignite_on_hit = 0
        self.gold_mult = 1.0
        self.shop_markup = 1.0
        self.bandit_coin = False
        self.ouroboros = False
        self.heart_revive = False
        self.void_teleport = False
        self.heart_used = False
        self.thorn_percent = 0
        self.stealth = 0
        self.chill_on_hit = False
        self.spawn_grub = False
        self.mad_crown = False
        self.mad_crown_counter = 0
        self.recall_cast_counter = 0
        self.anvil_buff_turns = 0
        self.anvil_buff_damage = 0
        self.set_bonus_active = None
        self.alarm_immunity = False
        self.freeze_resist = 0
        self.damage_mult = 1.0
        self.health_drain = 0
        self.fire_damage_mult = 1.0
        self.ui = None
        # Quest-related flags
        self.prototype_blade_equipped = False
        self.prototype_blade_kills = 0
        self.spell_only_kills_this_floor = 0
        self.cursed_ring_equipped = False
        self.heavy_package_carried = False
        self.soul_gem_equipped = False
        self.poison_immunity = False
        self.archmage_flow = False
        self.shop_discount = 0.0
        self._init_starting_equipment()
        self._recalc_stats()
    def _init_starting_equipment(self):
        start_weapon_type = random.choice(list(WEAPON_TYPES.keys()))
        self.weapon = Weapon(start_weapon_type, 0, [])
        basic_chest = ARMOR_PIECES["Boiled Leather Tunic"]
        basic_head = ARMOR_PIECES["Leather Cap"]
        basic_legs = ARMOR_PIECES["Leather Leggings"]
        self.equip_armor(basic_head, None)
        self.equip_armor(basic_chest, None)
        self.equip_armor(basic_legs, None)
        self.inventory.append(Item("Minor Health Potion","Minor Health Potion","consumable",30,{"hp":20},"Restores 20 HP."))
        self.inventory.append(Item("Minor Mana Elixir","Minor Mana Elixir","consumable",25,{"mp":15},"Restores 15 MP."))
        self.inventory.append(Item("Healing Salve","Healing Salve","consumable",20,{"hp":15},"Restores 15 HP gradually."))
    def _has_item_equipped(self, item_name):
        return (self.head_armor and self.head_armor.name == item_name) or \
               (self.chest_armor and self.chest_armor.name == item_name) or \
               (self.legs_armor and self.legs_armor.name == item_name) or \
               (self.weapon and self.weapon.weapon_type == item_name) or \
               (self.accessory and self.accessory.name == item_name)
    def update_set_bonus(self):
        self.alarm_immunity = False
        self.chill_on_hit = False
        self.freeze_resist = 0
        self.damage_mult = 1.0
        self.health_drain = 0
        self.fire_resist = min(self.fire_resist, 0.75)
        self.fire_damage_mult = 1.0
        self.set_bonus_active = None
        for combo, bonus in self.SET_BONUSES.items():
            if all(self._has_item_equipped(item) for item in combo):
                self.set_bonus_active = bonus["name"]
                for stat, value in bonus["effect"].items():
                    if stat == "dodge_chance":
                        self.dodge_chance += value
                    elif stat == "alarm_immunity":
                        self.alarm_immunity = True
                    elif stat == "chill_on_hit":
                        self.chill_on_hit = True
                    elif stat == "freeze_resist":
                        self.freeze_resist = value
                    elif stat == "damage_mult":
                        self.damage_mult = value
                    elif stat == "health_drain":
                        self.health_drain = value
                    elif stat == "fire_resist":
                        self.fire_resist = max(self.fire_resist, value)
                    elif stat == "fire_damage_mult":
                        self.fire_damage_mult = value
                if self.ui:
                    self.ui.log_message(f"Set bonus activated: {bonus['name']}!")
                break
    def _recalc_stats(self):
        bonus_attack = 0; bonus_defense = 0; bonus_magic = 0; bonus_hp = self.bonus_hp; bonus_mp = self.bonus_mp
        if self.weapon and not self.weapon.is_broken():
            bonus_attack += self.weapon.damage
            if self.weapon.mechanic == "bulwark": bonus_defense += 5
        if self.armor: bonus_defense += self.armor.stat_bonus.get("defense",0)
        if self.accessory:
            bonus_hp += self.accessory.stat_bonus.get("hp",0)
            bonus_mp += self.accessory.stat_bonus.get("mp",0)
            bonus_magic += self.accessory.stat_bonus.get("magic",0)
        phys_def = 0; mag_res = 0; self.movement_penalty = 0
        if self.head_armor:
            phys_def += self.head_armor.phys_def
            mag_res += self.head_armor.mag_res
            self.movement_penalty += self.head_armor.movement_mod
        if self.chest_armor:
            phys_def += self.chest_armor.phys_def
            mag_res += self.chest_armor.mag_res
            self.movement_penalty += self.chest_armor.movement_mod
        if self.legs_armor:
            phys_def += self.legs_armor.phys_def
            mag_res += self.legs_armor.mag_res
            self.movement_penalty += self.legs_armor.movement_mod
        if self.active_passive == "Mana Well": bonus_mp = int(self.base_mp * 0.5)
        if self.active_passive == "Toughness": bonus_hp = int(self.base_hp * 0.5)
        if self.active_passive == "Hardened Scales": bonus_defense += 10
        self.attack = self.base_attack + bonus_attack
        self.defense = self.base_defense + bonus_defense + phys_def + self.level
        self.magic = self.base_magic + bonus_magic
        self.magic_resist = mag_res
        self.max_hp = self.base_hp + bonus_hp
        self.max_mp = self.base_mp + bonus_mp
        self.hp = min(self.hp, self.max_hp)
        self.mp = min(self.mp, self.max_mp)
        self.dodge_chance = 0.05 + (self.movement_penalty * 0.02) + (self.active_passive == "Light Foot" and 0.1 or 0)
        if self.dodge_buff_turns > 0: self.dodge_chance += self.dodge_buff_amount
        self.dodge_chance = max(0.0, min(0.6, self.dodge_chance))
        self.update_set_bonus()
    def equip_armor(self, armor, game_engine):
        if armor.slot == "head":
            if self.head_armor: self.inventory.append(Item(self.head_armor.name,self.head_armor.name,"armor",0,{},self.head_armor.description))
            self.head_armor = armor
        elif armor.slot == "chest":
            if self.chest_armor: self.inventory.append(Item(self.chest_armor.name,self.chest_armor.name,"armor",0,{},self.chest_armor.description))
            self.chest_armor = armor
        elif armor.slot == "legs":
            if self.legs_armor: self.inventory.append(Item(self.legs_armor.name,self.legs_armor.name,"armor",0,{},self.legs_armor.description))
            self.legs_armor = armor
        else: return
        for i,item in enumerate(self.inventory):
            if item.name == armor.name:
                self.inventory.pop(i)
                break
        if armor.property_func and game_engine: armor.property_func(self, game_engine)
        self._recalc_stats()
    def unequip_armor(self, slot):
        if slot == "head" and self.head_armor:
            self.inventory.append(Item(self.head_armor.name,self.head_armor.name,"armor",0,{},self.head_armor.description))
            self.head_armor = None
        elif slot == "chest" and self.chest_armor:
            self.inventory.append(Item(self.chest_armor.name,self.chest_armor.name,"armor",0,{},self.chest_armor.description))
            self.chest_armor = None
        elif slot == "legs" and self.legs_armor:
            self.inventory.append(Item(self.legs_armor.name,self.legs_armor.name,"armor",0,{},self.legs_armor.description))
            self.legs_armor = None
        else: return
        self._recalc_stats()
    def equip_accessory(self, accessory, game_engine):
        if self.accessory: self.inventory.append(Item(self.accessory.name,self.accessory.name,"accessory",self.accessory.value,{},self.accessory.description))
        self.accessory = accessory
        for i,item in enumerate(self.inventory):
            if item.name == accessory.name:
                self.inventory.pop(i)
                break
        if accessory.effect_func: accessory.effect_func(self, game_engine)
        self._recalc_stats()
    def unequip_accessory(self):
        if self.accessory:
            self.inventory.append(Item(self.accessory.name,self.accessory.name,"accessory",self.accessory.value,{},self.accessory.description))
            self.accessory = None
            self._recalc_stats()
    def equip_weapon(self, weapon):
        if self.weapon: self.weapons_inventory.append(self.weapon)
        self.weapon = weapon
        self._recalc_stats()
    def unequip_weapon(self):
        if self.weapon:
            self.weapons_inventory.append(self.weapon)
            self.weapon = None
            self._recalc_stats()
    def add_xp(self, amount):
        if self.active_passive == "Scholar": amount = int(amount * 1.15)
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level_up()
    def level_up(self):
        self.level += 1
        self.xp_to_next = int(self.xp_to_next * 1.2)
        if self.hero_type == "Orc Berserker":
            self.base_hp += 15; self.base_attack += 3
        elif self.hero_type == "Elf Aether-Mage":
            self.base_mp += 12; self.base_magic += 4
        elif self.hero_type == "Dwarf Runesmith":
            self.base_defense += 4; self.base_hp += 10
        elif self.hero_type == "Nightblade":
            self.base_attack += 3; self.base_magic += 2
        elif self.hero_type == "Necromancer":
            self.base_mp += 10; self.base_magic += 3; self.base_hp += 8
        else:
            self.base_hp += 12; self.base_attack += 2; self.base_defense += 2
        self.max_hp = self.base_hp
        self.max_mp = self.base_mp
        self.hp = self.max_hp
        self.mp = self.max_mp
        self._recalc_stats()
    def take_damage(self, dmg):
        if self.has_status("Crystallized") and self.last_damage_type == "blunt":
            dmg = int(dmg * 2)
            self.remove_status("Crystallized")
        if self.hero_type == "Elf Aether-Mage" and self.ethereal_turns > 0: return 0
        if self.fire_resist > 0 and random.random() < self.fire_resist: dmg = int(dmg * (1 - self.fire_resist))
        if self.gold_skin_turns > 0: dmg = max(1, dmg - 50)
        actual = max(1, dmg - self.defense // 2)
        self.hp -= actual
        if self.hp < 0: self.hp = 0
        if self.hp <= 0 and self.heart_revive and not self.heart_used:
            self.hp = int(self.max_hp * 0.5)
            self.max_hp -= 10
            self.heart_used = True
            self.heart_revive = False
            return 0
        if self.hp <= 0 and hasattr(self, 'martyr_halo') and self.martyr_halo:
            self.hp = int(self.max_hp * 0.5)
            self.martyr_halo = False
            return 0
        return actual
    def heal(self, amount):
        if self.active_passive == "Alchemist": amount = int(amount * 1.5)
        if self.ouroboros: self.mp = min(self.max_mp, self.mp + amount)
        else: self.hp = min(self.max_hp, self.hp + amount)
    def restore_mp(self, amount):
        if self.active_passive == "Alchemist": amount = int(amount * 1.5)
        if self.ouroboros: self.hp = min(self.max_hp, self.hp + amount)
        else: self.mp = min(self.max_mp, self.mp + amount)
    def special_ability(self, game_engine):
        ht = self.hero_type
        if ht == "Orc Berserker":
            cost = int(self.max_hp * 0.15)
            if self.hp > cost:
                self.hp -= cost
                self.berserker_rage_turns = 3
                return ("Blood Rage activated! Double attack + 50% lifesteal for 3 turns.", True)
            else: return ("Not enough health!", False)
        elif ht == "Elf Aether-Mage":
            if self.mp >= 20:
                self.mp -= 20
                self.ethereal_turns = 1
                return ("Aetherial Shift: Ethereal for 1 turn.", True)
            else: return ("Not enough mana!", False)
        elif ht == "Dwarf Runesmith":
            if self.mp >= 15:
                self.mp -= 15
                game_engine.active_rune_absorb = 20
                return ("Rune of Warding placed! Absorbs 20 damage.", True)
            else: return ("Not enough mana!", False)
        elif ht == "Nightblade":
            if self.mp >= 10:
                self.mp -= 10
                game_engine.shadow_step_backstab = True
                return ("Shadow Step! Next attack is guaranteed critical.", True)
            else: return ("Not enough mana!", False)
        elif ht == "Automaton Sentinel":
            if self.heat <= 80:
                self.heat = 100
                return ("Overdrive Beam! Abilities disabled for 2 turns.", True)
            else: return ("Heat too high!", False)
        elif ht == "Necromancer":
            if len(game_engine.combat_monsters) > 0:
                return ("Soul Harvest: Restore HP equal to damage dealt on kill.", True)
            else:
                return ("No fallen enemies to raise.", False)
        return ("No special ability.", False)
    def update_buffs(self, game_engine):
        if self.berserker_rage_turns > 0: self.berserker_rage_turns -= 1
        if self.ethereal_turns > 0: self.ethereal_turns -= 1
        if self.hero_type == "Automaton Sentinel" and self.heat > 0: self.heat = max(0, self.heat - 20)
        if self.mad_crown:
            self.mad_crown_counter += 1
            if self.mad_crown_counter >= 3:
                self.mad_crown_counter = 0
                game_engine.scrambled_movement = 1
                game_engine.ui.log_message("Mad King's crown scrambles your controls!")
        if self.giant_strength_turns > 0:
            self.giant_strength_turns -= 1
            if self.giant_strength_turns == 0: game_engine.ui.log_message("Giant's Blood wears off.")
        if self.physical_nerf_turns > 0: self.physical_nerf_turns -= 1
        if self.phoenix_blessing_turns > 0: self.phoenix_blessing_turns -= 1
        if self.void_mana_turns > 0:
            self.void_mana_turns -= 1
            if self.void_mana_turns == 0:
                self.mp = 0
                game_engine.ui.log_message("Liquid Void effect ends: your mana is drained to 0.")
        if self.gold_skin_turns > 0:
            self.gold_skin_turns -= 1
            if self.gold_skin_turns == 0:
                self.gold += 100
                game_engine.ui.log_message("Liquid Gold hardens: you gain 100 gold!")
        if self.dodge_buff_turns > 0: self.dodge_buff_turns -= 1
        if self.displacement_teleport_turns > 0:
            self.displacement_teleport_turns -= 1
            if self.displacement_teleport_turns > 0 and not game_engine.in_combat:
                dx = random.choice([-1,0,1]); dy = random.choice([-1,0,1])
                game_engine.move(dx, dy)
        if self.recall_cast_counter > 0:
            self.recall_cast_counter -= 1
            if self.recall_cast_counter == 0:
                game_engine.teleport_to_safe_zone()
                game_engine.ui.log_message("Recall Scroll activates! You return to the Safe Zone.")
        if self.anvil_buff_turns > 0: self.anvil_buff_turns -= 1
        if self.health_drain > 0:
            drain = int(self.max_hp * self.health_drain)
            self.take_damage(drain)
            game_engine.ui.log_message(f"The set bonus drains {drain} HP from you.")
        self._recalc_stats()
    def get_attack_bonus(self):
        bonus = 1.0
        if self.berserker_rage_turns > 0: bonus *= 2.0
        if self.mad_crown: bonus *= 2.0
        if self.active_passive == "Berserker's Spirit":
            hp_ratio = self.hp / self.max_hp
            bonus *= (1 + (1 - hp_ratio) * 0.5)
        if self.giant_strength_turns > 0: bonus += 5
        if self.physical_nerf_turns > 0: bonus *= 0.5
        bonus *= self.damage_mult
        return bonus
    def get_lifesteal_percent(self): return 0.5 if self.berserker_rage_turns > 0 else 0.0
    def use_consumable(self, consumable, game_engine):
        if consumable.effect_func: consumable.effect_func(self, game_engine)
        if consumable.name == "Recall Scroll":
            if game_engine.in_combat:
                game_engine.ui.log_message("You start casting Recall Scroll... (2 turns)")
                self.recall_cast_counter = 2
            else: game_engine.teleport_to_safe_zone()
        elif consumable.name == "Scholar's Monocle":
            for item in self.inventory: item.identified = True
            game_engine.ui.log_message("Scholar's Monocle identifies all items in your inventory.")
        elif consumable.name == "Skeleton Key":
            game_engine.skeleton_key_used = True
            game_engine.ui.log_message("Skeleton Key used. Opens any lock.")
        elif consumable.name == "Miner's Dynamite":
            if game_engine.in_combat:
                for m in game_engine.combat_monsters: m.take_damage(30)
                game_engine.ui.log_message("Dynamite explodes, dealing 30 damage to all enemies!")
            else:
                game_engine.dynamite_used = True
                game_engine.ui.log_message("Dynamite blasts open a secret passage!")
        elif consumable.name == "Panacea Ointment":
            for s in ["Bleed","Rooted","Stunned","Poison","Soul-Burn"]:
                if s in self.active_statuses: del self.active_statuses[s]
            game_engine.ui.log_message("Panacea Ointment cures all physical ailments.")
        elif consumable.name == "Void Chalk":
            game_engine.void_chalk_charges = 3
            game_engine.ui.log_message("Void Chalk ready. Use 'Draw Glyph' button (3 charges).")
        elif consumable.name == "Blank Rune Slab":
            game_engine.rune_slab_available = True
            game_engine.ui.log_message("Blank Rune Slab added to crafting inventory. Visit Blacksmith to transfer enchantments.")
        self._recalc_stats()
    def get_durability_multiplier(self) -> float:
        if self.meta: return 1.0 - self.meta.get_durability_reduction()
        return 1.0
    def to_dict(self):
        return {
            "name":self.name,"hero_type":self.hero_type,"level":self.level,"xp":self.xp,
            "xp_to_next":self.xp_to_next,"gold":self.gold,"scrap_metal":self.scrap_metal,
            "base_hp":self.base_hp,"base_mp":self.base_mp,"base_attack":self.base_attack,
            "base_defense":self.base_defense,"base_magic":self.base_magic,"hp":self.hp,
            "mp":self.mp,"heat":self.heat,"inventory":[i.to_dict() for i in self.inventory],
            "weapon":self.weapon.to_dict() if self.weapon else None,
            "armor":self.armor.to_dict() if self.armor else None,
            "accessory":self.accessory.to_dict() if self.accessory else None,
            "head_armor":self.head_armor.to_dict() if self.head_armor else None,
            "chest_armor":self.chest_armor.to_dict() if self.chest_armor else None,
            "legs_armor":self.legs_armor.to_dict() if self.legs_armor else None,
            "boss_cores":self.boss_cores,"locker":[w.to_dict() for w in self.locker],
            "weapons_inventory":[w.to_dict() for w in self.weapons_inventory],
            "spellbook":[s.to_dict() for s in self.spellbook],
            "active_spells":[s.to_dict() for s in self.active_spells],
            "active_passive":self.active_passive,"runes":[r.to_dict() for r in self.runes],
            "heart_used":self.heart_used
        }
    @classmethod
    def from_dict(cls, data, meta=None):
        hero = cls(data["name"], data["hero_type"], meta)
        hero.level = data["level"]
        hero.xp = data["xp"]
        hero.xp_to_next = data["xp_to_next"]
        hero.gold = data["gold"]
        hero.scrap_metal = data.get("scrap_metal",0)
        hero.base_hp = data["base_hp"]
        hero.base_mp = data["base_mp"]
        hero.base_attack = data["base_attack"]
        hero.base_defense = data["base_defense"]
        hero.base_magic = data["base_magic"]
        hero.hp = data["hp"]
        hero.mp = data["mp"]
        hero.heat = data.get("heat",0)
        hero.inventory = [Item.from_dict(i) for i in data["inventory"]]
        hero.weapon = Weapon.from_dict(data["weapon"]) if data["weapon"] else None
        hero.armor = Item.from_dict(data["armor"]) if data["armor"] else None
        hero.accessory = Accessory.from_dict(data["accessory"]) if data.get("accessory") else None
        hero.head_armor = Armor.from_dict(data["head_armor"]) if data.get("head_armor") else None
        hero.chest_armor = Armor.from_dict(data["chest_armor"]) if data.get("chest_armor") else None
        hero.legs_armor = Armor.from_dict(data["legs_armor"]) if data.get("legs_armor") else None
        hero.boss_cores = data.get("boss_cores",[])
        hero.locker = [Weapon.from_dict(w) for w in data.get("locker",[])]
        hero.weapons_inventory = [Weapon.from_dict(w) for w in data.get("weapons_inventory",[])]
        hero.spellbook = [Spell.from_dict(s) for s in data.get("spellbook",[])]
        hero.active_spells = [Spell.from_dict(s) for s in data.get("active_spells",[])]
        hero.active_passive = data.get("active_passive")
        hero.runes = [Rune.from_dict(r) for r in data.get("runes",[])]
        hero.heart_used = data.get("heart_used",False)
        hero._recalc_stats()
        if hero.accessory and hero.accessory.effect_func: hero.accessory.effect_func(hero, None)
        return hero

# ============================== DUNGEON ==============================
class Dungeon:
    def __init__(self, seed=None, game_engine=None):
        self.seed = seed if seed else random.randint(1,1000000)
        random.seed(self.seed)
        self.current_level = 1
        self.max_level = MAX_LEVEL
        self.levels = {}
        self.game_engine = game_engine
        self.generate_level(self.current_level)
    def generate_level(self, level):
        random.seed(self.seed + level)
        grid = [[None for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
        boss_x, boss_y = random.randint(MAP_WIDTH-3, MAP_WIDTH-1), random.randint(MAP_HEIGHT-3, MAP_HEIGHT-1)
        grid[boss_y][boss_x] = {"type":"boss","monsters":[Boss(level)],"visited":False,"cleared":False,"features":[]}
        if level < self.max_level:
            for _ in range(10):
                sx, sy = random.randint(0,MAP_WIDTH-1), random.randint(0,MAP_HEIGHT-1)
                if grid[sy][sx] is None and (abs(sx-boss_x)+abs(sy-boss_y))>3:
                    grid[sy][sx] = {"type":"shop","visited":False,"cleared":True,"features":[]}
                    break
        treasure_count = 4 + level//3
        for _ in range(treasure_count):
            for _ in range(30):
                tx, ty = random.randint(0,MAP_WIDTH-1), random.randint(0,MAP_HEIGHT-1)
                if grid[ty][tx] is None:
                    grid[ty][tx] = {"type":"treasure","visited":False,"cleared":True,"looted":False,"features":[]}
                    break
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if grid[y][x] is None:
                    monster_count = 1 + (level//4) + random.randint(0,1)
                    monsters = [self._create_random_monster(level) for _ in range(monster_count)]
                    features = self._generate_room_features(level)
                    grid[y][x] = {"type":"normal","monsters":monsters,"visited":False,"cleared":False,"features":features}
        grid[0][0] = {"type":"normal","monsters":[],"visited":True,"cleared":True,"features":[]}
        self.levels[level] = {"grid":grid}
        random.seed()
    def _create_random_monster(self, level):
        if level >= 5 and random.random() < 0.02 and self.game_engine and self.game_engine.meta.last_death:
            return FallenHero(self.game_engine.meta.last_death, level, self.game_engine)
        names = ["Goblin","Orc","Skeleton","Dark Cultist","Giant Rat","Troll","Ghoul","Harpy","Minotaur","Wraith"]
        name = random.choice(names)
        hp = 20 + level*2
        atk = 8 + level
        defense = 3 + level//2
        xp = 30 + level*3
        gold = 15 + level*2
        if name == "Goblin" and random.random() < 0.1 and not self.game_engine.goblin_footpad_spawned:
            self.game_engine.goblin_footpad_spawned = True
            return Monster("Goblin Footpad","elite",level,hp*1.5,atk+5,defense+2,xp*2,gold*2,"footpad",{},[])
        if name == "Ghoul" and random.random() < 0.2:
            return Monster("Putrid Shambler","undead",level,hp+10,atk-2,defense,xp+20,gold,"poison_cloud",{},[])
        if level >= 6 and level <= 10 and name == "Orc" and random.random() < 0.15:
            return Monster("Cinder Sprite","elemental",level,hp-5,atk+3,defense-2,xp+15,gold+10,"fire_burst",{},[])
        return Monster(name,"normal",level,hp,atk,defense,xp,gold,"",{},[])
    def _generate_room_features(self, level):
        features = []
        num = random.randint(0,4)
        if random.random() < 0.1:
            features.append({"symbol":"$","name":"Cursed Shrine of Aethelgard","color":COLORS["purple"],"func":feature_cursed_shrine,"desc":"A dark altar pulses with forbidden power. Do you dare make an offering?","visible":True})
        for _ in range(num):
            feat_symbol = random.choice(list(FEATURES.keys()))
            name, color, func, desc, visible = FEATURES[feat_symbol]
            features.append({"symbol":feat_symbol,"name":name,"color":color,"func":func,"desc":desc,"visible":visible})
        return features
    def get_current_room(self, x, y):
        if 0<=x<MAP_WIDTH and 0<=y<MAP_HEIGHT:
            return self.levels[self.current_level]["grid"][y][x]
        return None
    def move_to_level(self, level):
        if level not in self.levels: self.generate_level(level)
        self.current_level = level

class FallenHero(Monster):
    def __init__(self, hero_data, current_level, game_engine):
        name = f"Zombified {hero_data['hero_type']}"
        hp = int(hero_data["max_hp"] * (0.8 + 0.1 * current_level/10))
        atk = hero_data["attack"] + current_level//2
        defense = hero_data["defense"] + current_level//3
        xp = 100 + current_level*10
        gold = hero_data["gold"] // 4
        super().__init__(name, "undead", current_level, hp, atk, defense, xp, gold, "zombie_rage", {}, [])
        self.weapon_type = hero_data["weapon"]["weapon_type"] if hero_data["weapon"] else None
        self.game_engine = game_engine
    def use_boss_ability(self, hero, game_engine):
        if self.ability == "zombie_rage" and random.random() < 0.3:
            hero.apply_status("Bleed", 3, 3)
            self.attack += 2
            game_engine.ui.combat_text.insert(tk.END, f"{self.name} enters a rage! Bleed applied and attack increased.\n")
            return True
        return False

# ============================== COMBAT ENGINE ==============================
class CombatEngine:
    @staticmethod
    def player_attack(hero, monster, is_backstab=False, from_side=False):
        if hero.has_status("Stunned"): return f"{hero.name} is stunned and cannot attack!", 0
        if random.random() < hero.dodge_chance: return f"{monster.name} dodges the attack!", 0
        if hero.weapon and hero.weapon.is_broken():
            damage = max(1, hero.attack//10)
            dealt = monster.take_damage(damage)
            return f"Weapon broken! {dealt} damage.", dealt
        if hero.weapon:
            if hero.weapon.weapon_type == "Whispering Blade":
                if not hasattr(hero,'whisper_kills'): hero.whisper_kills = 0
                damage = hero.attack + hero.whisper_kills
            elif hero.weapon.weapon_type == "Aethelgard's Regret":
                hp_cost = int(hero.max_hp * 0.05)
                if hero.hp > hp_cost: hero.hp -= hp_cost
                else: return f"Not enough HP to swing Aethelgard's Regret!", 0
            dura_cost = 2 if hero.weapon.mechanic == "volley" else 1
            actual_dura_cost = max(1, int(dura_cost * hero.get_durability_multiplier()))
            hero.weapon.use_durability(actual_dura_cost)
        damage = hero.attack + random.randint(-2,2)
        damage = int(damage * hero.get_attack_bonus())
        desperation = (hero.hp == 1 and hero.hp < hero.max_hp)
        if desperation:
            is_backstab = True
            monster.apply_status("Bleed", 3, 5)
        if is_backstab:
            mult = 3 if (hero.weapon and hero.weapon.mechanic == "backstab") else 2
            damage = int(damage * mult)
        damage = max(1, damage)
        msg = ""
        if desperation:
            msg += "Desperation strike! "
        if hero.weapon and hero.weapon.mechanic in ["impact","heavy_swing"]:
            hero.last_damage_type = "blunt"
        else: hero.last_damage_type = "physical"
        if hero.weapon:
            if hero.weapon.mechanic == "impact" and random.random()<0.2: msg += "Impact! "
            if hero.weapon.mechanic == "bleed":
                monster.apply_status("Bleed",3,2)
                msg += "Bleed applied! "
            if hero.weapon.mechanic == "reap" and monster.hp <= monster.max_hp*0.15:
                if not isinstance(monster,Boss):
                    damage = monster.hp
                    msg += "Reap execution! "
            if hero.weapon.mechanic == "undead_bane" and "undead" in monster.monster_type:
                damage *= 2
                msg += "Undead bane! "
            if hero.weapon.mechanic == "stun_chance" and random.random()<0.1:
                monster.apply_status("Stunned",1)
                msg += "Stunned! "
            if hero.weapon.mechanic == "storm_bonus" and (hasattr(hero,'last_spell_lightning') or "water" in monster.name):
                damage = int(damage * 1.5)
                msg += "Storm bonus! "
            if hero.weapon.mechanic == "bleed_repair" and monster.has_status("Bleed"):
                hero.weapon.repair(2)
                msg += "Blood-Letting Cleaver repairs 2 durability! "
            if hero.weapon.mechanic == "mana_drain":
                drain = min(5, monster.mp if hasattr(monster,'mp') else 0)
                hero.restore_mp(drain)
                msg += f"Mana drain +{drain} MP! "
            if hero.weapon.mechanic == "paradox":
                if random.random()<0.75:
                    damage *= 3
                    msg += "Paradox critical! "
                else:
                    monster.hp = monster.max_hp
                    msg += "Paradox backfire! Enemy fully healed! "
        if hasattr(hero,'ignite_on_hit') and random.random()<hero.ignite_on_hit:
            monster.apply_status("Soul-Burn",3,3)
            msg += "Enemy ignited! "
        if hero.bandit_coin and monster.hp - damage == 1:
            damage = monster.hp
            msg += "Bandit's Coin: enemy flees! "
        if hero.miasma_store:
            monster.apply_status("Bleed",3,5)
            monster.apply_status("Soul-Burn",3,3)
            hero.miasma_store = False
            msg += "Miasma transfers your debuffs to the enemy! "
        if hero.anvil_buff_turns > 0:
            damage += hero.anvil_buff_damage
            msg += "Anvil fire damage! "
        dealt = monster.take_damage(damage, from_side, False) if isinstance(monster,Boss) else monster.take_damage(damage)
        if hero.weapon and "Life-Drain" in hero.weapon.magic_abilities:
            heal = int(dealt * 0.05)
            hero.heal(heal)
            msg += f"Life-Drain +{heal} HP. "
        lifesteal = hero.get_lifesteal_percent()
        if lifesteal > 0:
            heal = int(dealt * lifesteal)
            hero.heal(heal)
            msg += f"Lifesteal +{heal} HP. "
        if hero.hero_type == "Necromancer" and not monster.is_alive():
            heal_amount = dealt // 2
            hero.heal(heal_amount)
            msg += f"Necromancer's Soul Harvest restores {heal_amount} HP! "
        return f"{msg}{hero.name} hits {monster.name} for {dealt} damage!", dealt
    @staticmethod
    def player_cast_spell(hero, spell, monster, game_engine):
        if hero.has_status("Stunned"): return "You are stunned and cannot cast!", 0
        if getattr(monster,'silenced_turns',0)>0: return "You are silenced!", 0
        cost = spell.get_cost()
        if hero.void_mana_turns > 0: cost = 0
        if hero.active_passive == "Blood Magic":
            if hero.hp > cost: hero.hp -= cost
            else: return "Not enough HP for Blood Magic!", 0
        else:
            if hero.mp >= cost: hero.mp -= cost
            else: return "Not enough mana!", 0
        for rune in hero.runes:
            if "mana_cost_reduction" in RUNES[rune.name]: hero.mp = min(hero.mp+5, hero.max_mp)
        if spell.current_cooldown > 0: return f"{spell.name} on cooldown ({spell.current_cooldown} turns).", 0
        data = spell.data
        effect = data["effect"]
        msg = ""
        damage = 0
        spell_damage = spell.get_damage()
        for rune in hero.runes:
            if "spell_damage_mult" in RUNES[rune.name]: spell_damage = int(spell_damage * 1.1)
        if hero.ouroboros: hero.heal(cost)
        spell_element = None
        if "Fire" in spell.name: spell_element = "fire"
        elif "Ice" in spell.name or "Frost" in spell.name: spell_element = "ice"
        elif "Lightning" in spell.name or "Chain" in spell.name: spell_element = "lightning"
        elif "Earth" in spell.name: spell_element = "earth"
        if spell_element == "fire" and monster.has_status("Frozen"):
            monster.remove_status("Frozen")
            monster.take_damage(40)
            msg += "Thermal shock! The frozen enemy explodes for 40 damage! "
        if spell_element == "earth" and monster.has_status("Drenched"):
            monster.remove_status("Drenched")
            monster.apply_status("Rooted",3)
            msg += "Mud trap! The enemy is rooted! "
        if effect == "aoe_damage":
            damage = spell_damage + random.randint(0,10)
            dealt = monster.take_damage(damage, False, True) if isinstance(monster,Boss) else monster.take_damage(damage)
            msg = f"{spell.name} deals {dealt} damage!"
        elif effect == "damage_slow":
            damage = spell_damage + random.randint(0,8)
            dealt = monster.take_damage(damage, False, True) if isinstance(monster,Boss) else monster.take_damage(damage)
            monster.apply_status("Rooted", data["slow_turns"])
            msg = f"{spell.name} deals {dealt} damage and slows!"
        elif effect == "chain_damage":
            total = 0
            for i,m in enumerate(game_engine.combat_monsters):
                if i >= data["max_targets"]: break
                d = spell_damage + random.randint(0,5)
                dmg = m.take_damage(d, False, True) if isinstance(m,Boss) else m.take_damage(d)
                total += dmg
            msg = f"{spell.name} hits {min(len(game_engine.combat_monsters),data['max_targets'])} enemies for {total} total damage!"
        elif effect == "armor_penetration":
            original_def = monster.defense
            monster.defense = int(monster.defense * (1 - data["penetration"]))
            damage = spell_damage + random.randint(0,10)
            dealt = monster.take_damage(damage, False, True) if isinstance(monster,Boss) else monster.take_damage(damage)
            monster.defense = original_def
            msg = f"{spell.name} ignores armor, dealing {dealt} damage!"
        elif effect == "push_back":
            msg = f"{spell.name} pushes enemies back!"
        elif effect == "reduce_defense":
            monster.defense -= data["defense_reduction"]
            msg = f"{spell.name} reduces defense by {data['defense_reduction']}!"
        elif effect == "blind":
            monster.apply_status("Blind", data["blind_turns"])
            msg = f"{spell.name} blinds the enemy!"
        elif effect == "pull_all":
            msg = f"{spell.name} pulls all enemies closer!"
        elif effect == "freeze_adjacent":
            for m in game_engine.combat_monsters:
                if m != monster: m.apply_status("Rooted", data["freeze_turns"])
            msg = f"{spell.name} freezes adjacent enemies!"
        elif effect == "teleport":
            msg = f"{spell.name} teleports you to a safe spot!"
        elif effect == "drain_hp_from_mana":
            drain = int(getattr(monster,'mp',0) * data["drain_ratio"])
            hero.heal(drain)
            msg = f"{spell.name} drains {drain} HP from mana!"
        elif effect == "flee":
            if not isinstance(monster,Boss):
                game_engine.combat_monsters.remove(monster)
                msg = f"{spell.name} makes the enemy flee!"
            else: msg = "The boss resists!"
        elif effect == "confuse":
            monster.apply_status("Confuse", data["duration"])
            msg = f"{spell.name} confuses the enemy!"
        elif effect == "bleed_double":
            monster.apply_status("Bleed",5,5)
            msg = f"{spell.name} causes massive bleeding!"
        elif effect == "silence":
            monster.apply_status("Silence", data["duration"])
            msg = f"{spell.name} silences the enemy!"
        elif effect == "root":
            monster.apply_status("Rooted", data["duration"])
            msg = f"{spell.name} roots the enemy!"
        elif effect == "double_damage_next":
            game_engine.double_damage_next = True
            msg = f"{spell.name} marks the enemy for double damage!"
        elif effect == "reveal_map":
            game_engine.reveal_map = True
            msg = f"{spell.name} reveals the map!"
        elif effect == "delayed_damage":
            game_engine.doom_tick_target = monster
            game_engine.doom_tick_counter = data["delay_turns"]
            game_engine.doom_tick_damage = data["damage"] + spell.level*10
            msg = f"{spell.name} places a doom tick!"
        elif effect == "heal":
            heal_amt = data["heal_amount"] + spell.level*5
            hero.heal(heal_amt)
            msg = f"{spell.name} heals {heal_amt} HP!"
        elif effect == "hp_to_mana":
            hp_cost = int(hero.max_hp * (data["hp_percent"]/100))
            if hero.hp > hp_cost:
                hero.hp -= hp_cost
                mana_gain = int(hero.max_mp * (data["mana_percent"]/100))
                hero.mp = min(hero.max_mp, hero.mp + mana_gain)
                msg = f"{spell.name} converts {hp_cost} HP to {mana_gain} MP!"
            else: msg = "Not enough HP!"
        elif effect == "absorb_shield":
            game_engine.absorb_shield = data["absorb_hits"]
            msg = f"{spell.name} grants a shield for {data['absorb_hits']} hits!"
        elif effect == "haste":
            game_engine.haste_turns = data["duration"]
            msg = f"{spell.name} doubles movement speed!"
        elif effect == "cleanse":
            game_engine.player_stunned = 0
            game_engine.player_rooted = 0
            game_engine.scrambled_movement = 0
            for s in ["Bleed","Soul-Burn","Rooted","Stunned","Blind","Confuse","Silence"]:
                if s in hero.active_statuses: del hero.active_statuses[s]
            msg = f"{spell.name} removes all negative effects!"
        elif effect == "regen":
            hero.apply_status("Regeneration", data["duration"], data["heal_per_turn"])
            msg = f"{spell.name} grants regeneration!"
        elif effect == "damage_reduction":
            game_engine.damage_reduction = data["reduction"]
            game_engine.damage_reduction_turns = data["duration"]
            msg = f"{spell.name} reduces damage by {int(data['reduction']*100)}%!"
        elif effect == "reflect_melee":
            game_engine.reflect_melee = data["reflect_percent"]/100
            game_engine.reflect_turns = data["duration"]
            msg = f"{spell.name} reflects {data['reflect_percent']}% melee damage!"
        elif effect == "revive_buff":
            game_engine.guardian_angel = True
            game_engine.guardian_turns = data["duration"]
            msg = f"{spell.name} will revive you!"
        elif effect == "missing_hp_damage":
            missing = hero.max_hp - hero.hp
            damage = missing + spell.level*5
            dealt = monster.take_damage(damage, False, True) if isinstance(monster,Boss) else monster.take_damage(damage)
            msg = f"{spell.name} deals {dealt} damage based on missing health!"
        elif effect == "item_to_gold":
            if hero.inventory:
                item = hero.inventory.pop(0)
                hero.gold += item.value
                msg = f"{spell.name} transmutes {item.name} into {item.value} gold!"
            else: msg = "No items to transmute!"
        elif effect == "time_stop":
            game_engine.time_stop_turns = data["duration"]
            msg = f"{spell.name} stops time for {data['duration']} turns!"
        elif effect == "decoy":
            game_engine.decoy_active = True
            msg = f"{spell.name} creates a decoy!"
        elif effect == "negate_projectiles":
            game_engine.gravity_well_turns = data["duration"]
            msg = f"{spell.name} negates projectiles!"
        elif effect == "teleport_attack":
            attack_msg, dmg = CombatEngine.player_attack(hero, monster, True, True)
            msg = f"{spell.name}: {attack_msg}"
        elif effect == "auto_loot":
            hero.gold += random.randint(10,50)
            msg = f"{spell.name} pulls in {random.randint(10,50)} gold!"
        elif effect == "petrify":
            if not isinstance(monster,Boss):
                game_engine.combat_monsters.remove(monster)
                msg = f"{spell.name} turns enemy into stone!"
            else: msg = "Boss resists!"
        elif effect == "double_cast_next":
            game_engine.double_cast_next = True
            msg = f"{spell.name} will double your next spell!"
        elif effect == "stun_line":
            for m in game_engine.combat_monsters: m.apply_status("Stunned",1)
            msg = f"{spell.name} stuns all enemies in a line!"
        elif effect == "all_mana_damage":
            damage = hero.mp * 2
            dealt = monster.take_damage(damage, False, True) if isinstance(monster,Boss) else monster.take_damage(damage)
            hero.mp = 0
            msg = f"{spell.name} consumes all mana to deal {dealt} damage!"
        spell.current_cooldown = data.get("cooldown",0) + 1
        if hero.active_passive == "Wizard's Flow": spell.current_cooldown = max(0, spell.current_cooldown - 1)
        return msg, damage

# ============================== NPC, JOURNAL, NARRATIVE DATA ==============================
class Journal:
    def __init__(self): self.entries = []; self.lore_unlocked = []
    def add_entry(self, title, content, category="lore"): self.entries.append({"title":title,"content":content,"category":category})
    def to_dict(self): return {"entries":self.entries,"lore_unlocked":self.lore_unlocked}
    @classmethod
    def from_dict(cls, data): j=cls(); j.entries=data.get("entries",[]); j.lore_unlocked=data.get("lore_unlocked",[]); return j

class NPC:
    def __init__(self, name, dialogue_tree, inventory=None, reputation=0):
        self.name=name; self.dialogue_tree=dialogue_tree; self.current_state="start"
        self.inventory=inventory or []; self.reputation=reputation
    def get_response(self, choice_idx):
        state_data = self.dialogue_tree.get(self.current_state)
        if not state_data: return "Goodbye.", True
        options = state_data.get("options",[])
        if choice_idx<0 or choice_idx>=len(options): return "I don't understand.", False
        next_state, response = options[choice_idx]
        self.current_state = next_state
        return response, (next_state=="end")
    def reset_dialogue(self): self.current_state = "start"

SHOPKEEPER_DIALOGUE = {
    "start": {"text": "Welcome, traveler! Need supplies for the depths?","options":[("shop","I'd like to browse your wares."),("quests","Do you have any tasks for me?"),("lore","Tell me about this place."),("end","Not right now, thanks.")]},
    "shop": {"text": "Take a look. Prices are fair, but my patience isn't.","options":[("buy","I want to buy something."),("sell","I want to sell something."),("start","Never mind, let's talk.")]},
    "buy": {"text": "What catches your eye?","options":[("shop","Back to shop menu.")]},
    "sell": {"text": "Let me see what you've got.","options":[("shop","Back to shop menu.")]},
    "quests": {"text": "I might have some work for a daring soul...","options":[("quest_list","Tell me about available quests."),("start","Maybe later.")]},
    "quest_list": {"text": "Choose a quest:","options":[]},
    "quest_accept": {"text": "Excellent! Return when you've completed it.","options":[("start","Farewell.")]},
    "quest_decline": {"text": "As you wish. The offer stands.","options":[("start","Thank you.")]},
    "quest_complete": {"text": "You've done it! Here's your reward.","options":[("start","Thank you!")]},
    "lore": {"text": "This dungeon was once a glorious kingdom...","options":[("start","Thank you for the warning."),("end","I must go.")]},
    "end": {"text": "May the light guide your path.","options":[]}
}

BLACKSMITH_DIALOGUE = {
    "start": {"text": "Clang! Need a weapon forged or repaired?","options":[("smithy","Smithy services"),("quests","Got any tasks?"),("end","Not now.")]},
    "smithy": {"text": "Upgrade, repair, buy, sell – I do it all.","options":[("start","Back")]},
    "quests": {"text": "I have some work for a strong arm.","options":[("quest_list","Tell me."),("start","Maybe later.")]},
    "quest_list": {"text": "Choose a quest:","options":[]},
    "quest_accept": {"text": "Good luck! Come back when it's done.","options":[("start","I will.")]},
    "quest_decline": {"text": "Suit yourself.","options":[("start","Thanks.")]},
    "quest_complete": {"text": "Fine work! Here's your reward.","options":[("start","Much appreciated.")]},
    "end": {"text": "Keep your blade sharp.","options":[]}
}

MAGIC_ALTAR_DIALOGUE = {
    "start": {"text": "The weave of magic awaits.","options":[("altar","Manage spells/passives"),("quests","Seek arcane tasks?"),("end","Not now.")]},
    "altar": {"text": "Study, learn, upgrade.","options":[("start","Back")]},
    "quests": {"text": "The Altar whispers of challenges.","options":[("quest_list","Speak them."),("start","Not interested.")]},
    "quest_list": {"text": "Choose a quest:","options":[]},
    "quest_accept": {"text": "May the currents of mana guide you.","options":[("start","I accept.")]},
    "quest_decline": {"text": "The offer fades...","options":[("start","Farewell.")]},
    "quest_complete": {"text": "The Altar pulses with gratitude. Take your reward.","options":[("start","Thank you.")]},
    "end": {"text": "The arcane awaits.","options":[]}
}

BLACK_MARKET_DIALOGUE = {
    "start": {"text": "Psst... looking for something... special?","options":[("buy","Black Market wares"),("quests","I need work... shady work."),("end","Get away from me.")]},
    "buy": {"text": "I have legendary items... for a price.","options":[("start","Maybe later.")]},
    "quests": {"text": "Heh. You've got guts. I've got... tasks.","options":[("quest_list","Let's hear them."),("start","Not interested.")]},
    "quest_list": {"text": "Choose your poison:","options":[]},
    "quest_accept": {"text": "Don't disappoint me. Or do. I don't care.","options":[("start","Understood.")]},
    "quest_decline": {"text": "Coward.","options":[("start","...")]},
    "quest_complete": {"text": "You're more useful than I thought. Here's your cut.","options":[("start","Pleasure doing business.")]},
    "end": {"text": "See you in the shadows.","options":[]}
}

NARRATIVE_DATA = {
    "main_menu": {
        "title": "AETHELGARD'S DESCENT",
        "tagline": "The darkness remembers. Do you?",
        "buttons": {
            "new_game": {"label":"Start New Descent","hover_text":"Plunge into the depths."},
            "load_game": {"label":"Resume Journey","hover_text":"Return to the darkness."},
            "codex": {"label":"The Adventurer's Codex","hover_text":"Read chronicles."},
            "ancestral_hall": {"label":"The Ancestral Hall","hover_text":"Spend Shards."},
            "settings": {"label":"Settings","hover_text":"Configure options."},
            "quit": {"label":"Flee to the Surface","hover_text":"Abandon the descent."}
        }
    },
    "introduction": "They called him Aethelgard, the Sorcerer-King...",
    "zone_transitions": {
        1: "The Forgotten Crypts – Where the dead do not sleep.",
        6: "The Molten Forges – Iron breathes fire here.",
        11: "The Alchemical Sewers – A green miasma clings.",
        16: "The Void-Touched Abyss – Reality leaks.",
        20: "Aethelgard's Throne Room – The air is still."
    },
    "lore_fragments": [
        {"title":"Day 3 – The Key that Broke","text":"The rusted lock ate my last key...","hint":"Some barrels contain enemies."},
        {"title":"The Smith's Lament","text":"My sword was sharp as morning...","hint":"Weapons wear out. Keep scrap metal."},
        {"title":"The Grinning Chest","text":"It looked like treasure...","hint":"Ornate chests have a 5% chance to be a Mimic."},
        {"title":"The Floor That Breathed","text":"The stone looked solid...","hint":"Some tiles are illusionary traps."},
        {"title":"The Alchemist's Last Brew","text":"I drank the golden liquid...","hint":"Liquid Gold makes you immobile but nearly invincible."}
    ],
    "boss_encounters": {
        "shopkeeper_greetings": ["Grumble says: 'More flesh for the grinder?'","Grumble says: 'You again. Still breathing.'","Grumble says: 'The darkness down there… it talks to you.'"],
        "grave_warden_taunt": "The Grave-Warden Aegis raises its shield. 'You will be forgotten.'",
        "lich_king_taunt": "The Lich King Aethelgard rises from his throne. 'What is death to a king?'"
    },
    "endings": {"victory":"The crown shatters. Aethelgard's bones turn to dust.","game_over":"Your vision fades to red. The last thing you hear is laughter."},
    "autosave": {"enabled":True,"frequency":"after every boss defeat and every 5 rooms entered","message":"Autosave: Your progress has been sealed in shadow."}
}

# ============================== ENVIRONMENTAL FEATURES ==============================
def feature_spring_trap(hero, game_engine, x, y):
    dmg = 15
    hero.take_damage(dmg)
    story = game_engine.story_gen.get_story("trap", damage=dmg)
    game_engine.ui.display_story(story)
    game_engine.remove_tile_feature(x,y)
def feature_poison_gas(hero, game_engine, x, y):
    hero.take_damage(5)
    hero.apply_status("Soul-Burn",3,2)
    game_engine.ui.log_message("Poison gas vents! You take 5 damage and are poisoned!")
    game_engine.remove_tile_feature(x,y)
def feature_void_pitfall(hero, game_engine, x, y):
    if game_engine.dungeon.current_level < MAX_LEVEL:
        game_engine.dungeon.move_to_level(game_engine.dungeon.current_level+1)
        game_engine.current_x, game_engine.current_y = 0,0
        fall_dmg = int(hero.max_hp * 0.2)
        hero.take_damage(fall_dmg)
        game_engine.ui.log_message(f"A void pitfall swallows you! You fall to level {game_engine.dungeon.current_level} and take {fall_dmg} fall damage!")
        game_engine.ui.update_map()
    else:
        game_engine.ui.log_message("The void pitfall fizzles harmlessly at the final level.")
    game_engine.remove_tile_feature(x,y)
def feature_alarm_rune(hero, game_engine, x, y):
    game_engine.ui.log_message("An alarm rune triggers! All monsters on this floor wake up and gain speed.")
    grid = game_engine.dungeon.levels[game_engine.dungeon.current_level]["grid"]
    for row in grid:
        for room in row:
            if room and room.get("monsters"):
                for m in room["monsters"]: m.ability = "awake"
    game_engine.remove_tile_feature(x,y)
def feature_barrel(hero, game_engine, x, y):
    roll = random.random()
    if roll < 0.7:
        gold = random.randint(5,25)
        hero.gold += gold
        game_engine.ui.log_message(f"You smash the barrel and find {gold} gold!")
        if random.random() < 0.15 and game_engine.dungeon.current_level <= 5:
            truffle = Item("Cave-Truffle","Cave-Truffle","material",50,{},"A rare fungal delicacy.")
            hero.inventory.append(truffle)
            game_engine.quest_manager.update_progress("gather", target="Cave-Truffle")
            game_engine.ui.log_message("You also find a Cave-Truffle!")
    elif roll < 0.9:
        game_engine.ui.log_message("The barrel is empty.")
    else:
        rat = Monster("Plague Rat","normal",game_engine.dungeon.current_level,15,5,2,20,10,"",{},[])
        game_engine.combat_monsters.append(rat)
        game_engine.start_combat([rat])
        game_engine.ui.log_message("A plague rat bursts out of the barrel!")
    game_engine.remove_tile_feature(x,y)
def feature_cracked_wall(hero, game_engine, x, y):
    if game_engine.dynamite_used or (hero.weapon and hero.weapon.mechanic in ["impact","heavy_swing"]):
        game_engine.remove_tile_feature(x,y)
        game_engine.ui.log_message("You blast open the cracked wall! A secret passage appears.")
    else:
        game_engine.ui.log_message("The cracked wall is too sturdy. You need dynamite or a heavy weapon.")
def feature_heavy_iron_door(hero, game_engine, x, y):
    if game_engine.skeleton_key_used:
        game_engine.remove_tile_feature(x,y)
        game_engine.ui.log_message("The skeleton key unlocks the iron door.")
    else:
        game_engine.ui.log_message("A heavy iron door blocks the way. You need a skeleton key.")
def feature_ornate_chest(hero, game_engine, x, y):
    if random.random() < 0.05:
        game_engine.ui.log_message("The chest growls! It's a Mimic!")
        mimic = Monster("Mimic","boss",game_engine.dungeon.current_level,60,15,20,200,150,"",{},[])
        game_engine.start_combat([mimic])
    else:
        gold = random.randint(50,200)
        hero.gold += gold
        game_engine.ui.log_message(f"You open the ornate chest and find {gold} gold!")
        if game_engine.dungeon.current_level >= 11 and game_engine.dungeon.current_level <= 15 and random.random() < 0.3:
            hammer = Item("Rusted Hammer Head","Rusted Hammer Head","quest_item",0,{},"A broken hammer head, still warm.")
            hero.inventory.append(hammer)
            game_engine.quest_manager.update_progress("gather", target="Rusted Hammer Head")
            game_engine.ui.log_message("You also find a Rusted Hammer Head!")
        if random.random() < 0.3:
            acc_name = random.choice(list(ACCESSORIES.keys()))
            acc = ACCESSORIES[acc_name]
            hero.inventory.append(Item(acc.name,acc.name,"accessory",acc.value,acc.stat_bonus,acc.description))
            game_engine.ui.log_message(f"You also found {acc.name}!")
    game_engine.remove_tile_feature(x,y)
def feature_fountain_nymph(hero, game_engine, x, y):
    hero.hp = hero.max_hp
    hero.mp = hero.max_mp
    for s in list(hero.active_statuses.keys()):
        if s in ["Bleed","Soul-Burn","Poison","Rooted","Stunned","Blind","Confuse","Silence"]:
            del hero.active_statuses[s]
    game_engine.ui.log_message("You drink from the Fountain of the Nymph. Fully restored and all ailments cured!")
    game_engine.remove_tile_feature(x,y)
def feature_altar_blood(hero, game_engine, x, y):
    if messagebox.askyesno("Altar of Blood","Sacrifice 15 max HP for a guaranteed unique artifact?"):
        hero.max_hp -= 15
        hero.hp = min(hero.hp, hero.max_hp)
        if random.random() < 0.5:
            weapon_name = random.choice(["Whispering Blade","Aethelgard's Regret","Paradox Scepter"])
            hero.weapons_inventory.append(Weapon(weapon_name,0,[]))
            game_engine.ui.log_message(f"The altar grants you {weapon_name}!")
        else:
            armor_name = random.choice(["Carapace of the Hive Mother","Crown of the Mad King","Boots of the Chronomancer"])
            armor = ARMOR_PIECES[armor_name]
            hero.inventory.append(Item(armor.name,armor.name,"armor",0,{},armor.description))
            game_engine.ui.log_message(f"The altar grants you {armor.name}!")
        game_engine.remove_tile_feature(x,y)
def feature_statue_gambler(hero, game_engine, x, y):
    if hero.gold >= 50:
        hero.gold -= 50
        if random.random() < 0.5:
            game_engine.blessed_buff = True
            game_engine.ui.log_message("The statue smiles. You gain the Blessed buff (+20% to all stats for the floor).")
        else:
            game_engine.cursed_buff = True
            game_engine.ui.log_message("The statue frowns. You are cursed (weapon durability drops twice as fast).")
        game_engine.remove_tile_feature(x,y)
    else:
        game_engine.ui.log_message("You don't have 50 gold to offer.")
def feature_anvil_echoes(hero, game_engine, x, y):
    if hero.weapon:
        hero.weapon.current_durability = hero.weapon.max_durability
        hero.anvil_buff_turns = 10
        hero.anvil_buff_damage = 5
        game_engine.ui.log_message("You strike the anvil. Your weapon is fully repaired and gains +5 fire damage for 10 turns!")
        for _ in range(3):
            monster = game_engine.dungeon._create_random_monster(game_engine.dungeon.current_level)
            game_engine.combat_monsters.append(monster)
        game_engine.start_combat(game_engine.combat_monsters)
        game_engine.remove_tile_feature(x,y)
def feature_cursed_shrine(hero, game_engine, x, y):
    if messagebox.askyesno("Cursed Shrine", "The altar pulses with dark energy. Accept the gift? (+20 Max HP, full heal, but you may drop your weapon on attack)"):
        hero.max_hp += 20
        hero.hp = hero.max_hp
        hero.mp = hero.max_mp
        hero.butterfingers = True
        game_engine.ui.log_message("You feel power surge through you, but your grip feels unsteady.")
        game_engine.remove_tile_feature(x,y)
    else:
        game_engine.ui.log_message("You step away from the shrine, unsettled.")

FEATURES = {
    "^":("Spring-Loaded Spikes",COLORS["health"],feature_spring_trap,"Deals 15 physical damage.",False),
    "P":("Poison Gas Vent",COLORS["green"],feature_poison_gas,"Creates a poison cloud.",False),
    "V":("Void Pitfall",COLORS["purple"],feature_void_pitfall,"Drops you to next level.",False),
    "A":("Alarm Rune",COLORS["gold_rare"],feature_alarm_rune,"Wakes all monsters.",False),
    "B":("Barrel",COLORS["brown"],feature_barrel,"Smash for loot or enemies.",True),
    "W":("Cracked Wall",COLORS["grey"],feature_cracked_wall,"Requires dynamite or heavy weapon.",True),
    "D":("Heavy Iron Door",COLORS["blue"],feature_heavy_iron_door,"Needs skeleton key.",True),
    "C":("Ornate Chest",COLORS["gold_rare"],feature_ornate_chest,"Contains treasure or a mimic.",True),
    "F":("Fountain of the Nymph",COLORS["cyan"],feature_fountain_nymph,"Fully restores HP/MP.",True),
    "X":("Altar of Blood",COLORS["red"],feature_altar_blood,"Sacrifice HP for artifact.",True),
    "G":("Statue of the Gambler",COLORS["gold"],feature_statue_gambler,"Risk gold for buff or curse.",True),
    "E":("Anvil of Echoes",COLORS["orange"],feature_anvil_echoes,"Repairs weapon, summons monsters.",True)
}

# ============================== GAME ENGINE ==============================
class GameEngine:
    def __init__(self, root, meta: MetaProgression, settings: Settings):
        self.root = root
        self.meta = meta
        self.settings = settings
        self.hero = None
        self.dungeon = None
        self.current_x = 0
        self.current_y = 0
        self.ui = None
        self.in_combat = False
        self.combat_monsters = []
        self.combat_index = 0
        self.player_rooted = 0
        self.player_stunned = 0
        self.floor_on_fire = False
        self.boss_flying = False
        self.fire_damage_dealt_this_turn = False
        self.scrambled_movement = 0
        self.mana_regen_penalty = 0
        self.active_rune_absorb = 0
        self.shadow_step_backstab = False
        self.armor_disabled = False
        self.curse_active = False
        self.absorb_shield = 0
        self.double_damage_next = False
        self.double_cast_next = False
        self.time_stop_turns = 0
        self.decoy_active = False
        self.gravity_well_turns = 0
        self.haste_turns = 0
        self.regen_turns = 0
        self.regen_amount = 0
        self.damage_reduction = 0
        self.damage_reduction_turns = 0
        self.reflect_melee = 0
        self.reflect_turns = 0
        self.guardian_angel = False
        self.guardian_turns = 0
        self.doom_tick_target = None
        self.doom_tick_counter = 0
        self.doom_tick_damage = 0
        self.reveal_map = False
        self.chrono_boots_used = False
        self.vision_radius = 0
        self.poisoned = False
        self.skeleton_key_used = False
        self.dynamite_used = False
        self.void_chalk_charges = 0
        self.rune_slab_available = False
        self.blessed_buff = False
        self.cursed_buff = False
        self.feature_map = {}
        self.journal = Journal()
        self.shopkeeper = NPC("Eldrin", SHOPKEEPER_DIALOGUE, [], 0)
        self.blacksmith_npc = NPC("Grimm", BLACKSMITH_DIALOGUE, [], 0)
        self.magic_altar_npc = NPC("Arcanist", MAGIC_ALTAR_DIALOGUE, [], 0)
        self.black_market_npc = NPC("Shadow", BLACK_MARKET_DIALOGUE, [], 0)
        self.story_gen = StoryGenerator(settings)
        self.room_counter = 0
        self.dread = 0
        self.shadow_spawned = False
        self.bestiary = {}
        self.last_killer_name = "unknown"
        self.scavenger = None
        self.quest_manager = QuestManager()
        self.prototype_blade_active = False
        self.cursed_ring_active = False
        self.heavy_package_active = False
        self.soul_gem_active = False
        self.soul_gem_charged = False
        self.spell_only_floor_active = False
        self.goblin_footpad_spawned = False
        self.last_action_was_spell = False
        self.blacksmith_hone_available = False
    def new_game(self, name, hero_type):
        self.hero = Hero(name, hero_type, self.meta)
        self.hero.ui = self.ui
        self.dungeon = Dungeon(game_engine=self)
        self.current_x = 0
        self.current_y = 0
        self.in_combat = False
        self.feature_map.clear()
        self.journal = Journal()
        self.journal.add_entry("The Descent Begins", "You have entered the cursed halls of Aethelgard...", "lore")
        self.room_counter = 0
        self.dread = 0
        self.shadow_spawned = False
        self.bestiary = {}
        self.quest_manager = QuestManager()
        self.prototype_blade_active = False
        self.cursed_ring_active = False
        self.heavy_package_active = False
        self.soul_gem_active = False
        self.spell_only_floor_active = False
        self.ui.build_main_interface()
        self.ui.log_message(f"Welcome, {name} the {hero_type}. Your descent begins...")
        self.ui.display_story(NARRATIVE_DATA["introduction"])
        self.ui.refresh_all()
    def save_game(self):
        if self.hero is None:
            self.ui.log_message("No game to save.")
            return
        grid = self.dungeon.levels[self.dungeon.current_level]["grid"]
        room_states = {}
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                room = grid[y][x]
                if room:
                    state = {"visited": room.get("visited",False), "cleared": room.get("cleared",False)}
                    if room["type"] == "treasure":
                        state["looted"] = room.get("looted",False)
                    room_states[f"{x},{y}"] = state
        data = {
            "hero": self.hero.to_dict(),
            "dungeon_seed": self.dungeon.seed,
            "current_level": self.dungeon.current_level,
            "player_x": self.current_x,
            "player_y": self.current_y,
            "journal": self.journal.to_dict(),
            "room_states": room_states,
            "bestiary": self.bestiary,
            "quest_manager": self.quest_manager.to_dict()
        }
        try:
            with open("savegame.json", "w") as f:
                json.dump(data, f, indent=2)
            self.ui.log_message("Game saved successfully.")
        except Exception as e:
            self.ui.log_message(f"Save failed: {e}")
    def auto_save(self, reason="progress"):
        self.save_game()
        self.ui.log_message(NARRATIVE_DATA["autosave"]["message"])
    def load_game(self):
        if not os.path.exists("savegame.json"):
            self.ui.log_message("No save file found.")
            return
        try:
            with open("savegame.json", "r") as f:
                data = json.load(f)
            self.hero = Hero.from_dict(data["hero"], self.meta)
            self.hero.ui = self.ui
            self.dungeon = Dungeon(seed=data["dungeon_seed"], game_engine=self)
            self.dungeon.current_level = data["current_level"]
            if self.dungeon.current_level not in self.dungeon.levels:
                self.dungeon.generate_level(self.dungeon.current_level)
            self.current_x = data["player_x"]
            self.current_y = data["player_y"]
            self.in_combat = False
            self.feature_map.clear()
            self.journal = Journal.from_dict(data.get("journal",{}))
            self.bestiary = data.get("bestiary", {})
            self.quest_manager.from_dict(data.get("quest_manager", {}))
            room_states = data.get("room_states",{})
            grid = self.dungeon.levels[self.dungeon.current_level]["grid"]
            for coord, state in room_states.items():
                try:
                    x,y = map(int, coord.split(','))
                    if 0<=x<MAP_WIDTH and 0<=y<MAP_HEIGHT and grid[y][x]:
                        grid[y][x]["visited"] = state.get("visited",False)
                        grid[y][x]["cleared"] = state.get("cleared",False)
                        if grid[y][x]["type"] == "treasure":
                            grid[y][x]["looted"] = state.get("looted",False)
                except: pass
            self.shopkeeper.reset_dialogue()
            self.blacksmith_npc.reset_dialogue()
            self.magic_altar_npc.reset_dialogue()
            self.black_market_npc.reset_dialogue()
            self.ui.build_main_interface()
            self.ui.update_map()
            self.ui.log_message("Game loaded successfully.")
            self.ui.refresh_all()
        except Exception as e:
            self.ui.log_message(f"Load failed: {e}\n{traceback.format_exc()}")
    def teleport_to_safe_zone(self):
        grid = self.dungeon.levels[self.dungeon.current_level]["grid"]
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if grid[y][x] and grid[y][x]["type"] == "shop":
                    self.current_x, self.current_y = x, y
                    self.ui.update_map()
                    self.ui.log_message("You teleport to the Safe Zone.")
                    return
        self.current_x, self.current_y = 0,0
        self.ui.update_map()
        self.ui.log_message("No Safe Zone found. You teleport to the entrance.")
    def remove_tile_feature(self, x, y):
        key = (x,y)
        if key in self.feature_map: del self.feature_map[key]
        room = self.dungeon.get_current_room(x,y)
        if room and "features" in room:
            for i,f in enumerate(room["features"]):
                if f.get("pos") == (x,y):
                    room["features"].pop(i)
                    break
        self.ui.update_map()
    def add_tile_feature(self, x, y, feature):
        key = (x,y)
        self.feature_map[key] = feature
        room = self.dungeon.get_current_room(x,y)
        if room:
            if "features" not in room: room["features"] = []
            room["features"].append({"symbol":feature.symbol,"name":feature.name,"color":feature.color,"func":feature.interaction_func,"desc":feature.description,"visible":feature.visible,"pos":(x,y)})
        self.ui.update_map()
    def move(self, dx, dy):
        if self.in_combat:
            self.ui.log_message("In combat! Cannot move.")
            return
        if self.player_rooted > 0 or self.hero.has_status("Rooted"):
            self.ui.log_message("Rooted! Cannot move.")
            return
        if self.hero.gold_skin_turns > 0:
            self.ui.log_message("You are immobilized by Liquid Gold!")
            return
        if self.scrambled_movement > 0:
            mapping = [(0,-1),(0,1),(-1,0),(1,0)]
            random.shuffle(mapping)
            if (dx,dy)==(0,-1): dx,dy = mapping[0]
            elif (dx,dy)==(0,1): dx,dy = mapping[1]
            elif (dx,dy)==(-1,0): dx,dy = mapping[2]
            elif (dx,dy)==(1,0): dx,dy = mapping[3]
            self.scrambled_movement -= 1
        if self.haste_turns > 0: self.haste_turns -= 1
        if self.hero.void_teleport:
            nx, ny = self.current_x + dx*3, self.current_y + dy*3
            nx = max(0, min(MAP_WIDTH-1, nx))
            ny = max(0, min(MAP_HEIGHT-1, ny))
            room = self.dungeon.get_current_room(nx,ny)
            if room is None:
                self.ui.log_message("Cannot teleport out of bounds.")
                return
            self.current_x, self.current_y = nx, ny
            self._enter_room(room)
            return
        nx, ny = self.current_x + dx, self.current_y + dy
        room = self.dungeon.get_current_room(nx,ny)
        if room is None:
            self.ui.log_message("Cannot go that way.")
            return
        self.current_x, self.current_y = nx, ny
        self._enter_room(room)
    def _enter_room(self, room):
        room["visited"] = True
        self.ui.update_map()
        self.room_counter += 1
        if self.room_counter % 5 == 0 and not self.in_combat:
            self.auto_save("room exploration")
        features = []
        if "features" in room:
            for f in room["features"]:
                if f.get("pos") == (self.current_x, self.current_y):
                    features.append(f)
        if features:
            for feat in features:
                if not feat["visible"]:
                    perception = 0.1 + (0.05 if self.hero.head_armor and self.hero.head_armor.name == "Miner's Hardhat" else 0)
                    if random.random() < perception:
                        feat["visible"] = True
                        self.ui.log_message(f"You sense a {feat['name']} nearby!")
                        self.ui.update_map()
                        continue
                    else:
                        self.ui.log_message(f"You step on a hidden {feat['name']}!")
                        feat["func"](self.hero, self, self.current_x, self.current_y)
                        return
                else:
                    answer = messagebox.askyesno(f"{feat['name']}", f"You see {feat['desc']}. Do you want to interact?")
                    if answer:
                        feat["func"](self.hero, self, self.current_x, self.current_y)
                        return
        story = self.story_gen.get_story("enter_room")
        self.ui.display_story(story)
        if self.dungeon.current_level in NARRATIVE_DATA["zone_transitions"] and self.current_x==0 and self.current_y==0:
            self.ui.display_story(NARRATIVE_DATA["zone_transitions"][self.dungeon.current_level])
        stain = self.meta.get_bloodstain_at(self.dungeon.current_level, self.current_x, self.current_y)
        if stain:
            self.ui.display_story(f"You find a bloodstained marker. Here lies {stain['hero_name']} the {stain['hero_class']}, slain by {stain['killed_by']}. You recover {stain['gold']} gold from their remains.")
            self.hero.gold += stain["gold"]
            self.meta.remove_bloodstain(stain)
        if room["type"] == "boss" and not room.get("cleared",False):
            if self.dungeon.current_level == 1:
                self.ui.display_story(NARRATIVE_DATA["boss_encounters"]["grave_warden_taunt"])
            elif self.dungeon.current_level == MAX_LEVEL:
                self.ui.display_story(NARRATIVE_DATA["boss_encounters"]["lich_king_taunt"])
            else:
                story = self.story_gen.get_story("combat_start", monster=room["monsters"][0].name)
                self.ui.display_story(story)
            self.start_combat(room["monsters"])
        elif room["type"] == "normal" and not room.get("cleared",False) and room["monsters"]:
            story = self.story_gen.get_story("combat_start", monster=room["monsters"][0].name)
            self.ui.display_story(story)
            self.start_combat(room["monsters"])
        elif room["type"] == "treasure" and not room.get("looted",False):
            self.loot_treasure()
        elif room["type"] == "shop":
            greeting = random.choice(NARRATIVE_DATA["boss_encounters"]["shopkeeper_greetings"])
            self.ui.display_story(greeting)
            self.ui.open_safe_zone()
        else:
            self.ui.log_message(f"You enter a {room['type']} room.")
        self.ui.refresh_stats()
        if self.player_rooted > 0: self.player_rooted -= 1
        if self.floor_on_fire:
            if not (self.hero.active_passive == "Firewalker"):
                self.hero.take_damage(3)
                self.ui.log_message("Floor on fire! 3 damage.")
            self.floor_on_fire = False
        if self.regen_turns > 0:
            self.hero.heal(self.regen_amount)
            self.regen_turns -= 1
            self.ui.log_message(f"Regeneration heals {self.regen_amount} HP.")
    def loot_treasure(self):
        room = self.dungeon.get_current_room(self.current_x, self.current_y)
        gold = random.randint(40,150) + self.dungeon.current_level*15
        material = random.choice(["iron_tip","spectral_essence","charged_core","silk_thread","dragon_scale","void_shard"])
        item = Item(material, material.capitalize().replace("_"," "), "material", 25, {}, f"A valuable crafting material used in upgrades and repairs.")
        self.hero.gold += gold
        self.hero.inventory.append(item)
        story = self.story_gen.get_story("treasure", gold=gold, item=item.name)
        self.ui.display_story(story)
        if random.random() < 0.25:
            lore = random.choice(NARRATIVE_DATA["lore_fragments"])
            self.ui.display_story(f"Found a journal: {lore['title']}\n{lore['text']}\n\nHint: {lore['hint']}")
            self.journal.add_entry(lore["title"], lore["text"]+"\n\n"+lore["hint"], "lore")
        if random.random() < 0.35:
            potion_name = random.choice(list(CONSUMABLES.keys()))
            potion = CONSUMABLES[potion_name]
            self.hero.inventory.append(Item(potion.name, potion.name, "consumable", potion.value, potion.stat_bonus, potion.description))
            self.ui.log_message(self.story_gen.get_loot_story(potion.name))
        elif random.random() < 0.25:
            armor_name = random.choice(list(ARMOR_PIECES.keys()))
            armor = ARMOR_PIECES[armor_name]
            self.hero.inventory.append(Item(armor.name, armor.name, "armor", armor.phys_def + armor.mag_res*2, {}, armor.description))
            self.ui.log_message(self.story_gen.get_loot_story(armor.name))
        elif random.random() < 0.15:
            acc_name = random.choice(list(ACCESSORIES.keys()))
            acc = ACCESSORIES[acc_name]
            self.hero.inventory.append(Item(acc.name, acc.name, "accessory", acc.value, acc.stat_bonus, acc.description))
            self.ui.log_message(self.story_gen.get_loot_story(acc.name))
        elif random.random() < 0.15:
            weapon_name = random.choice(list(WEAPON_TYPES.keys()))
            self.hero.weapons_inventory.append(Weapon(weapon_name,0,[]))
            self.ui.log_message(self.story_gen.get_loot_story(weapon_name))
        room["looted"] = True
        room["cleared"] = True
        self.ui.refresh_inventory()
        self.ui.refresh_stats()
    def start_combat(self, monsters):
        self.in_combat = True
        self.combat_monsters = monsters.copy()
        self.combat_index = 0
        self.boss_flying = False
        self.fire_damage_dealt_this_turn = False
        self.ui.open_combat_window(self.combat_monsters)
    def apply_doom_tick(self):
        if self.doom_tick_target and self.doom_tick_counter > 0:
            self.doom_tick_counter -= 1
            if self.doom_tick_counter == 0 and self.doom_tick_target in self.combat_monsters:
                self.doom_tick_target.take_damage(self.doom_tick_damage)
                self.ui.log_message(f"Doom Tick deals {self.doom_tick_damage} damage!")
                self.doom_tick_target = None
    def combat_action(self, action, spell_name=None):
        if not self.in_combat: return
        if self.player_stunned > 0 or self.hero.has_status("Stunned"):
            self.player_stunned = max(self.player_stunned,1)
            self.player_stunned -= 1
            self.ui.combat_text.insert(tk.END, "Stunned!\n")
            self.monster_turn()
            return
        if self.time_stop_turns > 0:
            self.time_stop_turns -= 1
            self.ui.combat_text.insert(tk.END, "Time frozen! Extra turn.\n")
        current = self.combat_monsters[self.combat_index]
        msg = ""
        self.fire_damage_dealt_this_turn = False
        self.last_action_was_spell = False
        if hasattr(self.hero, 'butterfingers') and self.hero.butterfingers and random.random() < 0.05 and self.hero.weapon:
            dropped = self.hero.weapon
            self.hero.unequip_weapon()
            self.ui.combat_text.insert(tk.END, f"Your butterfingers curse causes you to drop your weapon! It falls to the ground.\n")
        if action == "attack":
            from_side = random.random() < 0.5 if (isinstance(current,Boss) and current.property=="invulnerable_front") else True
            msg, _ = CombatEngine.player_attack(self.hero, current, self.shadow_step_backstab, from_side)
            self.shadow_step_backstab = False
        elif action == "magic":
            spell = next((s for s in self.hero.active_spells if s.name==spell_name), None)
            if spell:
                msg, _ = CombatEngine.player_cast_spell(self.hero, spell, current, self)
                self.fire_damage_dealt_this_turn = True
                self.last_action_was_spell = True
                if self.double_cast_next:
                    self.double_cast_next = False
                    msg2, _ = CombatEngine.player_cast_spell(self.hero, spell, current, self)
                    msg += "\n" + msg2
            else: msg = "Spell not found!"
        elif action == "special":
            msg, success = self.hero.special_ability(self)
            if not success:
                self.ui.combat_text.insert(tk.END, msg + "\n")
                return
        elif action == "flee":
            if random.random() < 0.4:
                self.in_combat = False
                self.ui.close_combat_window()
                self.ui.log_message(self.story_gen.get_flee_result(True))
                return
            else:
                msg = self.story_gen.get_flee_result(False)
        elif action == "use_item":
            self.ui.open_combat_item_menu()
            return
        self.ui.update_combat_display(self.combat_monsters)
        self.ui.combat_text.insert(tk.END, msg + "\n")
        if not current.is_alive():
            self.defeat_monster(current)
            return
        self.apply_doom_tick()
        self.monster_turn()
        if self.hero.movement_penalty <= -2:
            if random.random() < 0.2 * (-self.hero.movement_penalty/2):
                self.ui.combat_text.insert(tk.END, "Your heavy armor slows you! Monster takes another turn.\n")
                self.monster_turn()
        for m in self.combat_monsters:
            for mmsg in m.process_statuses(self):
                self.ui.combat_text.insert(tk.END, mmsg + "\n")
        for hmsg in self.hero.process_statuses(self):
            self.ui.combat_text.insert(tk.END, hmsg + "\n")
        self.ui.refresh_stats()
        if self.hero.hp <= 0:
            if self.guardian_angel and self.guardian_turns > 0:
                self.hero.hp = 10
                self.guardian_angel = False
                self.ui.log_message("Guardian Angel revives you with 10 HP!")
            elif self.hero.phoenix_blessing_turns > 0:
                self.hero.hp = int(self.hero.max_hp * 0.5)
                for m in self.combat_monsters: m.take_damage(20)
                self.ui.log_message("Phoenix Blessing triggers! You erupt in flames, damaging all enemies, and revive with 50% HP!")
                self.hero.phoenix_blessing_turns = 0
            else: self.game_over()
    def monster_turn(self):
        if self.time_stop_turns > 0: return
        current = self.combat_monsters[self.combat_index]
        if isinstance(current,Boss):
            boss_msg = current.use_boss_ability(self.hero, self)
            if boss_msg: self.ui.combat_text.insert(tk.END, boss_msg + "\n")
        if hasattr(current, 'use_boss_ability') and not isinstance(current,Boss) and current.ability == "zombie_rage":
            current.use_boss_ability(self.hero, self)
        if self.decoy_active and random.random() < 0.5:
            self.ui.combat_text.insert(tk.END, "Decoy attracts the attack!\n")
            return
        thorns_dmg = 0
        if hasattr(self.hero,'thorn_percent') and self.hero.thorn_percent > 0:
            thorns_dmg = int(current.attack * self.hero.thorn_percent)
        if self.hero.active_passive == "Thorns": thorns_dmg += 5
        if thorns_dmg > 0:
            current.take_damage(thorns_dmg)
            self.ui.combat_text.insert(tk.END, f"Thorns deal {thorns_dmg} damage to {current.name}.\n")
        if self.hero.chill_on_hit:
            current.apply_status("Rooted",2)
            self.ui.combat_text.insert(tk.END, f"{current.name} is chilled.\n")
        damage_taken = 0
        damage = current.attack + random.randint(-3,3)
        damage = max(1, damage)
        if self.boss_flying and not self.hero.hero_type == "Elf Aether-Mage":
            msg = f"{current.name} is flying and misses!"
        elif self.armor_disabled:
            original_def = self.hero.defense
            self.hero.defense = 0
            dealt = self.hero.take_damage(damage)
            self.hero.defense = original_def
            self.armor_disabled = False
            msg = f"{current.name} corrodes armor! {dealt} damage."
            damage_taken = dealt
        elif isinstance(current,Boss) and current.property == "sanguine_link":
            dealt = self.hero.take_damage(damage)
            current.hp = min(current.max_hp, current.hp + dealt)
            msg = f"{current.name} attacks for {dealt} and heals {dealt}!"
            damage_taken = dealt
        else:
            if self.damage_reduction_turns > 0:
                damage = int(damage * (1 - self.damage_reduction))
                self.damage_reduction_turns -= 1
            if self.absorb_shield > 0:
                self.absorb_shield -= 1
                msg = f"{current.name} hits your shield and is absorbed!"
            else:
                if self.reflect_turns > 0 and not isinstance(current,Boss):
                    reflect_dmg = int(damage * self.reflect_melee)
                    current.take_damage(reflect_dmg)
                    self.reflect_turns -= 1
                    dealt = self.hero.take_damage(damage)
                    msg = f"{current.name} attacks for {dealt} and takes {reflect_dmg} reflect damage!"
                    damage_taken = dealt
                else:
                    dealt = self.hero.take_damage(damage)
                    msg = f"{current.name} attacks for {dealt} damage!"
                    damage_taken = dealt
        self.ui.refresh_stats()
        self.ui.combat_text.insert(tk.END, msg + "\n")
        if damage_taken > 10 and hasattr(self.hero,'spawn_grub') and self.hero.spawn_grub:
            grub = Monster("Venomous Grub","normal",self.dungeon.current_level,20,5,2,0,0,"",{},[])
            self.combat_monsters.append(grub)
            self.ui.combat_text.insert(tk.END, "Carapace spawns a Venomous Grub ally!\n")
        if self.hero.hp <= 0 and self.guardian_angel and self.guardian_turns > 0:
            self.hero.hp = 10
            self.guardian_angel = False
            self.ui.log_message("Guardian Angel revives you!")
    def defeat_monster(self, monster):
        msg = ""
        scrap = 0
        scrap_bonus = 1 + (self.hero.scavenger_bonus if hasattr(self.hero,'scavenger_bonus') else 0)
        if isinstance(monster,Boss):
            if random.random() < 0.5: scrap = random.randint(2,4) * scrap_bonus
            shard_reward = monster.shard_reward
            if shard_reward > 0:
                self.meta.add_shards(shard_reward)
                msg += f"Aethelgard's Shards: +{shard_reward}!\n"
        else:
            if random.random() < 0.25: scrap = 1 * scrap_bonus
            if monster.name == "Putrid Shambler" and random.random() < 0.4:
                gland = Item("Poison Gland","Poison Gland","material",20,{},"A venomous gland.")
                self.hero.inventory.append(gland)
                self.quest_manager.update_progress("gather", target="Poison Gland")
                msg += "Poison Gland dropped!\n"
            if monster.name == "Cinder Sprite" and random.random() < 0.3:
                coal = Item("Living Coal","Living Coal","material",50,{},"A piece of living coal that still burns.")
                self.hero.inventory.append(coal)
                self.quest_manager.update_progress("gather", target="Living Coal")
                msg += "Living Coal dropped!\n"
            if monster.name == "Goblin Footpad" and not self.goblin_footpad_spawned:
                self.quest_manager.update_progress("kill", target="Goblin Footpad")
                msg += "You have slain the Goblin Footpad! Quest progress updated.\n"
        if scrap > 0:
            self.hero.scrap_metal += scrap
            msg += f"{monster.name} dropped {scrap} Scrap Metal!\n"
            self.quest_manager.update_progress("gather", target="Scrap Metal", amount=scrap)
        gold_mult = self.hero.gold_mult if hasattr(self.hero,'gold_mult') else 1.0
        if isinstance(monster,Boss):
            core = Item(monster.core_drop, monster.core_drop, "boss_core", 500, {}, f"Core of {monster.name} - A powerful artifact dropped by a boss.")
            self.hero.inventory.append(core)
            self.hero.boss_cores.append(monster.core_drop)
            msg += f"Defeated {monster.name}! Received {core.name}.\n"
            story = self.story_gen.get_story("boss_defeated", boss=monster.name)
            self.ui.display_story(story)
            self.journal.add_entry(f"Defeated {monster.name}", f"You have slain the {monster.name}, a formidable foe. The dungeon trembles.", "boss")
            if self.hero.active_passive == "Second Wind": self.hero.restore_mp(int(self.hero.max_mp * 0.2))
            self.auto_save("boss defeated")
        else:
            story = self.story_gen.get_story("defeat_monster", monster=monster.name)
            self.ui.display_story(story)
        xp = monster.xp_reward
        gold = int(monster.gold_reward * gold_mult)
        if self.hero.active_passive == "Scavenger": gold = int(gold * 1.2)
        self.hero.add_xp(xp)
        self.hero.gold += gold
        msg += f"+{xp} XP, +{gold} gold.\n"
        if self.hero.weapon and self.hero.weapon.weapon_type == "Whispering Blade":
            if not hasattr(self.hero,'whisper_kills'): self.hero.whisper_kills = 0
            self.hero.whisper_kills += 1
            msg += f"Whispering Blade grows stronger (+1 damage).\n"
        if self.hero.active_passive == "Soul Siphon":
            self.hero.heal(2)
            msg += "Soul Siphon restores 2 HP.\n"
        if random.random() < 0.2:
            potion_name = random.choice(list(CONSUMABLES.keys()))
            potion = CONSUMABLES[potion_name]
            self.hero.inventory.append(Item(potion.name, potion.name, "consumable", potion.value, potion.stat_bonus, potion.description))
            msg += self.story_gen.get_loot_story(potion.name) + "\n"
        name = monster.name
        if name not in self.bestiary:
            self.bestiary[name] = {"kills": 0, "lore_unlocked": False, "ability_unlocked": False}
        self.bestiary[name]["kills"] += 1
        kills = self.bestiary[name]["kills"]
        if kills == 1 and not self.bestiary[name]["lore_unlocked"]:
            self.bestiary[name]["lore_unlocked"] = True
            self.journal.add_entry(f"Bestiary: {name}", f"You have slain a {name}. Its HP is {monster.max_hp}.")
            self.ui.log_message(f"Bestiary entry unlocked for {name}!")
        elif kills == 10 and not self.bestiary[name]["ability_unlocked"]:
            self.bestiary[name]["ability_unlocked"] = True
            self.journal.add_entry(f"Bestiary: {name} (Mastery)", f"You now understand {name}'s abilities. +1 damage against this type.")
            if not hasattr(self.hero, 'monster_bonus_damage'):
                self.hero.monster_bonus_damage = {}
            self.hero.monster_bonus_damage[name] = self.hero.monster_bonus_damage.get(name, 0) + 1
            self.ui.log_message(f"Mastery gained: +1 damage vs {name}!")
        if hasattr(self.hero, 'monster_bonus_damage') and name in self.hero.monster_bonus_damage:
            bonus = self.hero.monster_bonus_damage[name]
            msg += f"Bestiary mastery grants +{bonus} damage vs {name} (next time).\n"
        self.quest_manager.update_progress("kill", target=name)
        if self.prototype_blade_active:
            self.hero.prototype_blade_kills += 1
            self.quest_manager.update_progress("special", target="prototype_kills")
        if self.spell_only_floor_active and self.last_action_was_spell:
            self.hero.spell_only_kills_this_floor += 1
            self.quest_manager.update_progress("special", target="spell_only_kills")
        self.combat_monsters.pop(self.combat_index)
        if not self.combat_monsters:
            room = self.dungeon.get_current_room(self.current_x, self.current_y)
            room["cleared"] = True
            self.in_combat = False
            self.ui.close_combat_window()
            self.ui.log_message(msg)
            self.ui.log_message("All enemies defeated!")
            self.ui.refresh_inventory()
            if self.cursed_ring_active:
                self.quest_manager.update_progress("special", target="clear_floor_with_ring")
            if isinstance(monster,Boss) and self.dungeon.current_level < MAX_LEVEL:
                self.dungeon.move_to_level(self.dungeon.current_level + 1)
                self.current_x, self.current_y = 0,0
                self.ui.log_message(f"Descended to level {self.dungeon.current_level}.")
                self.ui.update_map()
                if self.dungeon.current_level in NARRATIVE_DATA["zone_transitions"]:
                    self.ui.display_story(NARRATIVE_DATA["zone_transitions"][self.dungeon.current_level])
            return
        self.combat_index = min(self.combat_index, len(self.combat_monsters)-1)
        self.ui.combat_text.insert(tk.END, msg)
    def game_over(self):
        if self.hero:
            death_data = {
                "floor": self.dungeon.current_level,
                "x": self.current_x,
                "y": self.current_y,
                "gold": int(self.hero.gold * 0.1),
                "hero_name": self.hero.name,
                "hero_class": self.hero.hero_type,
                "killed_by": self.last_killer_name
            }
            self.meta.record_bloodstain(death_data)
            self.meta.set_last_death(self.hero.to_dict())
        self.in_combat = False
        self.ui.close_combat_window()
        self.ui.display_story(NARRATIVE_DATA["endings"]["game_over"])
        if messagebox.askyesno("Defeat", "You have fallen. Start a new game?"):
            self.ui.show_start_screen()
        else:
            self.root.quit()
    def rest(self):
        if self.in_combat:
            self.ui.log_message("Cannot rest in combat!")
            return
        self.hero.heal(1)
        if self.hero.max_mp > 0:
            self.hero.restore_mp(1)
        self.dread += 1
        self.ui.log_message("You rest for a moment. (+1 HP/MP). Dread increases.")
        self.ui.refresh_stats()
        if self.dread >= 10 and not self.shadow_spawned:
            self.spawn_shadow()
    def spawn_shadow(self):
        shadow = Monster("Shadow of the Lich", "boss", self.dungeon.current_level, 999, 30, 25, 0, 0, "inevitable", {}, [])
        shadow.immune_to_all = True
        self.combat_monsters = [shadow]
        self.start_combat([shadow])
        self.shadow_spawned = True
        self.ui.log_message("The Dread Meter fills! The Shadow of the Lich appears, unkillable. Run to the stairs!")
    def rewind(self):
        if not self.chrono_boots_used and self.hero.legs_armor and self.hero.legs_armor.name == "Boots of the Chronomancer":
            if os.path.exists("savegame.json"):
                self.load_game()
                self.chrono_boots_used = True
                self.ui.log_message("Chronomancer boots rewind time! Last 3 turns undone.")
            else: self.ui.log_message("No save to rewind to.")
    def draw_glyph(self):
        if self.void_chalk_charges <= 0:
            self.ui.log_message("No Void Chalk charges left.")
            return
        if self.in_combat:
            self.ui.log_message("Cannot draw glyphs in combat.")
            return
        glyph_type = simpledialog.askstring("Glyph Type", "Draw which glyph? (red for fire trap, blue for mana regen)")
        if glyph_type and glyph_type.lower() in ["red","blue"]:
            self.void_chalk_charges -= 1
            if not hasattr(self,'glyphs'): self.glyphs = {}
            self.glyphs[(self.current_x,self.current_y)] = glyph_type.lower()
            self.ui.log_message(f"{glyph_type.capitalize()} glyph placed. {self.void_chalk_charges} charges remaining.")
        else:
            self.ui.log_message("Invalid glyph type.")
    def inspect_tile(self, x, y):
        room = self.dungeon.get_current_room(x, y)
        if not room:
            return
        if room.get("monsters") and not room.get("cleared", False):
            m = room["monsters"][0]
            lore = self.story_gen.get_lore(m.name)
            self.ui.display_story(f"Inspecting {m.name}: {lore}")
        elif room.get("features"):
            for f in room["features"]:
                if f.get("pos") == (x, y):
                    lore = self.story_gen.get_lore(f["name"])
                    self.ui.display_story(f"Inspecting {f['name']}: {lore}")
                    return
        else:
            self.ui.display_story("Nothing of note here.")
    def get_available_quests_for_npc(self, npc_id):
        completed = self.quest_manager.completed_quests
        return self.quest_manager.get_available_quests(npc_id, completed)
    def accept_quest(self, quest_id):
        quest = self.quest_manager.accept_quest(quest_id)
        self.journal.add_entry(f"Quest Accepted: {quest.name}", quest.description, "quest")
        self.ui.log_message(f"Accepted quest: {quest.name}")
        if quest_id == "field_testing":
            prototype = Weapon("Prototype Blade", 0, ["Fragile"])
            prototype.damage = 20
            prototype.max_durability = 30
            prototype.current_durability = 30
            self.hero.weapons_inventory.append(prototype)
            self.prototype_blade_active = True
            self.ui.log_message("You receive the Prototype Blade. It's powerful but fragile!")
        elif quest_id == "cursed_wager":
            self.cursed_ring_active = True
            self.hero.max_hp = 10
            self.hero.hp = 10
            self.ui.log_message("You are forced to wear the Cursed Ring of Fragility! Your max HP is now 10.")
        elif quest_id == "smuggler_run":
            self.heavy_package_active = True
            self.ui.log_message("You are now carrying the Heavy Illicit Package. It slows you down.")
        elif quest_id == "soul_capture":
            gem = Item("Empty Soul Gem","Empty Soul Gem","quest_item",0,{},"An empty gem that can capture a boss's soul.")
            self.hero.inventory.append(gem)
            self.soul_gem_active = True
            self.ui.log_message("You receive an Empty Soul Gem. Defeat a boss while it's stunned or frozen to capture its soul.")
        elif quest_id == "echoes_void":
            self.spell_only_floor_active = True
            self.ui.log_message("The Arcanist binds you: you must defeat 3 enemies on this floor using only spells!")
    def complete_quest(self, quest_id):
        quest = self.quest_manager.quests_db[quest_id]
        rewards = self.quest_manager.complete_quest(quest)
        for reward in rewards:
            if reward["type"] == "gold":
                self.hero.gold += reward["value"]
                self.ui.log_message(f"Received {reward['value']} gold.")
            elif reward["type"] == "item":
                if reward["item"] == "Truffle Brew":
                    item = Item("Truffle Brew","Truffle Brew","consumable",100,{},"Heals 50 HP and cures all status effects.")
                    self.hero.inventory.append(item)
                elif reward["item"] == "Skeleton Key":
                    item = Item("Skeleton Key","Skeleton Key","consumable",100,{},"Opens any lock.")
                    self.hero.inventory.append(item)
                elif reward["item"] == "Antidote Pouch":
                    self.hero.poison_immunity = True
                    self.ui.log_message("You are now immune to poison!")
                elif reward["item"] == "Masterwork Whetstone":
                    item = Item("Masterwork Whetstone","Masterwork Whetstone","tool",0,{},"Repairs 10 durability once per floor.")
                    self.hero.inventory.append(item)
                elif reward["item"] == "Rune of Thrift":
                    rune = Rune("Rune of Thrift")
                    self.hero.runes.append(rune)
                elif reward["item"] == "Soul Gem Amulet":
                    acc = ACCESSORIES["Soul Gem Amulet"] = Accessory("Soul Gem Amulet","Artifact",lambda h,g: setattr(h,"soul_gem_amulet",True),"Regenerates 2 MP per turn.",800,{"mp_regen":2})
                    self.hero.equip_accessory(acc, self)
                elif reward["item"] == "Random Epic Weapon":
                    wtype = random.choice(list(WEAPON_TYPES.keys()))
                    epic = Weapon(wtype, 7, WEAPON_TYPES[wtype]["magic_pool"][:1])
                    self.hero.weapons_inventory.append(epic)
                    self.ui.log_message(f"Received {epic.weapon_type} +7!")
                elif reward["item"] == "Ring of the Survivor":
                    acc = ACCESSORIES["Ring of the Survivor"] = Accessory("Ring of the Survivor","Artifact",lambda h,g: (setattr(h,"bonus_hp",50), setattr(h,"dodge_chance",0.15)),"+50 Max HP, +15% Dodge.",1000,{"hp":50})
                    self.hero.equip_accessory(acc, self)
            elif reward["type"] == "weapon_upgrade":
                if self.hero.weapon:
                    self.hero.weapon.upgrade_level += reward["value"]
                    self.hero.weapon.damage += 2 * reward["value"]
                    self.hero.weapon.max_durability += 5 * reward["value"]
                    self.hero.weapon.current_durability += 5 * reward["value"]
                    self.ui.log_message(f"Your weapon upgraded by +{reward['value']} levels!")
            elif reward["type"] == "service":
                if reward["service"] == "hone":
                    self.blacksmith_hone_available = True
                    self.ui.log_message("Blacksmith now offers 'Hone' service: temporary unbreakable weapon.")
            elif reward["type"] == "unlock_spell":
                if reward["spell"] == "Time Stop" and reward["spell"] not in [s.name for s in self.hero.spellbook]:
                    self.hero.spellbook.append(Spell("Time Stop"))
                    self.ui.log_message("You learned Time Stop!")
            elif reward["type"] == "passive":
                if reward["passive"] == "Archmage's Flow":
                    self.hero.archmage_flow = True
                    self.ui.log_message("Passive gained: Archmage's Flow (25% chance spells cost 0 and cast twice).")
            elif reward["type"] == "shards":
                self.meta.add_shards(reward["value"])
                self.ui.log_message(f"Received {reward['value']} Aethelgard's Shards!")
            elif reward["type"] == "discount":
                self.hero.shop_discount = reward["value"] / 100.0
                self.ui.log_message(f"Storekeeper gives you a permanent {reward['value']}% discount!")
        self.journal.add_entry(f"Quest Complete: {quest.name}", f"You completed {quest.name} and received your reward.", "quest")
        self.ui.log_message(f"Quest completed: {quest.name}!")

# ============================== SETTINGS UI ==============================
class SettingsUI:
    def __init__(self, parent, settings: Settings, on_close_callback=None):
        self.parent = parent
        self.settings = settings
        self.on_close_callback = on_close_callback
        self.create_window()
    def create_window(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("Settings")
        self.window.geometry("400x300")
        self.window.configure(bg=COLORS["bg_dark"])
        self.window.transient(self.parent)
        self.window.grab_set()
        tk.Label(self.window, text="GAME SETTINGS", font=("Georgia",16,"bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack(pady=15)
        frame = tk.Frame(self.window, bg=COLORS["bg_dark"])
        frame.pack(pady=15, padx=20, fill=tk.X)
        tk.Label(frame, text="AI Story Generation (Ollama):", fg=COLORS["text"], bg=COLORS["bg_dark"], font=("Arial",12)).pack(side=tk.LEFT)
        self.ollama_var = tk.BooleanVar(value=self.settings.use_ollama)
        tk.Checkbutton(frame, variable=self.ollama_var, command=self.toggle_ollama, bg=COLORS["bg_dark"], fg=COLORS["text"], selectcolor=COLORS["bg_dark"]).pack(side=tk.RIGHT)
        self.warning = tk.Label(self.window, text="Warning: Ollama may cause lag on CPU. Disable for best performance.", fg=COLORS["gold_rare"], bg=COLORS["bg_dark"], font=("Arial",9), wraplength=350)
        if self.settings.use_ollama: self.warning.pack(pady=5)
        tk.Label(self.window, text="When AI is disabled, the game uses a library of\n100+ preset messages for variety without lag.\n\nChanges take effect immediately.", fg=COLORS["text"], bg=COLORS["bg_dark"], font=("Arial",10), justify=tk.CENTER).pack(pady=15)
        tk.Button(self.window, text="Close", command=self.close, bg=COLORS["bg_light"], fg=COLORS["text"], font=("Arial",12)).pack(pady=20)
    def toggle_ollama(self):
        self.settings.use_ollama = self.ollama_var.get()
        self.settings.save()
        if self.settings.use_ollama:
            self.warning.pack(pady=5)
        else:
            self.warning.pack_forget()
    def close(self):
        if self.on_close_callback: self.on_close_callback()
        self.window.destroy()

# ============================== GRAPHICAL UI ==============================
class GameUI:
    def __init__(self, root, engine: GameEngine, settings: Settings):
        self.root = root
        self.engine = engine
        self.settings = settings
        engine.ui = self
        self.root.title("Aethelgard's Descent")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=COLORS["bg_dark"])
        self.combat_window = None
        self.combat_text = None
        self.combat_monster_label = None
        self.monster_image_label = None
        self.status_text = None
        self.log_text = None
        self.story_text = None
        self.inv_listbox = None
        self.map_canvas = None
        self.level_label = None
        self.level_update_id = None
        self.image_cache = {}
        self.show_start_screen()
    
    # ----- Missing methods for NPC interactions -----
    def _npc_launch_buy(self, win, npc_id):
        """Launch buy window for the given NPC."""
        win.destroy()  # Close the dialogue window first
        if npc_id == "shopkeeper":
            self.open_npc_shop(self.root)
        elif npc_id == "black_market":
            self.open_black_market_window(self.root)
        else:
            self.log_message("Buy not available from this vendor.")
    
    def _npc_launch_sell(self, win, npc_id):
        """Launch sell window for the given NPC."""
        win.destroy()
        if npc_id == "shopkeeper":
            self.open_npc_sell(self.root)
        else:
            self.log_message("Sell not available from this vendor.")
    
    def _npc_show_quest_list(self, win, npc, quests, text_area):
        """Show quest list for the NPC in the current dialogue window."""
        # Clear the text area to show quest list
        text_area.delete(1.0, tk.END)
        text_area.insert(tk.END, f"{npc.name}: Available quests:\n\n")
        
        # Create a frame for quest list inside the window
        quest_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        quest_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        quest_listbox = tk.Listbox(quest_frame, bg=COLORS["bg_light"], fg=COLORS["text"], height=8)
        quest_listbox.pack(fill=tk.BOTH, expand=True)
        
        quest_objects = []
        for q in quests:
            quest_listbox.insert(tk.END, q.name)
            quest_objects.append(q)
        
        def show_quest_details():
            sel = quest_listbox.curselection()
            if not sel:
                return
            q = quest_objects[sel[0]]
            details = f"{q.name}\n\n{q.description}\n\nObjectives:\n"
            for obj in q.objectives:
                details += f"- {obj['target']}: {obj['current']}/{obj['amount']}\n"
            details += "\nRewards: "
            for r in q.rewards:
                if r["type"] == "gold":
                    details += f"{r['value']} gold, "
                elif r["type"] == "item":
                    details += f"{r['item']}, "
                elif r["type"] == "weapon_upgrade":
                    details += f"Weapon +{r['value']}, "
                elif r["type"] == "shards":
                    details += f"{r['value']} Shards, "
                elif r["type"] == "discount":
                    details += f"{r['value']}% discount, "
                elif r["type"] == "service":
                    details += f"{r['service']} service, "
                elif r["type"] == "unlock_spell":
                    details += f"Unlock {r['spell']}, "
                elif r["type"] == "passive":
                    details += f"Passive: {r['passive']}, "
            details = details.rstrip(", ")
            if messagebox.askyesno("Quest Details", details + "\n\nAccept this quest?"):
                self.engine.accept_quest(q.quest_id)
                win.destroy()
        
        btn_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(btn_frame, text="View/Accept Selected Quest", command=show_quest_details, bg="green", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Back", command=lambda: self._refresh_dialogue(win, npc, text_area, quests), bg="gray", fg="white").pack(side=tk.LEFT, padx=5)
    
    def _refresh_dialogue(self, win, npc, text_area, quests):
        """Refresh the dialogue window back to the quest list state."""
        # Clear the quest frame and button frame
        for widget in win.winfo_children():
            if widget != text_area:
                widget.destroy()
        text_area.delete(1.0, tk.END)
        text_area.insert(tk.END, f"{npc.name}: Choose a quest:\n\n")
        # Recreate the quest list
        self._npc_show_quest_list(win, npc, quests, text_area)
    
    # ----- End of missing methods -----
    
    def load_monster_image(self, monster_name):
        if not PIL_AVAILABLE:
            return None
        name_lower = monster_name.lower().replace(" ", "_").replace(",", "").replace("'", "")
        # Bosses
        if "grave-warden aegis" in name_lower:
            filename = "boss_grave_warden.png"
        elif "pyrophage" in name_lower:
            filename = "boss_pyrophage.png"
        elif "skitter-queen" in name_lower:
            filename = "boss_skitter_queen.png"
        elif "alchemist's failure" in name_lower:
            filename = "boss_alchemists_failure.png"
        elif "high inquisitor malphas" in name_lower:
            filename = "boss_inquisitor_malphas.png"
        elif "clockwork centurion" in name_lower:
            filename = "boss_clockwork_centurion.png"
        elif "glaciara" in name_lower:
            filename = "boss_glaciara.png"
        elif "general drax" in name_lower:
            filename = "boss_general_drax.png"
        elif "mirage weaver" in name_lower:
            filename = "boss_mirage_weaver.png"
        elif "gorgon-queen" in name_lower:
            filename = "boss_gorgon_queen.png"
        elif "abyssal leviathan" in name_lower:
            filename = "boss_abyssal_leviathan.png"
        elif "vampire king" in name_lower:
            filename = "boss_vampire_king.png"
        elif "rust-monster alpha" in name_lower:
            filename = "boss_rust_monster_alpha.png"
        elif "necromancer's amalgam" in name_lower:
            filename = "boss_necromancers_amalgam.png"
        elif "ra-hotep" in name_lower:
            filename = "boss_ra_hotep.png"
        elif "storm-herald avian" in name_lower:
            filename = "boss_storm_herald.png"
        elif "emerald hydra" in name_lower:
            filename = "boss_emerald_hydra.png"
        elif "xar-thul" in name_lower:
            filename = "boss_xar_thul.png"
        elif "iron-bound behemoth" in name_lower:
            filename = "boss_iron_behemoth.png"
        elif "lich king" in name_lower:
            filename = "boss_lich_king.png"
        # Regular monsters
        elif name_lower == "goblin":
            filename = "monster_goblin.png"
        elif name_lower == "orc":
            filename = "monster_orc.png"
        elif name_lower == "skeleton":
            filename = "monster_skeleton.png"
        elif name_lower == "dark_cultist":
            filename = "monster_dark_cultist.png"
        elif name_lower == "giant_rat":
            filename = "monster_giant_rat.png"
        elif name_lower == "troll":
            filename = "monster_troll.png"
        elif name_lower == "ghoul":
            filename = "monster_ghoul.png"
        elif name_lower == "harpy":
            filename = "monster_harpy.png"
        elif name_lower == "minotaur":
            filename = "monster_minotaur.png"
        elif name_lower == "wraith":
            filename = "monster_wraith.png"
        elif name_lower == "mimic":
            filename = "special_mimic.png"
        elif name_lower == "plague_rat":
            filename = "special_plague_rat.png"
        elif name_lower == "skeletal_hoplite":
            filename = "special_skeletal_hoplite.png"
        elif name_lower == "mirage_clone":
            filename = "special_mirage_clone.png"
        elif name_lower == "venomous_grub":
            filename = "special_venomous_grub.png"
        elif name_lower == "shadow_of_the_lich":
            filename = "special_shadow_of_the_lich.png"
        elif name_lower.startswith("zombified"):
            filename = "special_fallen_hero.png"
        else:
            filename = name_lower.replace(" ", "_") + ".png"
        if filename in self.image_cache:
            return self.image_cache[filename]
        path = os.path.join("bestiary", filename)
        if os.path.exists(path):
            try:
                img = Image.open(path)
                img = img.resize((200, 200), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.image_cache[filename] = photo
                return photo
            except Exception as e:
                print(f"Failed to load {path}: {e}")
                return None
        return None
    
    def update_level_display(self):
        try:
            if self.level_label and self.level_label.winfo_exists():
                if self.engine and self.engine.dungeon:
                    self.level_label.config(text=f"LEVEL {self.engine.dungeon.current_level}")
        except (tk.TclError, AttributeError, RuntimeError):
            pass
        try:
            if self.root and self.root.winfo_exists():
                self.level_update_id = self.root.after(1000, self.update_level_display)
        except (tk.TclError, AttributeError):
            pass
    
    def return_to_main_menu(self):
        """Save game and return to main menu without quitting."""
        if self.engine.hero:
            self.engine.save_game()
        # Cancel any pending level updates
        if self.level_update_id:
            try:
                self.root.after_cancel(self.level_update_id)
            except:
                pass
            self.level_update_id = None
        # Show start screen
        self.show_start_screen()
    
    def confirm_quit(self):
        """Quit the game entirely."""
        if messagebox.askyesno("Quit", "Are you sure you want to exit the game? Progress will be saved."):
            self.engine.save_game()
            self.root.quit()
            sys.exit(0)
    
    def show_start_screen(self):
        if hasattr(self, 'level_update_id') and self.level_update_id:
            try:
                self.root.after_cancel(self.level_update_id)
            except:
                pass
            self.level_update_id = None
        for widget in self.root.winfo_children(): widget.destroy()
        title = tk.Label(self.root, text=NARRATIVE_DATA["main_menu"]["title"], font=("Georgia",32,"bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"])
        title.pack(pady=50)
        tagline = tk.Label(self.root, text=NARRATIVE_DATA["main_menu"]["tagline"], font=("Georgia",14,"italic"), fg=COLORS["text"], bg=COLORS["bg_dark"])
        tagline.pack(pady=5)
        frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        frame.pack(pady=20)
        def btn(text, cmd):
            tk.Button(frame, text=text, command=cmd, bg=COLORS["bg_light"], fg=COLORS["text"], width=25, font=("Arial",12)).pack(pady=5)
        btn(NARRATIVE_DATA["main_menu"]["buttons"]["new_game"]["label"], lambda: self.show_hero_selection())
        if os.path.exists("savegame.json"):
            btn(NARRATIVE_DATA["main_menu"]["buttons"]["load_game"]["label"], lambda: self.engine.load_game())
        btn(NARRATIVE_DATA["main_menu"]["buttons"]["codex"]["label"], self.show_codex)
        btn(NARRATIVE_DATA["main_menu"]["buttons"]["ancestral_hall"]["label"], self.show_ancestral_hall)
        btn(NARRATIVE_DATA["main_menu"]["buttons"]["settings"]["label"], self.show_settings)
        btn(NARRATIVE_DATA["main_menu"]["buttons"]["quit"]["label"], self.confirm_quit)
    
    def show_settings(self):
        SettingsUI(self.root, self.settings, on_close_callback=lambda: self.show_start_screen())
    
    def show_hero_selection(self):
        win = tk.Toplevel(self.root)
        win.title("Choose Your Descent")
        win.geometry("500x600")
        win.configure(bg=COLORS["bg_dark"])
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="NAME YOUR HERO", font=("Georgia",16,"bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack(pady=15)
        name_entry = tk.Entry(win, font=("Arial",14), bg=COLORS["bg_light"], fg=COLORS["text"], insertbackground=COLORS["text"])
        name_entry.pack(pady=10, padx=20, fill=tk.X)
        name_entry.insert(0,"Adventurer")
        tk.Label(win, text="CHOOSE YOUR CLASS", font=("Georgia",14,"bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack(pady=15)
        class_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        class_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        selected_class = tk.StringVar(value="Orc Berserker")
        available = list(HERO_TYPES.keys())
        if not self.engine.meta.is_necromancer_unlocked():
            available.remove("Necromancer")
        for ht in available:
            data = HERO_TYPES[ht]
            f = tk.Frame(class_frame, bg=COLORS["bg_light"], relief=tk.RAISED, bd=1)
            f.pack(fill=tk.X, pady=5)
            rb = tk.Radiobutton(f, text=ht, variable=selected_class, value=ht, bg=COLORS["bg_light"], fg=data["color"], selectcolor=COLORS["bg_dark"], font=("Arial",12,"bold"))
            rb.pack(anchor=tk.W, padx=10, pady=5)
            tk.Label(f, text=data["desc"], bg=COLORS["bg_light"], fg=COLORS["text"], font=("Arial",9), wraplength=400, justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=(0,5))
            stats = data["base_stats"]
            stats_text = f"HP:{stats['hp']} MP:{stats['mp']} ATK:{stats['attack']} DEF:{stats['defense']} MAG:{stats['magic']}"
            if stats['mp']==0: stats_text += " (no mana)"
            tk.Label(f, text=stats_text, bg=COLORS["bg_light"], fg=COLORS["grey"], font=("Arial",8)).pack(anchor=tk.W, padx=10, pady=(0,5))
        if not self.engine.meta.is_necromancer_unlocked():
            lock = tk.Frame(class_frame, bg=COLORS["bg_light"], relief=tk.RAISED, bd=1)
            lock.pack(fill=tk.X, pady=5)
            tk.Label(lock, text="NECROMANCER (LOCKED)", bg=COLORS["bg_light"], fg=COLORS["gold_rare"], font=("Arial",12,"bold")).pack(anchor=tk.W, padx=10, pady=5)
            tk.Label(lock, text="Unlock in the Ancestral Hall with 50 Aethelgard's Shards", bg=COLORS["bg_light"], fg=COLORS["text"], font=("Arial",9)).pack(anchor=tk.W, padx=10, pady=(0,5))
        def start():
            name = name_entry.get().strip()
            if not name: name = "Adventurer"
            hero_type = selected_class.get()
            win.destroy()
            self.engine.new_game(name, hero_type)
        tk.Button(win, text="BEGIN DESCENT", command=start, bg=COLORS["highlight"], fg="white", font=("Arial",14,"bold"), width=20).pack(pady=20)
    
    def show_ancestral_hall(self):
        AncestralHallUI(self.root, self.engine.meta, on_close_callback=lambda: self.show_start_screen())
    
    def show_codex(self):
        win = tk.Toplevel(self.root)
        win.title("Adventurer's Codex")
        win.geometry("600x500")
        win.configure(bg=COLORS["bg_dark"])
        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True)
        lore_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(lore_frame, text="Lore")
        lore_text = tk.Text(lore_frame, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD)
        lore_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for entry in self.engine.journal.entries:
            lore_text.insert(tk.END, f"--- {entry['title']} ---\n{entry['content']}\n\n")
        for lore in NARRATIVE_DATA["lore_fragments"]:
            lore_text.insert(tk.END, f"--- {lore['title']} ---\n{lore['text']}\n\nHint: {lore['hint']}\n\n")
        lore_text.config(state=tk.DISABLED)
        quest_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(quest_frame, text="Quests")
        quest_text = tk.Text(quest_frame, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD)
        quest_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        quest_text.insert(tk.END, "=== ACTIVE QUESTS ===\n\n")
        for q in self.engine.quest_manager.active_quests:
            quest_text.insert(tk.END, f"★ {q.name}\n")
            quest_text.insert(tk.END, f"  {q.description}\n")
            for obj in q.objectives:
                quest_text.insert(tk.END, f"  - {obj['target']}: {obj['current']}/{obj['amount']}\n")
            quest_text.insert(tk.END, "\n")
        quest_text.insert(tk.END, "\n=== COMPLETED QUESTS ===\n\n")
        for qid in self.engine.quest_manager.completed_quests:
            q = self.engine.quest_manager.quests_db.get(qid)
            if q:
                quest_text.insert(tk.END, f"✓ {q.name}\n")
        quest_text.config(state=tk.DISABLED)
        boss_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(boss_frame, text="Bosses Slain")
        boss_text = tk.Text(boss_frame, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD)
        boss_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        if self.engine.hero:
            for core in self.engine.hero.boss_cores:
                boss_text.insert(tk.END, f"- {core}\n")
        boss_text.config(state=tk.DISABLED)
        bestiary_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(bestiary_frame, text="Bestiary")
        bestiary_text = tk.Text(bestiary_frame, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD)
        bestiary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for name, data in self.engine.bestiary.items():
            kills = data["kills"]
            lore = "Lore unlocked" if data["lore_unlocked"] else "???"
            ability = "Mastery unlocked (+1 damage)" if data["ability_unlocked"] else "???"
            bestiary_text.insert(tk.END, f"{name}: {kills} kills\n  {lore}\n  {ability}\n\n")
        bestiary_text.config(state=tk.DISABLED)
    
    def build_main_interface(self):
        for widget in self.root.winfo_children(): widget.destroy()
        if self.level_update_id:
            try:
                self.root.after_cancel(self.level_update_id)
            except:
                pass
            self.level_update_id = None
        top_bar = tk.Frame(self.root, bg=COLORS["bg_light"], height=40)
        top_bar.pack(fill=tk.X, padx=10, pady=(5,0))
        self.level_label = tk.Label(top_bar, text="LEVEL 1", font=("Arial",16,"bold"), fg=COLORS["highlight"], bg=COLORS["bg_light"])
        self.level_label.pack(side=tk.LEFT, padx=20, pady=5)
        tk.Label(top_bar, text="AETHELGARD'S DESCENT", font=("Georgia",14,"bold"), fg=COLORS["gold"], bg=COLORS["bg_light"]).pack(side=tk.LEFT, expand=True)
        self.save_label = tk.Label(top_bar, text="", font=("Arial",9), fg=COLORS["green"], bg=COLORS["bg_light"])
        self.save_label.pack(side=tk.RIGHT, padx=20, pady=5)
        main_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        left_panel = tk.Frame(main_frame, bg=COLORS["bg_dark"])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        map_frame = tk.LabelFrame(left_panel, text="Dungeon Map", bg=COLORS["bg_light"], fg=COLORS["text"], font=("Arial",12,"bold"))
        map_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.map_canvas = tk.Canvas(map_frame, bg=COLORS["bg_dark"], width=800, height=600)
        self.map_canvas.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.map_canvas.bind("<Button-3>", self.on_map_right_click)
        story_frame = tk.LabelFrame(left_panel, text="Story", bg=COLORS["bg_light"], fg=COLORS["text"], font=("Arial",12,"bold"))
        story_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        try: story_font = ("UnifrakturMaguntia",12)
        except: story_font = ("Courier",12)
        self.story_text = tk.Text(story_frame, height=6, bg=COLORS["bg_dark"], fg=COLORS["gold_rare"], font=story_font, wrap=tk.WORD, state=tk.DISABLED)
        self.story_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        right_frame = tk.Frame(main_frame, bg=COLORS["bg_dark"])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=5)
        status_frame = tk.LabelFrame(right_frame, text="Hero Status", bg=COLORS["bg_light"], fg=COLORS["text"])
        status_frame.pack(fill=tk.X, pady=5)
        self.status_text = tk.Text(status_frame, height=14, width=30, bg=COLORS["bg_dark"], fg=COLORS["text"], state=tk.DISABLED)
        self.status_text.pack(padx=5, pady=5)
        inv_frame = tk.LabelFrame(right_frame, text="Equipment & Spells", bg=COLORS["bg_light"], fg=COLORS["text"])
        inv_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.inv_listbox = tk.Listbox(inv_frame, bg=COLORS["bg_dark"], fg=COLORS["text"], height=12)
        self.inv_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.inv_listbox.bind("<Double-Button-1>", self.show_item_info)
        self.inv_listbox.bind("<Button-3>", self.on_inv_right_click)
        btn_frame = tk.Frame(inv_frame, bg=COLORS["bg_light"])
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="Equip", command=self.equip_selected, bg=COLORS["highlight"]).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Unequip", command=self.unequip_selected, bg="orange").pack(side=tk.LEFT, padx=2)
        ctrl_frame = tk.LabelFrame(right_frame, text="Controls", bg=COLORS["bg_light"], fg=COLORS["text"])
        ctrl_frame.pack(fill=tk.X, pady=5)
        move_btns = tk.Frame(ctrl_frame, bg=COLORS["bg_light"])
        move_btns.pack(pady=5)
        tk.Button(move_btns, text="↑", command=lambda: self.engine.move(0,-1), width=5).grid(row=0,column=1)
        tk.Button(move_btns, text="←", command=lambda: self.engine.move(-1,0), width=5).grid(row=1,column=0)
        tk.Button(move_btns, text="↓", command=lambda: self.engine.move(0,1), width=5).grid(row=1,column=1)
        tk.Button(move_btns, text="→", command=lambda: self.engine.move(1,0), width=5).grid(row=1,column=2)
        self.root.bind("<Up>", lambda e: self.engine.move(0,-1))
        self.root.bind("<Down>", lambda e: self.engine.move(0,1))
        self.root.bind("<Left>", lambda e: self.engine.move(-1,0))
        self.root.bind("<Right>", lambda e: self.engine.move(1,0))
        action_btns = tk.Frame(ctrl_frame, bg=COLORS["bg_light"])
        action_btns.pack(pady=5)
        def add_shortcut_button(parent, text, underline, command, key):
            btn = tk.Button(parent, text=text, underline=underline, command=command, bg=COLORS["highlight"])
            btn.pack(side=tk.LEFT, padx=2)
            self.root.bind(key, lambda e: command())
            return btn
        add_shortcut_button(action_btns, "Save", 0, self.engine.save_game, "<s>")
        add_shortcut_button(action_btns, "Rest", 0, self.engine.rest, "<r>")
        add_shortcut_button(action_btns, "Armor", 0, self.open_armor_ui, "<o>")
        add_shortcut_button(action_btns, "Accessory", 1, self.open_accessory_ui, "<c>")
        add_shortcut_button(action_btns, "Weapons", 0, self.open_weapons_ui, "<w>")
        add_shortcut_button(action_btns, "Items", 0, self.open_items_ui, "<i>")
        add_shortcut_button(action_btns, "Journal", 0, self.open_journal, "<j>")
        if self.engine.hero and self.engine.hero.legs_armor and self.engine.hero.legs_armor.name == "Boots of the Chronomancer":
            add_shortcut_button(action_btns, "Rewind", 0, self.engine.rewind, "<e>")
        if self.engine.void_chalk_charges > 0:
            add_shortcut_button(action_btns, "Draw Glyph", 0, self.engine.draw_glyph, "<g>")
        # Main Menu button now returns to main menu instead of quitting
        add_shortcut_button(action_btns, "Main Menu", 0, self.return_to_main_menu, "<m>")
        log_frame = tk.LabelFrame(right_frame, text="Event Log", bg=COLORS["bg_light"], fg=COLORS["text"])
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = tk.Text(log_frame, height=6, width=30, bg=COLORS["bg_dark"], fg=COLORS["text"], state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.refresh_all()
        self.update_level_display()
    
    def open_weapons_ui(self):
        win = tk.Toplevel(self.root)
        win.title("Weapons Management")
        win.geometry("500x400")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Available Weapons in Inventory:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        listbox = tk.Listbox(win, bg=COLORS["bg_light"], fg=COLORS["text"])
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        weapon_items = []
        for w in self.engine.hero.weapons_inventory:
            listbox.insert(tk.END, f"{w.weapon_type} (+{w.upgrade_level}) - Dura {w.current_durability}/{w.max_durability}")
            weapon_items.append(w)
        def equip():
            sel = listbox.curselection()
            if sel:
                w = weapon_items[sel[0]]
                # equip_weapon handles adding the currently equipped weapon back to inventory
                self.engine.hero.equip_weapon(w)
                # Remove the newly equipped weapon from weapons_inventory (it's now equipped)
                if w in self.engine.hero.weapons_inventory:
                    self.engine.hero.weapons_inventory.remove(w)
                self.log_message(f"Equipped {w.weapon_type}.")
                win.destroy()
                self.refresh_inventory()
                self.refresh_stats()
        def unequip():
            if self.engine.hero.weapon:
                w = self.engine.hero.weapon
                # unequip_weapon already adds the weapon to weapons_inventory
                self.engine.hero.unequip_weapon()
                self.log_message(f"Unequipped {w.weapon_type}.")
                win.destroy()
                self.refresh_inventory()
                self.refresh_stats()
            else:
                messagebox.showerror("Weapons", "No weapon equipped.")
        btn_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Equip Selected", command=equip, bg=COLORS["highlight"]).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Unequip Current", command=unequip, bg="orange").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=win.destroy, bg="red").pack(side=tk.LEFT, padx=5)
    
    def open_safe_zone(self):
        win = tk.Toplevel(self.root)
        win.title("Safe Zone")
        win.geometry("500x600")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Safe Zone - Choose an option", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=10)
        shop_quests = self.engine.get_available_quests_for_npc("shopkeeper")
        shop_text = "Talk to Shopkeeper"
        if shop_quests:
            shop_text += " (!)"
        tk.Button(win, text=shop_text, command=lambda: self.open_npc_dialogue(win, "shopkeeper"), bg="brown", width=25).pack(pady=5)
        smith_quests = self.engine.get_available_quests_for_npc("blacksmith")
        smith_text = "Smithy (Upgrade/Repair/Buy/Sell)"
        if smith_quests:
            smith_text += " (!)"
        tk.Button(win, text=smith_text, command=lambda: self.open_smithy_window(win), bg="orange", width=25).pack(pady=5)
        altar_quests = self.engine.get_available_quests_for_npc("magic_altar")
        altar_text = "Magic Altar (Manage Spells & Passives)"
        if altar_quests:
            altar_text += " (!)"
        tk.Button(win, text=altar_text, command=lambda: self.open_magic_altar(win), bg="cyan", width=25).pack(pady=5)
        bm_quests = self.engine.get_available_quests_for_npc("black_market")
        bm_text = "Black Market (Buy Legendary)"
        if bm_quests:
            bm_text += " (!)"
        tk.Button(win, text=bm_text, command=lambda: self.open_black_market_window(win), bg="purple", width=25).pack(pady=5)
        tk.Button(win, text="Locker (Store/Retrieve Weapons)", command=lambda: self.open_locker_window(win), bg="blue", width=25).pack(pady=5)
        if self.engine.rune_slab_available:
            tk.Button(win, text="Enchantment Forge (Transfer Enchantment)", command=self.open_enchantment_forge, bg="gold", width=25).pack(pady=5)
        tk.Button(win, text="Close", command=win.destroy, bg="red", width=25).pack(pady=5)
    
    def open_npc_dialogue(self, parent, npc_id):
        if npc_id == "shopkeeper":
            npc = self.engine.shopkeeper
            quests = self.engine.get_available_quests_for_npc("shopkeeper")
        elif npc_id == "blacksmith":
            npc = self.engine.blacksmith_npc
            quests = self.engine.get_available_quests_for_npc("blacksmith")
        elif npc_id == "magic_altar":
            npc = self.engine.magic_altar_npc
            quests = self.engine.get_available_quests_for_npc("magic_altar")
        elif npc_id == "black_market":
            npc = self.engine.black_market_npc
            quests = self.engine.get_available_quests_for_npc("black_market")
        else:
            return
        npc.reset_dialogue()
        # Build dynamic quest list
        if "quest_list" in npc.dialogue_tree:
            options = []
            for q in quests:
                options.append((f"quest_{q.quest_id}", q.name))
            options.append(("start", "Never mind"))
            npc.dialogue_tree["quest_list"]["options"] = options
        win = tk.Toplevel(parent)
        win.title(f"Talk to {npc.name}")
        win.geometry("500x400")
        win.configure(bg=COLORS["bg_dark"])
        text_area = tk.Text(win, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD, height=10)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        btn_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Store current state to handle special actions
        def update():
            state = npc.dialogue_tree.get(npc.current_state, {})
            text = state.get("text", "Goodbye.")
            text_area.delete(1.0, tk.END)
            text_area.insert(tk.END, f"{npc.name}: {text}\n\n")
            for w in btn_frame.winfo_children():
                w.destroy()
            options = state.get("options", [])
            if not options:
                tk.Button(btn_frame, text="Close", command=win.destroy, bg="red").pack()
            else:
                for next_state, opt_text in options:
                    # Special handling for buy/sell states: launch shop windows directly
                    if next_state == "buy":
                        btn = tk.Button(btn_frame, text=opt_text, command=lambda: self._npc_launch_buy(win, npc_id))
                    elif next_state == "sell":
                        btn = tk.Button(btn_frame, text=opt_text, command=lambda: self._npc_launch_sell(win, npc_id))
                    elif next_state == "quest_list":
                        # Show quest list as buttons, not as direct state change
                        btn = tk.Button(btn_frame, text=opt_text, command=lambda ns=next_state: self._npc_show_quest_list(win, npc, quests, text_area))
                    elif next_state.startswith("quest_"):
                        # This is a specific quest item from the quest_list - handled by _npc_show_quest_list
                        # We'll not create buttons here, because quest_list is handled separately.
                        pass
                    else:
                        btn = tk.Button(btn_frame, text=opt_text, command=lambda ns=next_state: handle_choice(ns))
                    btn.pack(fill=tk.X, pady=2)
        
        def handle_choice(next_state):
            npc.current_state = next_state
            update()
        
        update()
    
    def open_npc_shop(self, parent):
        win = tk.Toplevel(parent)
        win.title("Shopkeeper's Wares")
        win.geometry("500x450")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Select an item to buy:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        listbox = tk.Listbox(win, bg=COLORS["bg_light"], fg=COLORS["text"], height=12)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        desc_label = tk.Label(win, text="Item Description:", fg=COLORS["gold"], bg=COLORS["bg_dark"], font=("Arial",10,"bold"))
        desc_label.pack(anchor=tk.W, padx=10, pady=(5,0))
        desc_text = tk.Text(win, height=4, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD, state=tk.DISABLED)
        desc_text.pack(fill=tk.X, padx=10, pady=5)
        items = [("Minor Health Potion",30),("Minor Mana Elixir",25),("Repair Kit",80),("Charcoal Antidote",40),("Vial of Giant's Blood",50),("Healing Salve",20),("Mana Crystal",40)]
        # Apply discount if any
        discount = getattr(self.engine.hero, 'shop_discount', 0.0)
        for name,price in items:
            final_price = int(price * (1 - discount))
            listbox.insert(tk.END, f"{name} - {final_price} gold")
        def on_select(event):
            sel = listbox.curselection()
            if sel:
                name = items[sel[0]][0]
                cons = CONSUMABLES[name]
                desc_text.config(state=tk.NORMAL)
                desc_text.delete(1.0,tk.END)
                desc_text.insert(tk.END, cons.description)
                desc_text.config(state=tk.DISABLED)
        listbox.bind("<<ListboxSelect>>", on_select)
        def buy():
            sel = listbox.curselection()
            if sel:
                name,base_price = items[sel[0]]
                final_price = int(base_price * (1 - discount))
                if self.engine.hero.gold >= final_price:
                    self.engine.hero.gold -= final_price
                    cons = CONSUMABLES[name]
                    self.engine.hero.inventory.append(Item(cons.name,cons.name,"consumable",cons.value,cons.stat_bonus,cons.description))
                    self.engine.ui.log_message(f"Bought {name}. {cons.description}")
                    win.destroy()
                    self.open_npc_shop(parent)
                else:
                    messagebox.showerror("Shop","Not enough gold.")
        tk.Button(win, text="Buy Selected", command=buy, bg="green", fg="white").pack(pady=10)
        tk.Button(win, text="Close", command=win.destroy, bg="red", fg="white").pack(pady=5)
    
    def open_npc_sell(self, parent):
        win = tk.Toplevel(parent)
        win.title("Sell Items")
        win.geometry("500x450")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Select an item to sell:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        listbox = tk.Listbox(win, bg=COLORS["bg_light"], fg=COLORS["text"], height=12)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        desc_label = tk.Label(win, text="Item Description:", fg=COLORS["gold"], bg=COLORS["bg_dark"], font=("Arial",10,"bold"))
        desc_label.pack(anchor=tk.W, padx=10, pady=(5,0))
        desc_text = tk.Text(win, height=4, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD, state=tk.DISABLED)
        desc_text.pack(fill=tk.X, padx=10, pady=5)
        sellable = []
        for item in self.engine.hero.inventory:
            if item.type == "material" or (item.type=="consumable" and item.name not in ["Minor Health Potion","Minor Mana Elixir"]):
                listbox.insert(tk.END, f"{item.name} - sell for {item.value//2} gold")
                sellable.append(item)
        def on_select(event):
            sel = listbox.curselection()
            if sel:
                item = sellable[sel[0]]
                desc_text.config(state=tk.NORMAL)
                desc_text.delete(1.0,tk.END)
                desc_text.insert(tk.END, item.description if item.description else "No description.")
                desc_text.config(state=tk.DISABLED)
        listbox.bind("<<ListboxSelect>>", on_select)
        def sell():
            sel = listbox.curselection()
            if sel:
                item = sellable[sel[0]]
                price = item.value // 2
                self.engine.hero.gold += price
                self.engine.hero.inventory.remove(item)
                self.engine.ui.log_message(f"Sold {item.name} for {price} gold.")
                win.destroy()
                self.open_npc_sell(parent)
        tk.Button(win, text="Sell Selected", command=sell, bg="orange", fg="white").pack(pady=10)
        tk.Button(win, text="Close", command=win.destroy, bg="red", fg="white").pack(pady=5)
    
    def open_journal(self):
        win = tk.Toplevel(self.root)
        win.title("Journal - Lore & Quests")
        win.geometry("600x500")
        win.configure(bg=COLORS["bg_dark"])
        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True)
        lore_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(lore_frame, text="Lore")
        lore_text = tk.Text(lore_frame, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD)
        lore_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for entry in self.engine.journal.entries:
            if entry["category"] in ["lore","boss"]:
                lore_text.insert(tk.END, f"--- {entry['title']} ---\n{entry['content']}\n\n")
        for lore in NARRATIVE_DATA["lore_fragments"]:
            lore_text.insert(tk.END, f"--- {lore['title']} ---\n{lore['text']}\n\nHint: {lore['hint']}\n\n")
        lore_text.config(state=tk.DISABLED)
        quest_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(quest_frame, text="Quests")
        quest_text = tk.Text(quest_frame, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD)
        quest_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        quest_text.insert(tk.END, "=== ACTIVE QUESTS ===\n\n")
        for q in self.engine.quest_manager.active_quests:
            quest_text.insert(tk.END, f"★ {q.name}\n")
            quest_text.insert(tk.END, f"  {q.description}\n")
            for obj in q.objectives:
                quest_text.insert(tk.END, f"  - {obj['target']}: {obj['current']}/{obj['amount']}\n")
            quest_text.insert(tk.END, "\n")
        quest_text.insert(tk.END, "\n=== COMPLETED QUESTS ===\n\n")
        for qid in self.engine.quest_manager.completed_quests:
            q = self.engine.quest_manager.quests_db.get(qid)
            if q:
                quest_text.insert(tk.END, f"✓ {q.name}\n")
        quest_text.config(state=tk.DISABLED)
        boss_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(boss_frame, text="Bosses Slain")
        boss_text = tk.Text(boss_frame, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD)
        boss_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        if self.engine.hero:
            for core in self.engine.hero.boss_cores:
                boss_text.insert(tk.END, f"- {core}\n")
        boss_text.config(state=tk.DISABLED)
        bestiary_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(bestiary_frame, text="Bestiary")
        bestiary_text = tk.Text(bestiary_frame, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD)
        bestiary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for name, data in self.engine.bestiary.items():
            kills = data["kills"]
            lore = "Lore unlocked" if data["lore_unlocked"] else "???"
            ability = "Mastery unlocked (+1 damage)" if data["ability_unlocked"] else "???"
            bestiary_text.insert(tk.END, f"{name}: {kills} kills\n  {lore}\n  {ability}\n\n")
        bestiary_text.config(state=tk.DISABLED)
    
    def open_armor_ui(self):
        win = tk.Toplevel(self.root)
        win.title("Armor Management")
        win.geometry("400x300")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Available Armor in Inventory:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack()
        listbox = tk.Listbox(win, bg=COLORS["bg_light"], fg=COLORS["text"])
        armor_items = []
        for item in self.engine.hero.inventory:
            if item.type == "armor" and item.name in ARMOR_PIECES:
                listbox.insert(tk.END, f"{item.name} - {ARMOR_PIECES[item.name].description[:50]}...")
                armor_items.append(item)
        listbox.pack(fill=tk.BOTH, expand=True)
        def equip():
            sel = listbox.curselection()
            if sel:
                item = armor_items[sel[0]]
                armor = ARMOR_PIECES[item.name]
                self.engine.hero.equip_armor(armor, self.engine)
                self.log_message(f"Equipped {armor.name}.")
                win.destroy()
                self.refresh_inventory()
                self.refresh_stats()
        tk.Button(win, text="Equip Selected", command=equip, bg=COLORS["highlight"]).pack(pady=5)
    
    def open_accessory_ui(self):
        win = tk.Toplevel(self.root)
        win.title("Accessory Management")
        win.geometry("400x300")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Available Accessories in Inventory:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack()
        listbox = tk.Listbox(win, bg=COLORS["bg_light"], fg=COLORS["text"])
        acc_inv = []
        for item in self.engine.hero.inventory:
            if item.type == "accessory":
                desc = ACCESSORIES[item.name].description if item.name in ACCESSORIES else "Unknown accessory"
                listbox.insert(tk.END, f"{item.name} - {desc[:50]}...")
                acc_inv.append(item)
        listbox.pack(fill=tk.BOTH, expand=True)
        def equip():
            sel = listbox.curselection()
            if sel:
                item = acc_inv[sel[0]]
                if item.name in ACCESSORIES:
                    self.engine.hero.equip_accessory(ACCESSORIES[item.name], self.engine)
                    self.log_message(f"Equipped {item.name}.")
                else:
                    self.log_message("Unknown accessory cannot be equipped.")
                win.destroy()
                self.refresh_inventory()
                self.refresh_stats()
        tk.Button(win, text="Equip Selected", command=equip, bg=COLORS["highlight"]).pack(pady=5)
    
    def open_items_ui(self):
        win = tk.Toplevel(self.root)
        win.title("Items (Consumables & Materials)")
        win.geometry("600x500")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Your consumables and materials:", fg=COLORS["text"], bg=COLORS["bg_dark"], font=("Arial",12,"bold")).pack(pady=5)
        list_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox = tk.Listbox(list_frame, bg=COLORS["bg_light"], fg=COLORS["text"], yscrollcommand=scrollbar.set, font=("Arial",10))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        items_list = []
        for item in self.engine.hero.inventory:
            if item.type in ["consumable","material"]:
                listbox.insert(tk.END, f"📦 {item.name} [{item.type}]")
                items_list.append(item)
        win.items_list = items_list
        def on_double_click(event):
            selection = listbox.curselection()
            if selection and hasattr(win, 'items_list'):
                self._show_item_detail_from_list(win.items_list, selection)
        listbox.bind("<Double-Button-1>", on_double_click)
        btn_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        def use_item():
            sel = listbox.curselection()
            if sel and sel[0] < len(items_list):
                item = items_list[sel[0]]
                if item.type == "consumable" and item.name in CONSUMABLES:
                    cons = CONSUMABLES[item.name]
                    self.engine.hero.use_consumable(cons, self.engine)
                    self.engine.hero.inventory.remove(item)
                    self.log_message(f"Used {item.name}.")
                    if item.description:
                        self.display_story(f"You use the {item.name}. {item.description}")
                    if self.engine.in_combat:
                        self.engine.monster_turn()
                    win.destroy()
                    self.open_items_ui()
                    self.refresh_inventory()
                    self.refresh_stats()
                else:
                    self.log_message(f"Cannot use {item.name} here.")
        def sell_item():
            sel = listbox.curselection()
            if sel and sel[0] < len(items_list):
                item = items_list[sel[0]]
                price = item.value // 2
                self.engine.hero.gold += price
                self.engine.hero.inventory.remove(item)
                self.log_message(f"Sold {item.name} for {price} gold.")
                win.destroy()
                self.open_items_ui()
                self.refresh_stats()
        tk.Button(btn_frame, text="Use Selected", command=use_item, bg="green", fg="white", font=("Arial",10,"bold"), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Sell Selected", command=sell_item, bg="orange", fg="white", font=("Arial",10,"bold"), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=win.destroy, bg="red", fg="white", font=("Arial",10,"bold"), width=15).pack(side=tk.RIGHT, padx=5)
        tk.Label(win, text="💡 Double-click any item to see its full description", fg=COLORS["gold"], bg=COLORS["bg_dark"], font=("Arial",9,"italic")).pack(pady=5)
    
    def _show_item_detail_from_list(self, items_list, selection):
        if not selection or not items_list:
            return
        idx = selection[0]
        if idx >= len(items_list):
            return
        item = items_list[idx]
        win = tk.Toplevel(self.root)
        win.title(f"Item Details: {item.name}")
        win.geometry("500x400")
        win.configure(bg=COLORS["bg_dark"])
        win.transient(self.root)
        header_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        icon = "🧪" if item.type == "consumable" else "🔧"
        tk.Label(header_frame, text=f"{icon} {item.name}", font=("Georgia", 18, "bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack()
        type_color = COLORS["green"] if item.type == "consumable" else COLORS["orange"]
        tk.Label(header_frame, text=f"[{item.type.upper()}]", font=("Arial", 10, "bold"), fg=type_color, bg=COLORS["bg_dark"]).pack(pady=5)
        tk.Frame(win, height=2, bg=COLORS["highlight"]).pack(fill=tk.X, padx=20, pady=5)
        desc_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        desc_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        tk.Label(desc_frame, text="DESCRIPTION", font=("Arial", 10, "bold"), fg=COLORS["gold"], bg=COLORS["bg_dark"]).pack(anchor=tk.W)
        desc_text = tk.Text(desc_frame, wrap=tk.WORD, height=6, bg=COLORS["bg_light"], fg=COLORS["text"], font=("Arial", 11))
        desc_text.pack(fill=tk.BOTH, expand=True, pady=5)
        desc_text.insert(tk.END, item.description if item.description else "No additional description available.")
        desc_text.config(state=tk.DISABLED)
        stats_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        tk.Label(stats_frame, text="STATS", font=("Arial", 10, "bold"), fg=COLORS["gold"], bg=COLORS["bg_dark"]).pack(anchor=tk.W)
        stats_info = f"Value: {item.value} gold"
        if item.stat_bonus:
            bonuses = []
            for stat, val in item.stat_bonus.items():
                if stat == "hp":
                    bonuses.append(f"Restores {val} HP")
                elif stat == "mp":
                    bonuses.append(f"Restores {val} MP")
                else:
                    bonuses.append(f"+{val} {stat}")
            if bonuses:
                stats_info += f"\nEffects: {', '.join(bonuses)}"
        tk.Label(stats_frame, text=stats_info, font=("Arial", 10), fg=COLORS["text"], bg=COLORS["bg_dark"], justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        if item.type == "consumable":
            hint_frame = tk.Frame(win, bg=COLORS["bg_dark"])
            hint_frame.pack(fill=tk.X, padx=20, pady=10)
            tk.Label(hint_frame, text="💡 To use this item, select it and click 'Use Selected'", font=("Arial", 9, "italic"), fg=COLORS["gold"], bg=COLORS["bg_dark"]).pack()
        tk.Button(win, text="Close", command=win.destroy, bg=COLORS["bg_light"], fg=COLORS["text"], font=("Arial", 10), width=15).pack(pady=15)
    
    def open_smithy_window(self, parent):
        w = self.engine.hero.weapon
        win = tk.Toplevel(parent)
        win.title("Smithy")
        win.geometry("600x650")
        win.configure(bg=COLORS["bg_dark"])
        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # Upgrade/Repair tab
        repair_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(repair_frame, text="Upgrade / Repair")
        tk.Label(repair_frame, text=f"Weapon: {w.weapon_type} +{w.upgrade_level}", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        tk.Label(repair_frame, text=f"Durability: {w.current_durability}/{w.max_durability}", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        def upgrade():
            cost_scrap = 10 + w.upgrade_level*5
            cost_gold = 100 + w.upgrade_level*20
            if self.engine.hero.scrap_metal >= cost_scrap and self.engine.hero.gold >= cost_gold and w.upgrade_level < 10 and w.max_durability > 0:
                self.engine.hero.scrap_metal -= cost_scrap
                self.engine.hero.gold -= cost_gold
                w.upgrade_level += 1
                w.damage += 2
                w.max_durability += 5
                w.current_durability += 5
                if w.upgrade_level == 5 and len(w.magic_abilities) < 1:
                    new_magic = random.choice(WEAPON_TYPES[w.weapon_type]["magic_pool"])
                    w.magic_abilities.append(new_magic)
                if w.upgrade_level == 10 and len(w.magic_abilities) < 2:
                    new_magic = random.choice(WEAPON_TYPES[w.weapon_type]["magic_pool"])
                    if new_magic not in w.magic_abilities:
                        w.magic_abilities.append(new_magic)
                self.engine.hero._recalc_stats()
                self.log_message("Weapon upgraded!")
                win.destroy()
                self.open_smithy_window(parent)
                self.refresh_stats()
            else:
                messagebox.showerror("Smithy", "Not enough resources or already max or unbreakable.")
        def repair_scrap():
            if self.engine.hero.scrap_metal >= 1 and w.max_durability > 0:
                self.engine.hero.scrap_metal -= 1
                w.repair(10)
                self.log_message("Repaired with scrap.")
                win.destroy()
                self.open_smithy_window(parent)
                self.refresh_stats()
            else:
                messagebox.showerror("Smithy", "No scrap or unbreakable.")
        def repair_gold():
            if self.engine.hero.gold >= 20 and w.max_durability > 0:
                self.engine.hero.gold -= 20
                w.repair(20)
                self.log_message("Repaired with gold.")
                win.destroy()
                self.open_smithy_window(parent)
                self.refresh_stats()
            else:
                messagebox.showerror("Smithy", "Not enough gold or unbreakable.")
        tk.Button(repair_frame, text="Upgrade (+1)", command=upgrade, bg="gold", width=20).pack(pady=5)
        tk.Button(repair_frame, text="Repair (1 Scrap = +10 dura)", command=repair_scrap, bg="gray", width=20).pack(pady=5)
        tk.Button(repair_frame, text="Repair (20 gold = +20 dura)", command=repair_gold, bg="gray", width=20).pack(pady=5)
        # Buy Equipment tab
        buy_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(buy_frame, text="Buy Equipment")
        tk.Label(buy_frame, text="Available Equipment (random selection):", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        equip_listbox = tk.Listbox(buy_frame, bg=COLORS["bg_light"], fg=COLORS["text"], height=10)
        equip_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        equip_desc = tk.Text(buy_frame, height=4, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD, state=tk.DISABLED)
        equip_desc.pack(fill=tk.X, padx=10, pady=5)
        shop_items = []
        for _ in range(3):
            wtype = random.choice(list(WEAPON_TYPES.keys()))
            upgrade = random.randint(0, min(5, self.engine.dungeon.current_level // 2))
            weapon = Weapon(wtype, upgrade, [])
            price = weapon.value * 2
            shop_items.append(("weapon", weapon, price))
        armor_list = list(ARMOR_PIECES.keys())
        for _ in range(2):
            aname = random.choice(armor_list)
            armor = ARMOR_PIECES[aname]
            price = (armor.phys_def + armor.mag_res) * 15
            shop_items.append(("armor", armor, price))
        for item_type, item, price in shop_items:
            if item_type == "weapon":
                equip_listbox.insert(tk.END, f"{item.weapon_type} +{item.upgrade_level} - {price} gold")
            else:
                equip_listbox.insert(tk.END, f"{item.name} - {price} gold")
        def on_equip_select(event):
            sel = equip_listbox.curselection()
            if sel:
                item_type, item, price = shop_items[sel[0]]
                desc_text_str = ""
                if item_type == "weapon":
                    desc_text_str = f"Weapon: {item.weapon_type}\nDamage: {item.damage}\nDurability: {item.max_durability}\nMechanic: {item.mechanic}\nMagic: {', '.join(item.magic_abilities) if item.magic_abilities else 'None'}"
                else:
                    desc_text_str = f"Armor: {item.name}\nSlot: {item.slot}\nDefense: {item.phys_def}\nMagic Resist: {item.mag_res}\nMovement: {item.movement_mod}\n{item.description}"
                equip_desc.config(state=tk.NORMAL)
                equip_desc.delete(1.0, tk.END)
                equip_desc.insert(tk.END, desc_text_str)
                equip_desc.config(state=tk.DISABLED)
        equip_listbox.bind("<<ListboxSelect>>", on_equip_select)
        def buy_equipment():
            sel = equip_listbox.curselection()
            if sel:
                item_type, item, price = shop_items[sel[0]]
                if self.engine.hero.gold >= price:
                    self.engine.hero.gold -= price
                    if item_type == "weapon":
                        self.engine.hero.weapons_inventory.append(item)
                        self.log_message(f"Bought {item.weapon_type}!")
                    else:
                        self.engine.hero.inventory.append(Item(item.name, item.name, "armor", price, {}, item.description))
                        self.log_message(f"Bought {item.name}!")
                    win.destroy()
                    self.open_smithy_window(parent)
                    self.refresh_inventory()
                    self.refresh_stats()
                else:
                    messagebox.showerror("Smithy", "Not enough gold.")
        tk.Button(buy_frame, text="Buy Selected", command=buy_equipment, bg="green", fg="white", width=20).pack(pady=10)
        # Sell Equipment tab
        sell_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(sell_frame, text="Sell Equipment")
        tk.Label(sell_frame, text="Sell weapons and armor for gold:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        sell_listbox = tk.Listbox(sell_frame, bg=COLORS["bg_light"], fg=COLORS["text"], height=12)
        sell_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        sell_desc = tk.Text(sell_frame, height=4, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD, state=tk.DISABLED)
        sell_desc.pack(fill=tk.X, padx=10, pady=5)
        sellable_items = []
        for w in self.engine.hero.weapons_inventory:
            price = w.value // 2
            sell_listbox.insert(tk.END, f"Weapon: {w.weapon_type} +{w.upgrade_level} - {price} gold")
            sellable_items.append((w, price, "weapon"))
        for item in self.engine.hero.inventory:
            if item.type == "armor" and item.name in ARMOR_PIECES:
                price = item.value // 2
                sell_listbox.insert(tk.END, f"Armor: {item.name} - {price} gold")
                sellable_items.append((item, price, "armor"))
        def on_sell_select(event):
            sel = sell_listbox.curselection()
            if sel:
                obj, price, typ = sellable_items[sel[0]]
                desc_str = ""
                if typ == "weapon":
                    desc_str = f"Weapon: {obj.weapon_type}\nDamage: {obj.damage}\nDurability: {obj.current_durability}/{obj.max_durability}\nValue: {obj.value} gold\nSell price: {price}"
                else:
                    armor = ARMOR_PIECES[obj.name]
                    desc_str = f"Armor: {armor.name}\nSlot: {armor.slot}\nDefense: {armor.phys_def}\nMagic Resist: {armor.mag_res}\n{armor.description}\nSell price: {price}"
                sell_desc.config(state=tk.NORMAL)
                sell_desc.delete(1.0, tk.END)
                sell_desc.insert(tk.END, desc_str)
                sell_desc.config(state=tk.DISABLED)
        sell_listbox.bind("<<ListboxSelect>>", on_sell_select)
        def sell_equipment():
            sel = sell_listbox.curselection()
            if sel:
                obj, price, typ = sellable_items[sel[0]]
                self.engine.hero.gold += price
                if typ == "weapon":
                    self.engine.hero.weapons_inventory.remove(obj)
                else:
                    self.engine.hero.inventory.remove(obj)
                self.log_message(f"Sold {obj.name if typ=='armor' else obj.weapon_type} for {price} gold!")
                win.destroy()
                self.open_smithy_window(parent)
                self.refresh_inventory()
                self.refresh_stats()
        tk.Button(sell_frame, text="Sell Selected", command=sell_equipment, bg="orange", fg="white", width=20).pack(pady=10)
    
    def open_magic_altar(self, parent):
        win = tk.Toplevel(parent)
        win.title("Magic Altar")
        win.geometry("700x550")
        win.configure(bg=COLORS["bg_dark"])
        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True)
        # Learn Spells tab
        learn_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(learn_frame, text="Learn Spells")
        tk.Label(learn_frame, text="Available Spells (cost gold to learn)", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack()
        top_frame = tk.Frame(learn_frame, bg=COLORS["bg_dark"])
        top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        spell_list = tk.Listbox(top_frame, bg=COLORS["bg_light"], fg=COLORS["text"], height=12)
        spell_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_frame = tk.Frame(top_frame, bg=COLORS["bg_dark"])
        desc_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        tk.Label(desc_frame, text="Spell Details:", fg=COLORS["gold"], bg=COLORS["bg_dark"], font=("Arial",10,"bold")).pack(anchor=tk.W)
        spell_desc = tk.Text(desc_frame, height=12, width=40, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD, state=tk.DISABLED)
        spell_desc.pack(fill=tk.BOTH, expand=True)
        known = [s.name for s in self.engine.hero.spellbook]
        spell_items = []
        for name in SPELLS.keys():
            if name not in known:
                cost = 50 + len(self.engine.hero.spellbook) * 10
                spell_list.insert(tk.END, f"{name} - Learn for {cost} gold")
                spell_items.append((name, cost))
        def on_spell_select(event):
            sel = spell_list.curselection()
            if sel:
                name, cost = spell_items[sel[0]]
                spell = Spell(name)
                spell_desc.config(state=tk.NORMAL)
                spell_desc.delete(1.0, tk.END)
                spell_desc.insert(tk.END, spell.get_description())
                spell_desc.insert(tk.END, f"\n\nUpgrade cost per level: {spell.upgrade_cost()} gold")
                spell_desc.config(state=tk.DISABLED)
        spell_list.bind("<<ListboxSelect>>", on_spell_select)
        def learn():
            sel = spell_list.curselection()
            if sel:
                name, cost = spell_items[sel[0]]
                if self.engine.hero.gold >= cost:
                    self.engine.hero.gold -= cost
                    self.engine.hero.spellbook.append(Spell(name))
                    self.log_message(f"Learned {name}!")
                    win.destroy()
                    self.open_magic_altar(parent)
                    self.refresh_stats()
                else:
                    messagebox.showerror("Altar", "Not enough gold.")
        tk.Button(learn_frame, text="Learn Selected Spell", command=learn, bg="green").pack(pady=5)
        # Active Spells tab
        active_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(active_frame, text="Active Spells")
        tk.Label(active_frame, text="Select up to 6 spells for loadout", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack()
        active_list = tk.Listbox(active_frame, selectmode=tk.MULTIPLE, height=10)
        active_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for s in self.engine.hero.spellbook:
            active_list.insert(tk.END, s.name)
        def set_active():
            sel = active_list.curselection()
            if len(sel) > 6:
                messagebox.showerror("Altar", "Maximum 6 active spells.")
                return
            self.engine.hero.active_spells = [self.engine.hero.spellbook[i] for i in sel]
            self.log_message("Active spells updated.")
            win.destroy()
            self.open_magic_altar(parent)
            self.refresh_inventory()
        tk.Button(active_frame, text="Set Active Spells", command=set_active, bg="blue").pack(pady=5)
        # Upgrade Spells tab
        upgrade_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(upgrade_frame, text="Upgrade Spells")
        tk.Label(upgrade_frame, text="Upgrade spell level", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack()
        up_top_frame = tk.Frame(upgrade_frame, bg=COLORS["bg_dark"])
        up_top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        upgrade_list = tk.Listbox(up_top_frame, bg=COLORS["bg_light"], fg=COLORS["text"], height=10)
        upgrade_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        up_desc_frame = tk.Frame(up_top_frame, bg=COLORS["bg_dark"])
        up_desc_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        tk.Label(up_desc_frame, text="Spell Details:", fg=COLORS["gold"], bg=COLORS["bg_dark"], font=("Arial",10,"bold")).pack(anchor=tk.W)
        upgrade_desc = tk.Text(up_desc_frame, height=10, width=40, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD, state=tk.DISABLED)
        upgrade_desc.pack(fill=tk.BOTH, expand=True)
        upgrade_spells = []
        for s in self.engine.hero.spellbook:
            upgrade_list.insert(tk.END, f"{s.name} (Lv{s.level}) - Upgrade cost: {s.upgrade_cost()} gold")
            upgrade_spells.append(s)
        def on_upgrade_select(event):
            sel = upgrade_list.curselection()
            if sel:
                s = upgrade_spells[sel[0]]
                upgrade_desc.config(state=tk.NORMAL)
                upgrade_desc.delete(1.0, tk.END)
                upgrade_desc.insert(tk.END, s.get_description())
                upgrade_desc.insert(tk.END, f"\n\nNext level cost: {s.upgrade_cost()} gold")
                upgrade_desc.config(state=tk.DISABLED)
        upgrade_list.bind("<<ListboxSelect>>", on_upgrade_select)
        def upgrade_spell():
            sel = upgrade_list.curselection()
            if sel:
                spell = upgrade_spells[sel[0]]
                cost = spell.upgrade_cost()
                if self.engine.hero.gold >= cost:
                    self.engine.hero.gold -= cost
                    spell.level += 1
                    self.log_message(f"{spell.name} upgraded to level {spell.level}!")
                    win.destroy()
                    self.open_magic_altar(parent)
                    self.refresh_inventory()
                    self.refresh_stats()
                else:
                    messagebox.showerror("Altar", "Not enough gold.")
        tk.Button(upgrade_frame, text="Upgrade Spell", command=upgrade_spell, bg="orange").pack(pady=5)
        # Passive tab
        passive_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(passive_frame, text="Passive")
        tk.Label(passive_frame, text="Choose one passive", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack()
        passive_list = tk.Listbox(passive_frame, height=10)
        passive_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for p in PASSIVES.keys():
            passive_list.insert(tk.END, p)
        def set_passive():
            sel = passive_list.curselection()
            if sel:
                chosen = passive_list.get(sel[0])
                self.engine.hero.active_passive = chosen
                self.engine.hero._recalc_stats()
                self.log_message(f"Passive set to {chosen}.")
                win.destroy()
                self.open_magic_altar(parent)
                self.refresh_stats()
        tk.Button(passive_frame, text="Set Passive", command=set_passive, bg="purple").pack(pady=5)
        # Runes tab
        rune_frame = tk.Frame(notebook, bg=COLORS["bg_dark"])
        notebook.add(rune_frame, text="Runes")
        tk.Label(rune_frame, text="Apply runes (max 3)", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack()
        rune_list = tk.Listbox(rune_frame, height=10)
        rune_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for r in RUNES.keys():
            rune_list.insert(tk.END, r)
        def add_rune():
            sel = rune_list.curselection()
            if sel:
                rune_name = rune_list.get(sel[0])
                if len(self.engine.hero.runes) >= 3:
                    messagebox.showerror("Runes", "Maximum 3 runes.")
                    return
                if rune_name in [r.name for r in self.engine.hero.runes]:
                    messagebox.showerror("Runes", "Rune already active.")
                    return
                if self.engine.hero.gold >= 200:
                    self.engine.hero.gold -= 200
                    self.engine.hero.runes.append(Rune(rune_name))
                    self.log_message(f"Added {rune_name}.")
                    win.destroy()
                    self.open_magic_altar(parent)
                    self.refresh_stats()
                else:
                    messagebox.showerror("Runes", "Not enough gold.")
        tk.Button(rune_frame, text="Add Rune (200 gold)", command=add_rune, bg="cyan").pack(pady=5)
        tk.Button(win, text="Close", command=win.destroy, bg="red").pack(pady=5)
    
    def open_black_market_window(self, parent):
        win = tk.Toplevel(parent)
        win.title("Black Market")
        win.geometry("500x450")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Legendary Item (random)", fg=COLORS["text"], bg=COLORS["bg_dark"], font=("Arial",14,"bold")).pack(pady=10)
        wtype = random.choice(list(WEAPON_TYPES.keys()))
        upgrade = min(5 + self.engine.dungeon.current_level // 4, 10)
        magic = WEAPON_TYPES[wtype]["magic_pool"][:1]
        legendary = Weapon(wtype, upgrade, magic)
        price = legendary.value * 3
        if hasattr(self.engine.hero, 'shop_markup'):
            price = int(price * self.engine.hero.shop_markup)
        desc_text = tk.Text(win, height=8, bg=COLORS["bg_light"], fg=COLORS["text"], wrap=tk.WORD)
        desc_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        desc_text.insert(tk.END, f"Weapon: {legendary.weapon_type} +{legendary.upgrade_level}\n")
        desc_text.insert(tk.END, f"Damage: {legendary.damage}\nDurability: {legendary.max_durability}\n")
        desc_text.insert(tk.END, f"Mechanic: {legendary.mechanic}\n")
        desc_text.insert(tk.END, f"Magic: {', '.join(legendary.magic_abilities) if legendary.magic_abilities else 'None'}\n")
        desc_text.insert(tk.END, f"Price: {price} gold")
        desc_text.config(state=tk.DISABLED)
        def buy():
            if self.engine.hero.gold >= price:
                self.engine.hero.gold -= price
                self.engine.hero.weapons_inventory.append(legendary)
                self.log_message(f"Bought {legendary.weapon_type}!")
                win.destroy()
                self.refresh_inventory()
                self.refresh_stats()
            else:
                messagebox.showerror("Black Market", "Not enough gold.")
        tk.Button(win, text="Buy", command=buy, bg="gold", fg="black", width=20).pack(pady=10)
        tk.Button(win, text="Close", command=win.destroy, bg="red", fg="white", width=20).pack(pady=5)
    
    def open_locker_window(self, parent):
        win = tk.Toplevel(parent)
        win.title("Locker")
        win.geometry("500x400")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Locker (unlimited storage)", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack()
        frame = tk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True)
        listbox = tk.Listbox(frame, bg=COLORS["bg_light"], fg=COLORS["text"])
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for w in self.engine.hero.locker:
            listbox.insert(tk.END, f"{w.weapon_type} +{w.upgrade_level} (Dura {w.current_durability})")
        def store():
            if self.engine.hero.weapon:
                self.engine.hero.locker.append(self.engine.hero.weapon)
                self.engine.hero.weapon = None
                self.log_message("Stored weapon.")
                win.destroy()
                self.open_locker_window(parent)
                self.refresh_stats()
            else:
                messagebox.showerror("Locker", "No weapon equipped.")
        def retrieve():
            sel = listbox.curselection()
            if sel:
                w = self.engine.hero.locker.pop(sel[0])
                if self.engine.hero.weapon:
                    self.engine.hero.locker.append(self.engine.hero.weapon)
                self.engine.hero.weapon = w
                self.log_message(f"Retrieved {w.weapon_type}.")
                win.destroy()
                self.open_locker_window(parent)
                self.refresh_stats()
        tk.Button(win, text="Store Current Weapon", command=store, bg="blue", fg="white").pack(pady=5)
        tk.Button(win, text="Retrieve Selected", command=retrieve, bg="blue", fg="white").pack(pady=5)
    
    def open_enchantment_forge(self):
        win = tk.Toplevel(self.root)
        win.title("Enchantment Forge")
        win.geometry("400x300")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Select source weapon to extract enchantment", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack()
        listbox = tk.Listbox(win, bg=COLORS["bg_light"], fg=COLORS["text"])
        for w in self.engine.hero.weapons_inventory:
            if w.magic_abilities:
                listbox.insert(tk.END, f"{w.weapon_type} (+{w.upgrade_level}) - {', '.join(w.magic_abilities)}")
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        def extract():
            sel = listbox.curselection()
            if sel:
                w = self.engine.hero.weapons_inventory[sel[0]]
                if w.magic_abilities and self.engine.hero.weapon:
                    ability = w.magic_abilities[0]
                    self.engine.hero.weapon.magic_abilities.append(ability)
                    self.engine.hero.weapons_inventory.remove(w)
                    self.engine.rune_slab_available = False
                    self.log_message(f"Transferred {ability} to your equipped weapon!")
                    win.destroy()
                    self.refresh_inventory()
                    self.refresh_stats()
                else:
                    messagebox.showerror("Forge", "No magic ability or no weapon equipped.")
        tk.Button(win, text="Transfer (consumes Blank Rune Slab)", command=extract, bg="gold").pack(pady=10)
    
    def equip_selected(self):
        sel = self.inv_listbox.curselection()
        if not sel:
            return
        text = self.inv_listbox.get(sel[0])
        if text.startswith("[W]"):
            for i, w in enumerate(self.engine.hero.weapons_inventory):
                if f"[W] {w.weapon_type}" in text:
                    self.engine.hero.weapons_inventory.pop(i)
                    self.engine.hero.equip_weapon(w)
                    self.log_message(f"Equipped {w.weapon_type}.")
                    break
        elif text.startswith("[S]"):
            pass
        else:
            for item in self.engine.hero.inventory:
                if item.name in text:
                    if item.type == "armor" and item.name in ARMOR_PIECES:
                        self.engine.hero.equip_armor(ARMOR_PIECES[item.name], self.engine)
                        self.log_message(f"Equipped {item.name}.")
                    elif item.type == "accessory" and item.name in ACCESSORIES:
                        self.engine.hero.equip_accessory(ACCESSORIES[item.name], self.engine)
                        self.log_message(f"Equipped {item.name}.")
                    break
        self.refresh_inventory()
        self.refresh_stats()
    
    def unequip_selected(self):
        options = []
        if self.engine.hero.weapon:
            options.append("weapon")
        if self.engine.hero.armor:
            options.append("armor (legacy)")
        if self.engine.hero.accessory:
            options.append("accessory")
        if self.engine.hero.head_armor:
            options.append("head")
        if self.engine.hero.chest_armor:
            options.append("chest")
        if self.engine.hero.legs_armor:
            options.append("legs")
        if not options:
            self.log_message("Nothing equipped to unequip.")
            return
        win = tk.Toplevel(self.root)
        win.title("Unequip Item")
        win.geometry("300x150")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Select slot to unequip:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=10)
        selected = tk.StringVar(value=options[0])
        ttk.Combobox(win, textvariable=selected, values=options, state="readonly").pack(pady=5)
        def confirm():
            choice = selected.get()
            if choice == "weapon" and self.engine.hero.weapon:
                self.engine.hero.unequip_weapon()
                self.log_message("Unequipped weapon.")
            elif choice == "head":
                self.engine.hero.unequip_armor("head")
                self.log_message("Unequipped head armor.")
            elif choice == "chest":
                self.engine.hero.unequip_armor("chest")
                self.log_message("Unequipped chest armor.")
            elif choice == "legs":
                self.engine.hero.unequip_armor("legs")
                self.log_message("Unequipped leg armor.")
            elif choice == "accessory":
                self.engine.hero.unequip_accessory()
                self.log_message("Unequipped accessory.")
            elif choice == "armor (legacy)" and self.engine.hero.armor:
                self.engine.hero.inventory.append(self.engine.hero.armor)
                self.engine.hero.armor = None
                self.engine.hero._recalc_stats()
                self.log_message("Unequipped armor.")
            win.destroy()
            self.refresh_inventory()
            self.refresh_stats()
        tk.Button(win, text="Unequip", command=confirm, bg="orange").pack(pady=10)
    
    def show_item_info(self, event):
        sel = self.inv_listbox.curselection()
        if not sel:
            return
        text = self.inv_listbox.get(sel[0])
        if text.startswith("[W]"):
            for w in self.engine.hero.weapons_inventory:
                if f"[W] {w.weapon_type}" in text:
                    self._show_weapon_info(w)
                    return
        if text.startswith("[S]"):
            parts = text.split()
            if len(parts) >= 2:
                spell_name = parts[1]
                for s in self.engine.hero.active_spells:
                    if s.name == spell_name:
                        self._show_spell_info(s)
                        return
        if "Weapon:" in text and self.engine.hero.weapon:
            self._show_weapon_info(self.engine.hero.weapon)
            return
        if "Head:" in text and self.engine.hero.head_armor:
            self._show_armor_info(self.engine.hero.head_armor)
            return
        if "Chest:" in text and self.engine.hero.chest_armor:
            self._show_armor_info(self.engine.hero.chest_armor)
            return
        if "Legs:" in text and self.engine.hero.legs_armor:
            self._show_armor_info(self.engine.hero.legs_armor)
            return
        if "Accessory:" in text and self.engine.hero.accessory:
            self._show_accessory_info(self.engine.hero.accessory)
            return
        for item in self.engine.hero.inventory:
            if item.name in text:
                if item.type == "armor" and item.name in ARMOR_PIECES:
                    self._show_armor_info(ARMOR_PIECES[item.name])
                elif item.type == "accessory" and item.name in ACCESSORIES:
                    self._show_accessory_info(ACCESSORIES[item.name])
                elif item.type == "consumable":
                    self._show_consumable_info(item)
                else:
                    self._show_generic_item_info(item)
                return
        self._show_generic_message(text)
    
    def _show_weapon_info(self, w):
        win = tk.Toplevel(self.root)
        win.title(f"Weapon: {w.weapon_type}")
        win.geometry("400x400")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text=w.weapon_type, font=("Arial",16,"bold"), fg=w.get_color(), bg=COLORS["bg_dark"]).pack(pady=10)
        info = f"Rarity: {w.get_rarity()}\nUpgrade Level: +{w.upgrade_level}\nDamage: {w.damage}\nDurability: {w.current_durability}/{w.max_durability}\nMechanic: {w.mechanic}\nMagic Abilities: {', '.join(w.magic_abilities) if w.magic_abilities else 'None'}\nValue: {w.value} gold"
        tk.Label(win, text=info, font=("Arial",11), fg=COLORS["text"], bg=COLORS["bg_dark"], justify=tk.LEFT).pack(pady=10)
        if w.max_durability > 0 and w.upgrade_level < 10:
            tk.Button(win, text="Upgrade (requires Scrap + Gold)", command=lambda: self._upgrade_weapon(w, win), bg=COLORS["gold_rare"]).pack(pady=5)
        tk.Button(win, text="Close", command=win.destroy, bg=COLORS["bg_light"]).pack(pady=10)
    
    def _upgrade_weapon(self, w, parent_win):
        cost_scrap = 10 + w.upgrade_level * 5
        cost_gold = 100 + w.upgrade_level * 20
        if self.engine.hero.scrap_metal >= cost_scrap and self.engine.hero.gold >= cost_gold:
            self.engine.hero.scrap_metal -= cost_scrap
            self.engine.hero.gold -= cost_gold
            w.upgrade_level += 1
            w.damage += 2
            w.max_durability += 5
            w.current_durability += 5
            if w.upgrade_level == 5 and len(w.magic_abilities) < 1:
                new_magic = random.choice(WEAPON_TYPES[w.weapon_type]["magic_pool"])
                w.magic_abilities.append(new_magic)
            if w.upgrade_level == 10 and len(w.magic_abilities) < 2:
                new_magic = random.choice(WEAPON_TYPES[w.weapon_type]["magic_pool"])
                if new_magic not in w.magic_abilities:
                    w.magic_abilities.append(new_magic)
            self.engine.hero._recalc_stats()
            self.log_message(f"Weapon upgraded to +{w.upgrade_level}!")
            parent_win.destroy()
            self.refresh_inventory()
            self.refresh_stats()
        else:
            messagebox.showerror("Upgrade Failed", f"Need {cost_scrap} Scrap and {cost_gold} gold.")
    
    def _show_armor_info(self, a):
        win = tk.Toplevel(self.root)
        win.title(f"Armor: {a.name}")
        win.geometry("400x350")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text=a.name, font=("Arial",16,"bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack(pady=10)
        info = f"Slot: {a.slot}\nTier: {a.tier}\nPhysical Defense: {a.phys_def}\nMagic Resistance: {a.mag_res}\nMovement Modifier: {a.movement_mod}\nDescription: {a.description}"
        tk.Label(win, text=info, font=("Arial",11), fg=COLORS["text"], bg=COLORS["bg_dark"], justify=tk.LEFT).pack(pady=10)
        tk.Button(win, text="Close", command=win.destroy, bg=COLORS["bg_light"]).pack(pady=10)
    
    def _show_accessory_info(self, acc):
        win = tk.Toplevel(self.root)
        win.title(f"Accessory: {acc.name}")
        win.geometry("400x300")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text=acc.name, font=("Arial",16,"bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack(pady=10)
        info = f"Tier: {acc.tier}\nValue: {acc.value} gold\nDescription: {acc.description}\nStat Bonuses: {acc.stat_bonus}"
        tk.Label(win, text=info, font=("Arial",11), fg=COLORS["text"], bg=COLORS["bg_dark"], justify=tk.LEFT).pack(pady=10)
        tk.Button(win, text="Close", command=win.destroy, bg=COLORS["bg_light"]).pack(pady=10)
    
    def _show_consumable_info(self, item):
        win = tk.Toplevel(self.root)
        win.title(f"Item: {item.name}")
        win.geometry("500x400")
        win.configure(bg=COLORS["bg_dark"])
        win.transient(self.root)
        win.grab_set()
        header_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        tk.Label(header_frame, text=f"🧪 {item.name}", font=("Georgia", 18, "bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack()
        tk.Label(header_frame, text="[CONSUMABLE]", font=("Arial", 10, "bold"), fg=COLORS["green"], bg=COLORS["bg_dark"]).pack(pady=5)
        tk.Frame(win, height=2, bg=COLORS["highlight"]).pack(fill=tk.X, padx=20, pady=5)
        tk.Label(win, text="DESCRIPTION", font=("Arial", 11, "bold"), fg=COLORS["gold"], bg=COLORS["bg_dark"]).pack(anchor=tk.W, padx=20, pady=(10,0))
        desc_text = tk.Text(win, wrap=tk.WORD, height=6, bg=COLORS["bg_light"], fg=COLORS["text"], font=("Arial", 11))
        desc_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        desc_text.insert(tk.END, item.description if item.description else "A mysterious consumable item.")
        desc_text.config(state=tk.DISABLED)
        stats_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        tk.Label(stats_frame, text="STATS", font=("Arial", 11, "bold"), fg=COLORS["gold"], bg=COLORS["bg_dark"]).pack(anchor=tk.W)
        stats_info = f"💰 Value: {item.value} gold"
        if item.stat_bonus:
            bonuses = []
            for stat, val in item.stat_bonus.items():
                if stat == "hp":
                    bonuses.append(f"❤️ Restores {val} HP")
                elif stat == "mp":
                    bonuses.append(f"💙 Restores {val} MP")
                else:
                    bonuses.append(f"✨ +{val} {stat}")
            if bonuses:
                stats_info += f"\n📊 Effects: {', '.join(bonuses)}"
        tk.Label(stats_frame, text=stats_info, font=("Arial", 10), fg=COLORS["text"], bg=COLORS["bg_dark"], justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        tk.Button(win, text="Close", command=win.destroy, bg=COLORS["bg_light"], fg=COLORS["text"], font=("Arial", 10), width=15).pack(pady=15)
    
    def _show_spell_info(self, s):
        win = tk.Toplevel(self.root)
        win.title(f"Spell: {s.name}")
        win.geometry("400x300")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text=s.name, font=("Arial",16,"bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack(pady=10)
        info = f"Level: {s.level}\nMana Cost: {s.get_cost()}\nBase Damage: {s.get_damage()}\nCooldown: {s.data.get('cooldown',0)} turns\nEffect: {s.data.get('effect','unknown')}\nUpgrade Cost: {s.upgrade_cost()} gold"
        tk.Label(win, text=info, font=("Arial",11), fg=COLORS["text"], bg=COLORS["bg_dark"], justify=tk.LEFT).pack(pady=10)
        tk.Button(win, text="Close", command=win.destroy, bg=COLORS["bg_light"]).pack(pady=10)
    
    def _show_generic_item_info(self, item):
        win = tk.Toplevel(self.root)
        win.title(f"Item: {item.name}")
        win.geometry("400x250")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text=item.name, font=("Arial",16,"bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack(pady=10)
        info = f"Type: {item.type}\nValue: {item.value} gold\nDescription: {item.description if item.description else 'No additional description.'}"
        tk.Label(win, text=info, font=("Arial",11), fg=COLORS["text"], bg=COLORS["bg_dark"], justify=tk.LEFT).pack(pady=10)
        tk.Button(win, text="Close", command=win.destroy, bg=COLORS["bg_light"]).pack(pady=10)
    
    def _show_generic_message(self, text):
        win = tk.Toplevel(self.root)
        win.title("Item Info")
        win.geometry("400x200")
        win.configure(bg=COLORS["bg_dark"])
        tk.Label(win, text="Item Information", font=("Arial", 16, "bold"), fg=COLORS["highlight"], bg=COLORS["bg_dark"]).pack(pady=15)
        tk.Label(win, text=text, font=("Arial", 11), fg=COLORS["text"], bg=COLORS["bg_dark"], wraplength=350).pack(pady=20)
        tk.Button(win, text="Close", command=win.destroy, bg=COLORS["bg_light"], fg=COLORS["text"]).pack(pady=15)
    
    def on_inv_right_click(self, event):
        sel = self.inv_listbox.curselection()
        if sel:
            text = self.inv_listbox.get(sel[0])
            for item in self.engine.hero.inventory:
                if item.name in text:
                    lore = self.engine.story_gen.get_lore(item.name)
                    self.display_story(f"Inspecting {item.name}: {lore}")
                    return
            self.display_story("No additional lore for this item.")
    
    def on_map_right_click(self, event):
        if self.map_canvas.winfo_width() > 1 and self.map_canvas.winfo_height() > 1:
            tile_width = self.map_canvas.winfo_width() // MAP_WIDTH
            tile_height = self.map_canvas.winfo_height() // MAP_HEIGHT
            x = event.x // tile_width
            y = event.y // tile_height
            if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                self.engine.inspect_tile(x, y)
    
    def log_message(self, msg):
        try:
            if self.log_text and self.log_text.winfo_exists():
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
            else:
                print(msg)
        except tk.TclError:
            print(msg)
    
    def display_story(self, story):
        if self.story_text:
            self.story_text.config(state=tk.NORMAL)
            self.story_text.insert(tk.END, story + "\n\n")
            self.story_text.see(tk.END)
            self.story_text.config(state=tk.DISABLED)
    
    def refresh_all(self):
        self.refresh_stats()
        self.refresh_inventory()
        self.update_map()
    
    def refresh_stats(self):
        if not self.status_text or not self.engine.hero:
            return
        h = self.engine.hero
        stats = f"Name: {h.name}\nType: {h.hero_type}\nLevel: {h.level}  XP: {h.xp}/{h.xp_to_next}\n"
        stats += f"HP: {h.hp}/{h.max_hp}\nMP: {h.mp}/{h.max_mp}\n"
        stats += f"Attack: {h.attack}  Defense: {h.defense}\nMagic: {h.magic}  Dodge: {int(h.dodge_chance*100)}%\n"
        stats += f"Gold: {h.gold}  Scrap: {h.scrap_metal}\n"
        if h.weapon:
            stats += f"Weapon: {h.weapon.weapon_type} (+{h.weapon.upgrade_level})  Dura: {h.weapon.current_durability}/{h.weapon.max_durability}\n"
        if h.active_passive:
            stats += f"Passive: {h.active_passive}\n"
        if h.set_bonus_active:
            stats += f"Set Bonus: {h.set_bonus_active}\n"
        buffs = []
        if h.giant_strength_turns > 0:
            buffs.append(f"Giant's Blood ({h.giant_strength_turns})")
        if h.physical_nerf_turns > 0:
            buffs.append(f"Physical nerf ({h.physical_nerf_turns})")
        if h.phoenix_blessing_turns > 0:
            buffs.append(f"Phoenix Blessing ({h.phoenix_blessing_turns})")
        if h.void_mana_turns > 0:
            buffs.append(f"Void Mana ({h.void_mana_turns})")
        if h.gold_skin_turns > 0:
            buffs.append(f"Liquid Gold ({h.gold_skin_turns})")
        if h.dodge_buff_turns > 0:
            buffs.append(f"Dodge buff ({h.dodge_buff_turns})")
        if h.berserker_rage_turns > 0:
            buffs.append(f"Blood Rage ({h.berserker_rage_turns})")
        if h.ethereal_turns > 0:
            buffs.append(f"Ethereal ({h.ethereal_turns})")
        if h.recall_cast_counter > 0:
            buffs.append(f"Recall casting ({h.recall_cast_counter})")
        if buffs:
            stats += "Buffs: " + ", ".join(buffs) + "\n"
        if self.engine.dread > 0:
            stats += f"Dread: {self.engine.dread}/10\n"
        if self.engine.void_chalk_charges > 0:
            stats += f"Void Chalk: {self.engine.void_chalk_charges} charges\n"
        if h.active_statuses:
            stats += "Statuses: " + ", ".join(f"{k}({v.duration})" for k, v in h.active_statuses.items()) + "\n"
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, stats)
        self.status_text.config(state=tk.DISABLED)
    
    def refresh_inventory(self):
        if not self.inv_listbox or not self.engine.hero:
            return
        self.inv_listbox.delete(0, tk.END)
        self.inv_listbox.insert(tk.END, "--- Equipped ---")
        self.inv_listbox.insert(tk.END, f"Weapon: {self.engine.hero.weapon.weapon_type if self.engine.hero.weapon else 'None'}")
        self.inv_listbox.insert(tk.END, f"Head: {self.engine.hero.head_armor.name if self.engine.hero.head_armor else 'None'}")
        self.inv_listbox.insert(tk.END, f"Chest: {self.engine.hero.chest_armor.name if self.engine.hero.chest_armor else 'None'}")
        self.inv_listbox.insert(tk.END, f"Legs: {self.engine.hero.legs_armor.name if self.engine.hero.legs_armor else 'None'}")
        self.inv_listbox.insert(tk.END, f"Accessory: {self.engine.hero.accessory.name if self.engine.hero.accessory else 'None'}")
        if self.engine.hero.weapons_inventory:
            self.inv_listbox.insert(tk.END, "--- Weapons ---")
            for w in self.engine.hero.weapons_inventory:
                self.inv_listbox.insert(tk.END, f"[W] {w.weapon_type} +{w.upgrade_level} (Dura {w.current_durability})")
        self.inv_listbox.insert(tk.END, "--- Active Spells ---")
        for s in self.engine.hero.active_spells:
            cd = f" (CD:{s.current_cooldown})" if s.current_cooldown > 0 else ""
            self.inv_listbox.insert(tk.END, f"[S] {s.name} Lv{s.level}{cd} Cost:{s.get_cost()}")
    
    def update_map(self):
        if not self.map_canvas or not self.engine.dungeon:
            return
        self.map_canvas.delete("all")
        grid = self.engine.dungeon.levels[self.engine.dungeon.current_level]["grid"]
        w = self.map_canvas.winfo_width() if self.map_canvas.winfo_width() > 1 else 800
        h = self.map_canvas.winfo_height() if self.map_canvas.winfo_height() > 1 else 600
        if w <= 1 or h <= 1:
            return
        cw, ch = w // MAP_WIDTH, h // MAP_HEIGHT
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                room = grid[y][x]
                if room:
                    if room["type"] == "boss":
                        color = COLORS["boss"]
                    elif room["type"] == "treasure":
                        color = COLORS["treasure"]
                    elif room["type"] == "shop":
                        color = COLORS["shop"]
                    else:
                        color = COLORS["visited_cleared"] if room.get("cleared", False) else COLORS["visited_not_cleared"]
                    if not room.get("visited", False):
                        color = COLORS["unvisited"]
                    if self.engine.current_x == x and self.engine.current_y == y:
                        color = COLORS["current"]
                    self.map_canvas.create_rectangle(x * cw, y * ch, (x + 1) * cw, (y + 1) * ch, fill=color, outline=COLORS["text"])
                    icon = ""
                    if self.engine.current_x == x and self.engine.current_y == y:
                        icon = ICONS["current"]
                    elif room["type"] == "boss":
                        icon = ICONS["boss"]
                    elif room["type"] == "treasure":
                        icon = ICONS["chest"]
                    elif room["type"] == "shop":
                        icon = ICONS["shop"]
                    elif not room.get("cleared", False) and room.get("monsters"):
                        icon = ICONS["monster"]
                    elif room.get("cleared", False):
                        icon = ICONS["cleared"]
                    else:
                        icon = ICONS["unknown"]
                    if "features" in room:
                        for f in room["features"]:
                            if f.get("pos") == (x, y) and f.get("visible", False):
                                icon = f["symbol"]
                                break
                    if icon:
                        self.map_canvas.create_text(x * cw + cw // 2, y * ch + ch // 2, text=icon, fill="white", font=("Arial", 12))
    
    def open_combat_window(self, monsters):
        if self.combat_window:
            self.combat_window.destroy()
        self.combat_window = tk.Toplevel(self.root)
        self.combat_window.title("Combat")
        self.combat_window.geometry("600x650")
        self.combat_window.configure(bg=COLORS["bg_dark"])
        self.monster_image_label = tk.Label(self.combat_window, bg=COLORS["bg_dark"])
        self.monster_image_label.pack(pady=5)
        self.combat_monster_label = tk.Label(self.combat_window, text="", fg=COLORS["text"], bg=COLORS["bg_dark"], font=("Arial", 14))
        self.combat_monster_label.pack(pady=5)
        self.combat_text = tk.Text(self.combat_window, height=12, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.combat_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        spell_frame = tk.Frame(self.combat_window, bg=COLORS["bg_dark"])
        spell_frame.pack(pady=5)
        for spell in self.engine.hero.active_spells:
            btn = tk.Button(spell_frame, text=f"{spell.name} ({spell.get_cost()} MP)", command=lambda s=spell: self.engine.combat_action("magic", s.name), bg="blue", fg="white", width=12)
            btn.pack(side=tk.LEFT, padx=2)
        btn_frame = tk.Frame(self.combat_window, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=10)
        def add_combat_shortcut(text, underline, command, key):
            btn = tk.Button(btn_frame, text=text, underline=underline, command=command, width=12)
            btn.pack(side=tk.LEFT, padx=5)
            self.combat_window.bind(key, lambda e: command())
            return btn
        add_combat_shortcut("Attack", 0, lambda: self.engine.combat_action("attack"), "<a>")
        add_combat_shortcut("Special Ability", 0, lambda: self.engine.combat_action("special"), "<s>")
        add_combat_shortcut("Use Item", 0, self.open_combat_item_menu, "<u>")
        add_combat_shortcut("Flee", 0, lambda: self.engine.combat_action("flee"), "<f>")
        self.update_combat_display(monsters)
    
    def open_combat_item_menu(self):
        if not self.engine.in_combat:
            return
        win = tk.Toplevel(self.combat_window)
        win.title("Use Item")
        win.geometry("400x300")
        listbox = tk.Listbox(win)
        cons = [item for item in self.engine.hero.inventory if item.type == "consumable"]
        for item in cons:
            desc_preview = item.description[:40] + "..." if len(item.description) > 40 else item.description
            listbox.insert(tk.END, f"{item.name} - {desc_preview}")
        listbox.pack(fill=tk.BOTH, expand=True)
        def use():
            sel = listbox.curselection()
            if sel:
                item = cons[sel[0]]
                if item.name in CONSUMABLES:
                    self.engine.hero.use_consumable(CONSUMABLES[item.name], self.engine)
                    self.engine.hero.inventory.remove(item)
                    self.engine.ui.log_message(f"Used {item.name}. {item.description}")
                    win.destroy()
                    self.engine.combat_action("attack")
                else:
                    self.log_message("Cannot use that item.")
        tk.Button(win, text="Use", command=use).pack(pady=5)
    
    def update_combat_display(self, monsters):
        if not self.combat_window:
            return
        if monsters and self.engine.combat_index < len(monsters):
            m = monsters[self.engine.combat_index]
            self.combat_monster_label.config(text=f"{m.name}  HP: {m.hp}/{m.max_hp}")
            if PIL_AVAILABLE:
                img = self.load_monster_image(m.name)
                if img:
                    self.monster_image_label.config(image=img)
                    self.monster_image_label.image = img
                else:
                    self.monster_image_label.config(image="", text="[No Image]", compound=tk.CENTER)
            else:
                self.monster_image_label.config(text="PIL not installed", fg="red")
        else:
            self.combat_monster_label.config(text="Victory!")
            if self.monster_image_label:
                self.monster_image_label.config(image="")
    
    def close_combat_window(self):
        if self.combat_window:
            self.combat_window.destroy()
            self.combat_window = None

if __name__ == "__main__":
    root = tk.Tk()
    settings = Settings()
    meta = MetaProgression()
    engine = GameEngine(root, meta, settings)
    GameUI(root, engine, settings)
    root.mainloop()
