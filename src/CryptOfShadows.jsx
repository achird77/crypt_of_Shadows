import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';

/* =====================================================================
   CRYPT OF SHADOWS — React/JSX edition
   The data + engine + dungeon generator below are the SAME tested core
   used before (pure functions, no DOM). The UI is a real React tree:
   dynamic components, hooks, transitions, floating damage, screen shake.
   ===================================================================== */

'use strict';

/* ───────────────────────────── RNG / UTIL ───────────────────────── */
const rnd = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
const chance = (p) => Math.random() < p;
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

/* ───────────────────────────── CLASSES ──────────────────────────── */
const CLASSES = {
  warrior:     { name: 'Warrior',     emoji: '⚔️', color: '#ef4444', atkStat: 'str',
    desc: 'A bulwark of muscle and steel. High strength and constitution; outlasts anything it cannot outhit.',
    base: { str: 16, dex: 12, con: 15, int: 8,  wis: 10, cha: 9  } },
  mage:        { name: 'Mage',        emoji: '🧙', color: '#8b5cf6', atkStat: 'int',
    desc: 'A scholar of fire and lightning. Frail in the body, devastating at range. Mind over matter.',
    base: { str: 8,  dex: 10, con: 10, int: 17, wis: 14, cha: 11 } },
  rogue:       { name: 'Rogue',       emoji: '🗡️', color: '#10b981', atkStat: 'dex',
    desc: 'A blade in the dark. Strikes for critical wounds, slips past blows, and flees when the odds turn.',
    base: { str: 10, dex: 17, con: 11, int: 12, wis: 10, cha: 10 } },
  paladin:     { name: 'Paladin',     emoji: '🛡️', color: '#f59e0b', atkStat: 'str',
    desc: 'A holy warrior wedded to the light. Smites the wicked and mends its own wounds in the same breath.',
    base: { str: 14, dex: 8,  con: 14, int: 10, wis: 13, cha: 11 } },
  necromancer: { name: 'Necromancer', emoji: '💀', color: '#22c55e', atkStat: 'int',
    desc: 'A pact-bound death-mage. Tears life from foes to mend its own flesh. The crypt is its garden.',
    base: { str: 8,  dex: 11, con: 12, int: 16, wis: 13, cha: 10 } },
};
const CLASS_LIST = ['warrior', 'mage', 'rogue', 'paladin', 'necromancer'];

/* ───────────────────────────── SKILLS ───────────────────────────── */
// fields: dmg (multiplier, 0 = none) · heal (frac of maxHp) · lifesteal (frac of dmg dealt)
//         status (applied to enemy) · selfStatus (applied to caster) · mp · lvl
const SKILLS = {
  warrior: [
    { id: 'power_strike', name: 'Power Strike', emoji: '💥', mp: 5,  lvl: 1, dmg: 2.0, desc: 'A crushing overhead blow. 2.0× damage.' },
    { id: 'shield_bash',  name: 'Shield Bash',  emoji: '🛡️', mp: 5,  lvl: 2, dmg: 1.5, status: { type: 'stun', turns: 1, chance: 0.45 }, desc: '1.5× damage with a chance to stun.' },
    { id: 'war_cry',      name: 'War Cry',      emoji: '📯', mp: 8,  lvl: 3, dmg: 0,   heal: 0.25, selfStatus: { type: 'might', turns: 3, value: 0.25 }, desc: 'Heal 25% HP and rage for +25% damage (3 turns).' },
    { id: 'whirlwind',    name: 'Whirlwind',    emoji: '🌪️', mp: 12, lvl: 5, dmg: 2.5, desc: 'A spinning storm of steel. 2.5× damage.' },
    { id: 'berserker',    name: 'Berserker Rage', emoji: '😤', mp: 18, lvl: 8, dmg: 3.0, selfStatus: { type: 'might', turns: 2, value: 0.4 }, desc: '3.0× damage and a burst of fury.' },
    { id: 'titan_strike', name: 'Titan Strike', emoji: '⚡', mp: 26, lvl: 12, dmg: 4.2, status: { type: 'stun', turns: 1, chance: 0.6 }, desc: 'Titanic force. 4.2× damage, likely stun.' },
  ],
  mage: [
    { id: 'fireball',   name: 'Fireball',     emoji: '🔥', mp: 6,  lvl: 1, dmg: 2.0, status: { type: 'burn', turns: 3, value: 0.08, chance: 0.6 }, desc: '2.0× damage, may set the foe ablaze.' },
    { id: 'ice_shard',  name: 'Ice Shard',    emoji: '❄️', mp: 5,  lvl: 2, dmg: 1.8, status: { type: 'freeze', turns: 1, chance: 0.35 }, desc: '1.8× damage, may freeze.' },
    { id: 'arcane_shield', name: 'Arcane Shield', emoji: '🔮', mp: 8, lvl: 3, dmg: 0, heal: 0.2, selfStatus: { type: 'ward', turns: 3, value: 0.3 }, desc: 'Heal 20% HP and ward 30% of incoming damage.' },
    { id: 'lightning',  name: 'Lightning Bolt', emoji: '⚡', mp: 14, lvl: 5, dmg: 2.8, desc: 'A spear of lightning. 2.8× damage.' },
    { id: 'meteor',     name: 'Meteor Storm', emoji: '☄️', mp: 20, lvl: 8, dmg: 3.5, status: { type: 'burn', turns: 3, value: 0.1, chance: 0.8 }, desc: '3.5× damage and lingering fire.' },
    { id: 'arcane_nova', name: 'Arcane Nova', emoji: '💫', mp: 28, lvl: 12, dmg: 4.6, desc: 'Raw arcane annihilation. 4.6× damage.' },
  ],
  rogue: [
    { id: 'backstab',     name: 'Backstab',    emoji: '🗡️', mp: 5,  lvl: 1, dmg: 2.2, desc: 'A strike to the kidneys. 2.2× damage.' },
    { id: 'poison_strike', name: 'Poison Strike', emoji: '☠️', mp: 5, lvl: 2, dmg: 1.7, status: { type: 'poison', turns: 4, value: 0.07, chance: 0.9 }, desc: '1.7× damage and deep venom.' },
    { id: 'evasion',      name: 'Evasion',     emoji: '💨', mp: 6,  lvl: 3, dmg: 0, heal: 0.15, selfStatus: { type: 'evasive', turns: 2, value: 0.5 }, desc: 'Heal 15% HP and gain 50% dodge (2 turns).' },
    { id: 'shadow_step',  name: 'Shadow Step', emoji: '👥', mp: 12, lvl: 5, dmg: 2.6, desc: 'Vanish and reappear blade-first. 2.6× damage.' },
    { id: 'assassinate',  name: 'Assassinate', emoji: '💀', mp: 18, lvl: 8, dmg: 3.6, desc: 'Aim for the throat. 3.6× damage.' },
    { id: 'death_mark',   name: 'Death Mark',  emoji: '⚰️', mp: 24, lvl: 12, dmg: 4.4, status: { type: 'poison', turns: 5, value: 0.1, chance: 1 }, desc: 'Mark for death. 4.4× damage and mortal poison.' },
  ],
  paladin: [
    { id: 'holy_smite', name: 'Holy Smite',   emoji: '✨', mp: 5,  lvl: 1, dmg: 1.8, desc: 'Searing light. 1.8× damage.' },
    { id: 'lay_hands',  name: 'Lay on Hands', emoji: '🙏', mp: 8,  lvl: 2, dmg: 0, heal: 0.3, desc: 'Divine mending. Heal 30% HP.' },
    { id: 'divine_shield', name: 'Divine Shield', emoji: '🛡️', mp: 10, lvl: 3, dmg: 0, heal: 0.2, selfStatus: { type: 'ward', turns: 3, value: 0.4 }, desc: 'Heal 20% HP and ward 40% damage.' },
    { id: 'consecrate', name: 'Consecrate',   emoji: '☀️', mp: 12, lvl: 5, dmg: 2.2, status: { type: 'burn', turns: 2, value: 0.08, chance: 0.7 }, desc: 'Hallowed flame. 2.2× damage.' },
    { id: 'divine_storm', name: 'Divine Storm', emoji: '⛈️', mp: 18, lvl: 8, dmg: 3.0, heal: 0.1, desc: 'Holy tempest. 3.0× damage, heal 10%.' },
    { id: 'judgment',   name: 'Final Judgment', emoji: '👼', mp: 26, lvl: 12, dmg: 3.9, heal: 0.15, desc: 'Pass sentence. 3.9× damage, heal 15%.' },
  ],
  necromancer: [
    { id: 'bone_spear', name: 'Bone Spear',  emoji: '🦴', mp: 6,  lvl: 1, dmg: 1.9, desc: 'Hurl a jagged shard of bone. 1.9× damage.' },
    { id: 'siphon',     name: 'Siphon Life', emoji: '🩸', mp: 7,  lvl: 2, dmg: 1.6, lifesteal: 0.4, desc: '1.6× damage, heal 40% of it.' },
    { id: 'bone_ward',  name: 'Bone Ward',   emoji: '💀', mp: 9,  lvl: 3, dmg: 0, heal: 0.22, selfStatus: { type: 'ward', turns: 2, value: 0.3 }, desc: 'Heal 22% HP and raise a ward of bone.' },
    { id: 'chill_touch', name: 'Chill Touch', emoji: '🫳', mp: 13, lvl: 5, dmg: 2.4, status: { type: 'weaken', turns: 3, value: 0.3, chance: 0.8 }, desc: '2.4× damage and saps the foe’s strength.' },
    { id: 'soul_harvest', name: 'Soul Harvest', emoji: '👻', mp: 19, lvl: 8, dmg: 3.2, lifesteal: 0.5, desc: '3.2× damage, heal half the damage dealt.' },
    { id: 'army_dead',  name: 'Army of the Dead', emoji: '🧟', mp: 28, lvl: 12, dmg: 4.3, lifesteal: 0.35, desc: 'Loose the legions. 4.3× damage with lifesteal.' },
  ],
};

/* ───────────────────────────── ITEMS ────────────────────────────── */
let _iid = 0;
const I = (o) => Object.assign({ id: 'proto_' + (_iid++) }, o);

const WEAPONS = [
  I({ name: 'Rusty Sword',     slot: 'weapon', rarity: 'common', desc: 'A dull, pitted blade.',          dmg: 4,  value: 10,  lvl: 1,  emoji: '🗡️' }),
  I({ name: 'Wooden Staff',    slot: 'weapon', rarity: 'common', desc: 'A simple branch, barely magic.', dmg: 3,  bonus: { int: 2 }, value: 10, lvl: 1, emoji: '🪄' }),
  I({ name: 'Chipped Dagger',  slot: 'weapon', rarity: 'common', desc: 'Small, worn, and quick.',        dmg: 3,  bonus: { dex: 2 }, value: 8, lvl: 1, emoji: '🔪' }),
  I({ name: 'Wooden Mace',     slot: 'weapon', rarity: 'common', desc: 'A crude bludgeon.',              dmg: 5,  value: 12,  lvl: 1,  emoji: '🔨' }),
  I({ name: 'Bone Wand',       slot: 'weapon', rarity: 'common', desc: 'Carved from a femur.',           dmg: 3,  bonus: { int: 2, wis: 1 }, value: 11, lvl: 1, emoji: '🦴' }),
  I({ name: 'Iron Sword',      slot: 'weapon', rarity: 'uncommon', desc: 'A sturdy, honest blade.',      dmg: 8,  value: 30,  lvl: 3,  emoji: '⚔️' }),
  I({ name: 'Oak Staff',       slot: 'weapon', rarity: 'uncommon', desc: 'Seasoned oak, faintly humming.', dmg: 6, bonus: { int: 4 }, value: 35, lvl: 3, emoji: '🪄' }),
  I({ name: 'Steel Dagger',    slot: 'weapon', rarity: 'uncommon', desc: 'Keen on both edges.',          dmg: 7,  bonus: { dex: 3 }, value: 28, lvl: 3, emoji: '🗡️' }),
  I({ name: 'War Hammer',      slot: 'weapon', rarity: 'uncommon', desc: 'Two hands, one purpose.',      dmg: 10, bonus: { str: 2 }, value: 40, lvl: 3, emoji: '🔨' }),
  I({ name: 'Steel Longsword', slot: 'weapon', rarity: 'rare', desc: 'A finely balanced longsword.',     dmg: 14, bonus: { str: 3 }, value: 80, lvl: 5, emoji: '⚔️' }),
  I({ name: 'Crystal Staff',   slot: 'weapon', rarity: 'rare', desc: 'Tipped with a singing crystal.',   dmg: 11, bonus: { int: 6 }, value: 85, lvl: 5, emoji: '🔮' }),
  I({ name: 'Shadow Dagger',   slot: 'weapon', rarity: 'rare', desc: 'It drinks the light around it.',   dmg: 12, bonus: { dex: 5 }, value: 75, lvl: 5, emoji: '🗡️' }),
  I({ name: 'Holy Mace',       slot: 'weapon', rarity: 'rare', desc: 'Blessed and warm to the touch.',   dmg: 13, bonus: { wis: 4 }, value: 90, lvl: 5, emoji: '⚒️' }),
  I({ name: 'Reaper Scythe',   slot: 'weapon', rarity: 'rare', desc: 'Harvests more than wheat.',        dmg: 13, bonus: { int: 4, dex: 2 }, value: 88, lvl: 5, emoji: '🌾' }),
  I({ name: 'Enchanted Blade', slot: 'weapon', rarity: 'epic', desc: 'Runes crawl along the fuller.',    dmg: 20, bonus: { str: 5, dex: 3 }, value: 180, lvl: 8, emoji: '⚔️' }),
  I({ name: 'Arcane Staff',    slot: 'weapon', rarity: 'epic', desc: 'Crackling with raw arcana.',       dmg: 17, bonus: { int: 8, wis: 4 }, value: 200, lvl: 8, emoji: '🪄' }),
  I({ name: "Assassin's Blade", slot: 'weapon', rarity: 'epic', desc: 'Whisper-quiet, wickedly sharp.',  dmg: 18, bonus: { dex: 7, str: 3 }, value: 190, lvl: 8, emoji: '🗡️' }),
  I({ name: 'Blessed Hammer',  slot: 'weapon', rarity: 'epic', desc: 'It hums a hymn when swung.',       dmg: 19, bonus: { str: 4, wis: 5 }, value: 195, lvl: 8, emoji: '🔨' }),
  I({ name: 'Lich Scepter',    slot: 'weapon', rarity: 'epic', desc: 'The dead lean toward it.',         dmg: 17, bonus: { int: 9, con: 3 }, value: 198, lvl: 8, emoji: '🦯' }),
  I({ name: 'Dragonslayer',    slot: 'weapon', rarity: 'legendary', desc: 'Forged to end great wyrms.',  dmg: 28, bonus: { str: 8, dex: 5 }, value: 400, lvl: 12, emoji: '⚔️' }),
  I({ name: 'Staff of Elements', slot: 'weapon', rarity: 'legendary', desc: 'Fire, frost, and storm obey.', dmg: 24, bonus: { int: 12, wis: 6 }, value: 420, lvl: 12, emoji: '🪄' }),
  I({ name: 'Shadowfang',      slot: 'weapon', rarity: 'legendary', desc: 'Drinks the blood of the slain.', dmg: 26, bonus: { dex: 10, str: 5 }, value: 410, lvl: 12, emoji: '🗡️' }),
  I({ name: 'Divine Avenger',  slot: 'weapon', rarity: 'legendary', desc: 'The wrath of heaven, bottled.', dmg: 27, bonus: { str: 7, wis: 8 }, value: 430, lvl: 12, emoji: '🔨' }),
  I({ name: 'Soulrender',      slot: 'weapon', rarity: 'legendary', desc: 'It hungers, and is never full.', dmg: 25, bonus: { int: 11, con: 5 }, value: 425, lvl: 12, emoji: '💀' }),
  I({ name: 'Voidedge',        slot: 'weapon', rarity: 'legendary', desc: 'A sliver of the dark between stars.', dmg: 33, bonus: { str: 9, dex: 9, int: 6 }, value: 700, lvl: 16, emoji: '🌑' }),
  I({ name: 'Sunforged Greatblade', slot: 'weapon', rarity: 'legendary', desc: 'Quenched in a captured sunrise.', dmg: 31, bonus: { str: 10, wis: 10 }, value: 720, lvl: 16, emoji: '🌅' }),
];

const ARMOR = [
  I({ name: 'Cloth Tunic',     slot: 'armor', rarity: 'common', desc: 'Better than nothing. Barely.', def: 2,  value: 8,  lvl: 1, emoji: '👕' }),
  I({ name: 'Leather Armor',   slot: 'armor', rarity: 'common', desc: 'Cured hide, well-worn.',        def: 3,  value: 12, lvl: 1, emoji: '🧥' }),
  I({ name: 'Padded Robe',     slot: 'armor', rarity: 'common', desc: 'Quilted, warm, unimposing.',   def: 2,  bonus: { int: 1 }, value: 10, lvl: 1, emoji: '🥋' }),
  I({ name: 'Chain Mail',      slot: 'armor', rarity: 'uncommon', desc: 'Interlocking rings of iron.', def: 6,  value: 35, lvl: 3, emoji: '🧥' }),
  I({ name: 'Studded Leather', slot: 'armor', rarity: 'uncommon', desc: 'Reinforced and flexible.',   def: 5,  bonus: { dex: 2 }, value: 30, lvl: 3, emoji: '🧥' }),
  I({ name: 'Plate Mail',      slot: 'armor', rarity: 'rare', desc: 'A walking wall of steel.',        def: 10, bonus: { con: 3 }, value: 90, lvl: 5, emoji: '🛡️' }),
  I({ name: 'Scale Mail',      slot: 'armor', rarity: 'rare', desc: 'Overlapping plates like a fish.', def: 8,  bonus: { dex: 2, con: 2 }, value: 80, lvl: 5, emoji: '🧥' }),
  I({ name: 'Shroud of Bone',  slot: 'armor', rarity: 'rare', desc: 'Woven from the ribs of the dead.', def: 8, bonus: { int: 3, con: 2 }, value: 84, lvl: 5, emoji: '🦴' }),
  I({ name: 'Mithril Armor',   slot: 'armor', rarity: 'epic', desc: 'Light as cloth, hard as fate.',   def: 15, bonus: { dex: 4, con: 4 }, value: 200, lvl: 8, emoji: '🛡️' }),
  I({ name: 'Enchanted Robes', slot: 'armor', rarity: 'epic', desc: 'Woven with binding sigils.',      def: 12, bonus: { int: 5, wis: 3 }, value: 180, lvl: 8, emoji: '👘' }),
  I({ name: 'Dragon Scale Armor', slot: 'armor', rarity: 'legendary', desc: 'Plundered from a sleeping wyrm.', def: 22, bonus: { str: 5, con: 8 }, value: 450, lvl: 12, emoji: '🛡️' }),
  I({ name: 'Arcane Vestments', slot: 'armor', rarity: 'legendary', desc: 'Robes of an archmage long dead.', def: 18, bonus: { int: 10, wis: 6 }, value: 420, lvl: 12, emoji: '👘' }),
  I({ name: 'Aegis Plate',     slot: 'armor', rarity: 'legendary', desc: 'Forged in the heart of a star.', def: 27, bonus: { con: 10, str: 6, wis: 6 }, value: 740, lvl: 16, emoji: '✨' }),
];

const SHIELDS = [
  I({ name: 'Wooden Shield',   slot: 'shield', rarity: 'common', desc: 'Splintered but serviceable.',  def: 2,  value: 8,  lvl: 1, emoji: '🛡️' }),
  I({ name: 'Iron Shield',     slot: 'shield', rarity: 'uncommon', desc: 'Dented from honest use.',    def: 4,  value: 30, lvl: 3, emoji: '🛡️' }),
  I({ name: 'Steel Tower Shield', slot: 'shield', rarity: 'rare', desc: 'A door you carry.',           def: 7,  bonus: { con: 2 }, value: 85, lvl: 5, emoji: '🛡️' }),
  I({ name: 'Enchanted Buckler', slot: 'shield', rarity: 'epic', desc: 'Hums when blows draw near.',   def: 10, bonus: { con: 3, wis: 2 }, value: 170, lvl: 8, emoji: '🛡️' }),
  I({ name: 'Aegis of Light',  slot: 'shield', rarity: 'legendary', desc: 'Radiates a protective dawn.', def: 15, bonus: { con: 6, wis: 4 }, value: 380, lvl: 12, emoji: '🛡️' }),
  I({ name: 'Bulwark Eternal', slot: 'shield', rarity: 'legendary', desc: 'No blade has passed it twice.', def: 20, bonus: { con: 9, str: 4 }, value: 700, lvl: 16, emoji: '🛡️' }),
];

const RINGS = [
  I({ name: 'Copper Ring',     slot: 'ring', rarity: 'common', desc: 'A plain band, slightly green.',  bonus: { str: 1 }, value: 10, lvl: 1, emoji: '💍' }),
  I({ name: 'Silver Ring',     slot: 'ring', rarity: 'uncommon', desc: 'Cool and untarnished.',        bonus: { dex: 2, str: 1 }, value: 35, lvl: 3, emoji: '💍' }),
  I({ name: 'Ring of Power',   slot: 'ring', rarity: 'rare', desc: 'It thrums against the bone.',      bonus: { str: 3, int: 3 }, value: 100, lvl: 5, emoji: '💍' }),
  I({ name: 'Ring of the Archmage', slot: 'ring', rarity: 'epic', desc: 'Worn smooth by dead scholars.', bonus: { int: 6, wis: 4 }, value: 220, lvl: 8, emoji: '💍' }),
  I({ name: 'Ring of Omnipotence', slot: 'ring', rarity: 'legendary', desc: 'It knows what you want.',  bonus: { str: 5, dex: 5, int: 5, con: 5 }, value: 500, lvl: 12, emoji: '💍' }),
  I({ name: 'Band of the Spire', slot: 'ring', rarity: 'legendary', desc: 'Forged where heaven touches stone.', bonus: { int: 7, wis: 7, con: 5, cha: 5 }, value: 760, lvl: 16, emoji: '💍' }),
];

const AMULETS = [
  I({ name: 'Bone Amulet',     slot: 'amulet', rarity: 'common', desc: 'Strung on gut.',               bonus: { con: 1, wis: 1 }, value: 10, lvl: 1, emoji: '📿' }),
  I({ name: 'Jade Pendant',    slot: 'amulet', rarity: 'uncommon', desc: 'Cool, green, calming.',      bonus: { wis: 3, con: 2 }, value: 35, lvl: 3, emoji: '📿' }),
  I({ name: 'Ruby Amulet',     slot: 'amulet', rarity: 'rare', desc: 'A trapped coal that never dies.', bonus: { str: 3, con: 4 }, value: 95, lvl: 5, emoji: '📿' }),
  I({ name: 'Amulet of Shadows', slot: 'amulet', rarity: 'epic', desc: 'Eats the candlelight near it.', bonus: { dex: 5, cha: 4, wis: 3 }, value: 210, lvl: 8, emoji: '📿' }),
  I({ name: 'Amulet of Eternity', slot: 'amulet', rarity: 'legendary', desc: 'Death keeps forgetting you.', bonus: { con: 8, wis: 6, cha: 5 }, value: 480, lvl: 12, emoji: '📿' }),
  I({ name: 'Heart of the Star', slot: 'amulet', rarity: 'legendary', desc: 'A captured ember of creation.', bonus: { int: 8, wis: 8, con: 6 }, value: 750, lvl: 16, emoji: '🌟' }),
];

// Consumables. effect fields: heal · mp · revive · damage(combat) · cure · flee · town · buff{type,turns,value} · perm{stat}
const CONSUMABLES = [
  I({ name: 'Small Health Potion',  consumable: true, rarity: 'common',   desc: 'Restores 25 HP.',  heal: 25,  value: 10,  lvl: 1, emoji: '🧪' }),
  I({ name: 'Medium Health Potion', consumable: true, rarity: 'uncommon', desc: 'Restores 60 HP.',  heal: 60,  value: 25,  lvl: 3, emoji: '🧪' }),
  I({ name: 'Large Health Potion',  consumable: true, rarity: 'rare',     desc: 'Restores 120 HP.', heal: 120, value: 50,  lvl: 6, emoji: '🧪' }),
  I({ name: 'Supreme Health Potion', consumable: true, rarity: 'epic',    desc: 'Restores 250 HP.', heal: 250, value: 100, lvl: 10, emoji: '🧪' }),
  I({ name: 'Small Mana Potion',    consumable: true, rarity: 'common',   desc: 'Restores 15 MP.',  mp: 15,    value: 12,  lvl: 1, emoji: '💧' }),
  I({ name: 'Medium Mana Potion',   consumable: true, rarity: 'uncommon', desc: 'Restores 35 MP.',  mp: 35,    value: 30,  lvl: 3, emoji: '💧' }),
  I({ name: 'Large Mana Potion',    consumable: true, rarity: 'rare',     desc: 'Restores 70 MP.',  mp: 70,    value: 55,  lvl: 6, emoji: '💧' }),
  I({ name: 'Supreme Mana Potion',  consumable: true, rarity: 'epic',     desc: 'Restores 150 MP.', mp: 150,   value: 110, lvl: 10, emoji: '💧' }),
  I({ name: 'Elixir of Life',       consumable: true, rarity: 'legendary', desc: 'Full HP and MP.', heal: 9999, mp: 9999, value: 300, lvl: 1, emoji: '✨' }),
  I({ name: 'Antidote',             consumable: true, rarity: 'common',   desc: 'Cures poison and burn.', cure: true, value: 15, lvl: 1, emoji: '🧫' }),
  I({ name: 'Firebomb',             consumable: true, rarity: 'uncommon', desc: 'Hurl for 45 fire damage in combat.', damage: 45, value: 35, lvl: 2, emoji: '💣' }),
  I({ name: 'Greater Firebomb',     consumable: true, rarity: 'rare',     desc: 'Hurl for 110 fire damage in combat.', damage: 110, value: 80, lvl: 7, emoji: '💣' }),
  I({ name: 'Smoke Bomb',           consumable: true, rarity: 'uncommon', desc: 'Guarantees escape from any fight (not bosses).', flee: true, value: 40, lvl: 2, emoji: '🌫️' }),
  I({ name: 'Scroll of Town Portal', consumable: true, rarity: 'uncommon', desc: 'Return instantly to town.', town: true, value: 45, lvl: 1, emoji: '📜' }),
  I({ name: 'Whetstone Draught',    consumable: true, rarity: 'rare',     desc: 'Mighty: +30% damage for 4 turns.', buff: { type: 'might', turns: 4, value: 0.3 }, value: 60, lvl: 4, emoji: '🥃' }),
  I({ name: 'Stoneskin Tonic',      consumable: true, rarity: 'rare',     desc: 'Ward 40% of damage for 4 turns.', buff: { type: 'ward', turns: 4, value: 0.4 }, value: 60, lvl: 4, emoji: '🫙' }),
  I({ name: 'Tome of Strength',     consumable: true, rarity: 'epic',     desc: 'Permanently +1 STR.', perm: 'str', value: 150, lvl: 1, emoji: '📕' }),
  I({ name: 'Tome of Agility',      consumable: true, rarity: 'epic',     desc: 'Permanently +1 DEX.', perm: 'dex', value: 150, lvl: 1, emoji: '📗' }),
  I({ name: 'Tome of Vitality',     consumable: true, rarity: 'epic',     desc: 'Permanently +1 CON.', perm: 'con', value: 150, lvl: 1, emoji: '📘' }),
  I({ name: 'Tome of Intellect',    consumable: true, rarity: 'epic',     desc: 'Permanently +1 INT.', perm: 'int', value: 150, lvl: 1, emoji: '📙' }),
];

const ALL_EQUIP = [...WEAPONS, ...ARMOR, ...SHIELDS, ...RINGS, ...AMULETS];
const RARITY_ORDER = ['common', 'uncommon', 'rare', 'epic', 'legendary'];
// Three player-facing tiers. The original 5 internal grades fold onto these.
const DISPLAY_RARITY = { common: 'Normal', uncommon: 'Normal', normal: 'Normal', rare: 'Rare', epic: 'Epic', legendary: 'Epic' };
const DISPLAY_COLOR = { Normal: '#cbd5e1', Rare: '#4ea1ff', Epic: '#c061ff' };
// Keep the old name->color map working (used as --rc everywhere) but recolor onto the 3 tiers.
const RARITY_COLOR = { common: '#cbd5e1', uncommon: '#cbd5e1', normal: '#cbd5e1', rare: '#4ea1ff', epic: '#c061ff', legendary: '#c061ff' };
function rarityName(it) { return DISPLAY_RARITY[it.rarity] || 'Normal'; }
function rarityColor(it) { return DISPLAY_COLOR[rarityName(it)] || '#cbd5e1'; }

const cloneItem = (it) => Object.assign({}, it, { id: 'item_' + uid() });

/* ───────────────────────── MAGIC ITEM AFFIXES ─────────────────────────
   Generated loot can roll Normal / Rare / Epic. Rare gets one affix, Epic two.
   Affixes bake their bonuses straight into the item (bonus/dmg/def) so the
   existing stat math needs no changes, and are also recorded for display. */
const MAGIC_PREFIX = [
  { w: 'Vicious',  bonus: { str: 1 } },
  { w: 'Nimble',   bonus: { dex: 1 } },
  { w: "Scholar's", bonus: { int: 1 } },
  { w: 'Hardy',    bonus: { con: 1 } },
  { w: 'Hallowed', bonus: { wis: 1 } },
  { w: 'Cruel',    dmgPct: 0.30, slot: ['weapon'] },
  { w: 'Razor',    dmgPct: 0.22, slot: ['weapon'] },
  { w: 'Tempered', defFlat: 2,   slot: ['armor', 'shield'] },
  { w: 'Bulwark',  defFlat: 3,   slot: ['armor', 'shield'] },
];
const MAGIC_SUFFIX = [
  { w: 'of the Bear',   bonus: { con: 1, str: 1 } },
  { w: 'of the Fox',    bonus: { dex: 2 } },
  { w: 'of the Owl',    bonus: { int: 2 } },
  { w: 'of the Saint',  bonus: { wis: 2 } },
  { w: 'of Vigor',      bonus: { con: 2 } },
  { w: 'of Ruin',       dmgPct: 0.40, slot: ['weapon'] },
  { w: 'of the Aegis',  defFlat: 3,   slot: ['armor', 'shield'] },
];
function affixFits(a, item) {
  if (!a.slot) return true;
  return a.slot.includes(item.slot);
}
function applyAffix(item, a, mag, baseDmg) {
  const parts = [];
  if (a.bonus) {
    item.bonus = item.bonus || {};
    for (const k in a.bonus) {
      const v = a.bonus[k] * mag;
      item.bonus[k] = (item.bonus[k] || 0) + v;
      parts.push(`+${v} ${k.toUpperCase()}`);
    }
  }
  if (a.dmgPct && item.slot === 'weapon') {
    const add = Math.max(1, Math.round(baseDmg * a.dmgPct) + mag);
    item.dmg = (item.dmg || 0) + add;
    parts.push(`+${add} DMG`);
  }
  if (a.defFlat && (item.slot === 'armor' || item.slot === 'shield')) {
    const add = a.defFlat + mag;
    item.def = (item.def || 0) + add;
    parts.push(`+${add} DEF`);
  }
  return parts.join(', ');
}
function rollMagicTier(level, isBoss) {
  // deeper floors and bosses tilt the odds toward Rare/Epic
  let rareW = 22 + level * 1.6 + (isBoss ? 25 : 0);
  let epicW = 6 + level * 1.1 + (isBoss ? 18 : 0);
  const normalW = Math.max(8, 70 - level * 1.0);
  const total = normalW + rareW + epicW;
  const r = Math.random() * total;
  if (r < epicW) return 'epic';
  if (r < epicW + rareW) return 'rare';
  return 'normal';
}
function enchant(item, level, isBoss, forceTier) {
  if (!item.slot) return item;                 // only equippable gear gets enchanted
  const tier = forceTier || rollMagicTier(level, isBoss);
  if (tier === 'normal') return item;          // leave the base item (and its own grade) alone
  const baseDmg = item.dmg || 0;
  const n = tier === 'epic' ? 2 : 1;
  const mag = 1 + Math.floor(level / 4) + (tier === 'epic' ? 1 : 0);
  item.affixes = item.affixes || [];
  let prefix = null, suffix = null;
  const preChoices = MAGIC_PREFIX.filter((a) => affixFits(a, item));
  const sufChoices = MAGIC_SUFFIX.filter((a) => affixFits(a, item));
  if (preChoices.length) { prefix = pick(preChoices); const d = applyAffix(item, prefix, mag, baseDmg); if (d) item.affixes.push(d); }
  if (n === 2 && sufChoices.length) { suffix = pick(sufChoices); const d = applyAffix(item, suffix, mag, baseDmg); if (d) item.affixes.push(d); }
  item.baseName = item.baseName || item.name;
  item.name = `${prefix ? prefix.w + ' ' : ''}${item.baseName}${suffix ? ' ' + suffix.w : ''}`;
  item.rarity = tier;                          // now Rare or Epic
  item.magic = true;
  item.value = Math.round((item.value || 10) * (tier === 'epic' ? 2.6 : 1.7));
  return item;
}

/* ───────────────────────────── WORLDS ───────────────────────────── */
const WORLDS = [
  { id: 'crypt',   name: 'Crypt of Shadows', emoji: '💀', floors: 5, minLevel: 1,  theme: 'undead',
    accent: '#6ee7a8', fog: '#04150c', desc: 'Burial vaults where the dead refuse their rest. Bone scrapes on stone in the dark.' },
  { id: 'goblin',  name: 'Goblin Warrens',  emoji: '👺', floors: 5, minLevel: 3,  theme: 'goblin',
    accent: '#a3e635', fog: '#0f1604', desc: 'A reeking maze of tunnels and traps. The little wretches hunt in packs.' },
  { id: 'sunken',  name: 'Sunken Temple',   emoji: '🔱', floors: 6, minLevel: 4,  theme: 'aquatic',
    accent: '#22d3ee', fog: '#04141a', desc: 'A drowned sanctuary half-swallowed by black water. Something still prays below.' },
  { id: 'frozen',  name: 'Frozen Citadel',  emoji: '❄️', floors: 6, minLevel: 6,  theme: 'frost',
    accent: '#7dd3fc', fog: '#08121f', desc: 'A fortress sealed in glacial silence. Frost rimes every blade left behind.' },
  { id: 'thorn',   name: 'Thornwood Hollow', emoji: '🌲', floors: 6, minLevel: 7, theme: 'beast',
    accent: '#86efac', fog: '#0a1407', desc: 'A forest grown wrong, roots like cages. The beasts here have learned our hate.' },
  { id: 'dragon',  name: "Dragon's Lair",   emoji: '🐉', floors: 6, minLevel: 9,  theme: 'dragon',
    accent: '#fb923c', fog: '#1a0a04', desc: 'Lava-veined caverns reeking of sulphur. Heat shimmers over hoarded gold.' },
  { id: 'clock',   name: 'Clockwork Foundry', emoji: '⚙️', floors: 7, minLevel: 11, theme: 'construct',
    accent: '#fcd34d', fog: '#181206', desc: 'An endless engine that builds its own guards. Steam hisses; gears never sleep.' },
  { id: 'abyss',   name: 'Abyssal Depths',  emoji: '😈', floors: 7, minLevel: 13, theme: 'demon',
    accent: '#f472b6', fog: '#16041a', desc: 'A wound in the world leaking hellfire. Names whispered here do not return.' },
  { id: 'spire',   name: 'Celestial Spire', emoji: '🌌', floors: 8, minLevel: 16, theme: 'celestial',
    accent: '#c4b5fd', fog: '#0a0820', desc: 'A tower of light at the end of everything. What guards it was never meant to be fought.' },
];

/* ───────────────────────────── ENEMIES ──────────────────────────── */
// ability: { name, dmg(mult, 0=none), chance, heal(frac maxHp), status{type,turns,value,chance}, msg }
const ENEMIES = {
  undead: [
    { name: 'Skeleton', emoji: '💀', hp: 22, atk: 6, def: 2, abilities: [{ dmg: 1.3, chance: 0.3, msg: 'rakes you with bony claws —' }] },
    { name: 'Zombie',   emoji: '🧟', hp: 30, atk: 5, def: 3, abilities: [{ dmg: 1.5, chance: 0.25, msg: 'lunges and bites —' }] },
    { name: 'Ghost',    emoji: '👻', hp: 18, atk: 8, def: 1, abilities: [{ dmg: 1.8, chance: 0.3, msg: 'wails, chilling your soul —' }] },
    { name: 'Wraith',   emoji: '👤', hp: 28, atk: 9, def: 3, abilities: [{ dmg: 1.5, chance: 0.35, heal: 0.3, msg: 'drains your life —' }] },
    { name: 'Lich King', emoji: '👑', hp: 80, atk: 14, def: 6, boss: true, xpM: 3, goldM: 5, abilities: [
      { dmg: 2.0, chance: 0.4, msg: 'unleashes necrotic fire —' },
      { dmg: 0, chance: 0.25, heal: 0.2, msg: 'knits its bones with dark magic —' },
      { dmg: 1.4, chance: 0.3, status: { type: 'weaken', turns: 2, value: 0.25, chance: 1 }, msg: 'curses your strength —' } ] },
  ],
  goblin: [
    { name: 'Goblin Scout',  emoji: '👺', hp: 25, atk: 8,  def: 3, abilities: [{ dmg: 1.4, chance: 0.3, msg: 'jabs quick and low —' }] },
    { name: 'Goblin Warrior', emoji: '🪓', hp: 35, atk: 10, def: 5, abilities: [{ dmg: 1.6, chance: 0.25, msg: 'slams its shield —' }] },
    { name: 'Goblin Shaman', emoji: '🧙', hp: 22, atk: 12, def: 2, abilities: [{ dmg: 1.8, chance: 0.35, msg: 'hurls a firebolt —' }, { dmg: 0, chance: 0.2, heal: 0.25, msg: 'chants a crude mending —' }] },
    { name: 'Hobgoblin',     emoji: '👹', hp: 45, atk: 13, def: 6, abilities: [{ dmg: 1.7, chance: 0.3, msg: 'cleaves with a great axe —' }] },
    { name: 'Goblin King', emoji: '🤴', hp: 100, atk: 16, def: 8, boss: true, xpM: 3, goldM: 5, abilities: [
      { dmg: 2.0, chance: 0.35, msg: 'brings down a royal strike —' },
      { dmg: 0, chance: 0.2, heal: 0.15, msg: 'roars; its wounds close —' } ] },
  ],
  aquatic: [
    { name: 'Mudfish',   emoji: '🐟', hp: 28, atk: 9,  def: 4, abilities: [{ dmg: 1.4, chance: 0.3, msg: 'thrashes against you —' }] },
    { name: 'Drowned',   emoji: '🧟', hp: 40, atk: 11, def: 5, abilities: [{ dmg: 1.6, chance: 0.3, status: { type: 'poison', turns: 3, value: 0.05, chance: 0.6 }, msg: 'vomits brine —' }] },
    { name: 'Siren',     emoji: '🧜', hp: 34, atk: 14, def: 4, abilities: [{ dmg: 1.7, chance: 0.35, heal: 0.25, msg: 'sings; the song flays you —' }] },
    { name: 'Deep Crab', emoji: '🦀', hp: 50, atk: 12, def: 11, abilities: [{ dmg: 1.6, chance: 0.3, msg: 'crushes you in a claw —' }] },
    { name: 'The Tide-Maw', emoji: '🐙', hp: 150, atk: 22, def: 9, boss: true, xpM: 3.5, goldM: 5, abilities: [
      { dmg: 2.2, chance: 0.35, msg: 'lashes with a forest of arms —' },
      { dmg: 1.6, chance: 0.3, status: { type: 'poison', turns: 4, value: 0.07, chance: 1 }, msg: 'spews venomous ink —' },
      { dmg: 0, chance: 0.15, heal: 0.12, msg: 'sinks beneath the water and mends —' } ] },
  ],
  frost: [
    { name: 'Ice Sprite', emoji: '🧊', hp: 30, atk: 10, def: 4, abilities: [{ dmg: 1.5, chance: 0.3, status: { type: 'freeze', turns: 1, chance: 0.25 }, msg: 'flings a frost bolt —' }] },
    { name: 'Frost Wolf', emoji: '🐺', hp: 40, atk: 14, def: 5, abilities: [{ dmg: 1.6, chance: 0.35, msg: 'bites with icy fangs —' }] },
    { name: 'Ice Golem',  emoji: '🗿', hp: 55, atk: 12, def: 10, abilities: [{ dmg: 1.8, chance: 0.25, msg: 'hammers with frozen fists —' }] },
    { name: 'Frost Giant', emoji: '🏔️', hp: 60, atk: 16, def: 7, abilities: [{ dmg: 2.0, chance: 0.3, msg: 'buries you in an avalanche —' }] },
    { name: 'The Ice Queen', emoji: '👸', hp: 150, atk: 20, def: 10, boss: true, xpM: 3.5, goldM: 5, abilities: [
      { dmg: 2.2, chance: 0.35, status: { type: 'freeze', turns: 1, chance: 0.4 }, msg: 'calls a killing blizzard —' },
      { dmg: 0, chance: 0.2, heal: 0.15, msg: 'drinks the cold and heals —' } ] },
  ],
  beast: [
    { name: 'Dire Rat',   emoji: '🐀', hp: 26, atk: 10, def: 3, abilities: [{ dmg: 1.4, chance: 0.35, status: { type: 'poison', turns: 3, value: 0.05, chance: 0.5 }, msg: 'gnaws a filthy wound —' }] },
    { name: 'Thornback Boar', emoji: '🐗', hp: 48, atk: 13, def: 7, abilities: [{ dmg: 1.7, chance: 0.3, msg: 'gores you on tusks —' }] },
    { name: 'Wild Spriggan', emoji: '🌿', hp: 38, atk: 12, def: 6, abilities: [{ dmg: 1.5, chance: 0.3, heal: 0.2, msg: 'roots drink your blood —' }] },
    { name: 'Great Bear', emoji: '🐻', hp: 64, atk: 17, def: 8, abilities: [{ dmg: 1.9, chance: 0.3, msg: 'mauls with both paws —' }] },
    { name: 'The Antlered King', emoji: '🦌', hp: 175, atk: 24, def: 10, boss: true, xpM: 4, goldM: 5, abilities: [
      { dmg: 2.3, chance: 0.35, msg: 'charges, antlers lowered —' },
      { dmg: 1.5, chance: 0.3, status: { type: 'weaken', turns: 2, value: 0.3, chance: 1 }, msg: 'bellows a spell of withering —' },
      { dmg: 0, chance: 0.15, heal: 0.12, msg: 'the forest mends its hide —' } ] },
  ],
  dragon: [
    { name: 'Kobold',     emoji: '🦎', hp: 35, atk: 12, def: 5, abilities: [{ dmg: 1.4, chance: 0.3, msg: 'thrusts a crude spear —' }] },
    { name: 'Fire Salamander', emoji: '🦎', hp: 45, atk: 16, def: 6, abilities: [{ dmg: 1.7, chance: 0.35, status: { type: 'burn', turns: 2, value: 0.06, chance: 0.5 }, msg: 'breathes scorching flame —' }] },
    { name: 'Drake',      emoji: '🐲', hp: 55, atk: 18, def: 8, abilities: [{ dmg: 1.8, chance: 0.3, msg: 'slashes with razor wings —' }] },
    { name: 'Young Dragon', emoji: '🐉', hp: 70, atk: 22, def: 10, abilities: [{ dmg: 2.0, chance: 0.35, status: { type: 'burn', turns: 3, value: 0.07, chance: 0.5 }, msg: 'looses dragonfire —' }] },
    { name: 'Ancient Red Dragon', emoji: '🐉', hp: 220, atk: 28, def: 14, boss: true, xpM: 4.5, goldM: 6, abilities: [
      { dmg: 2.5, chance: 0.35, status: { type: 'burn', turns: 3, value: 0.08, chance: 0.7 }, msg: 'engulfs you in an inferno —' },
      { dmg: 1.8, chance: 0.25, msg: 'sweeps its mountainous tail —' },
      { dmg: 0, chance: 0.15, heal: 0.1, msg: 'regenerates its smoking wounds —' } ] },
  ],
  construct: [
    { name: 'Cog Sentry', emoji: '🤖', hp: 40, atk: 13, def: 8, abilities: [{ dmg: 1.5, chance: 0.3, msg: 'fires a bolt of brass —' }] },
    { name: 'Steam Hound', emoji: '🐕', hp: 48, atk: 16, def: 7, abilities: [{ dmg: 1.6, chance: 0.35, status: { type: 'burn', turns: 2, value: 0.06, chance: 0.5 }, msg: 'vents scalding steam —' }] },
    { name: 'Iron Golem', emoji: '🗿', hp: 70, atk: 15, def: 14, abilities: [{ dmg: 1.8, chance: 0.25, msg: 'pounds with piston arms —' }] },
    { name: 'Spark Wisp', emoji: '⚡', hp: 44, atk: 20, def: 6, abilities: [{ dmg: 1.9, chance: 0.35, status: { type: 'stun', turns: 1, chance: 0.3 }, msg: 'discharges raw current —' }] },
    { name: 'The Great Engine', emoji: '⚙️', hp: 260, atk: 30, def: 16, boss: true, xpM: 5, goldM: 7, abilities: [
      { dmg: 2.4, chance: 0.35, msg: 'slams a piston the size of a door —' },
      { dmg: 1.7, chance: 0.3, status: { type: 'stun', turns: 1, chance: 0.5 }, msg: 'overloads, arcing lightning —' },
      { dmg: 0, chance: 0.15, heal: 0.12, msg: 'reroutes power and self-repairs —' } ] },
  ],
  demon: [
    { name: 'Imp',        emoji: '👿', hp: 40, atk: 16, def: 5, abilities: [{ dmg: 1.6, chance: 0.35, status: { type: 'burn', turns: 2, value: 0.06, chance: 0.5 }, msg: 'spits hellfire —' }] },
    { name: 'Demon Soldier', emoji: '😡', hp: 60, atk: 20, def: 10, abilities: [{ dmg: 1.8, chance: 0.3, msg: 'hacks with a black blade —' }] },
    { name: 'Succubus',   emoji: '😈', hp: 50, atk: 22, def: 6, abilities: [{ dmg: 1.7, chance: 0.35, heal: 0.3, msg: 'drains your very soul —' }] },
    { name: 'Pit Fiend',  emoji: '🔥', hp: 80, atk: 25, def: 12, abilities: [{ dmg: 2.0, chance: 0.3, msg: 'strikes with abyssal force —' }] },
    { name: 'The Demon Lord', emoji: '👹', hp: 320, atk: 35, def: 16, boss: true, xpM: 5.5, goldM: 8, abilities: [
      { dmg: 2.5, chance: 0.3, status: { type: 'burn', turns: 3, value: 0.09, chance: 0.7 }, msg: 'unleashes the apocalypse —' },
      { dmg: 2.0, chance: 0.25, heal: 0.2, msg: 'devours your essence —' },
      { dmg: 3.0, chance: 0.15, msg: 'calls down a hellstorm —' } ] },
  ],
  celestial: [
    { name: 'Lantern Wisp', emoji: '🕯️', hp: 55, atk: 20, def: 8, abilities: [{ dmg: 1.6, chance: 0.3, msg: 'sears you with pure light —' }] },
    { name: 'Watcher',    emoji: '👁️', hp: 70, atk: 24, def: 10, abilities: [{ dmg: 1.8, chance: 0.35, status: { type: 'weaken', turns: 2, value: 0.25, chance: 0.6 }, msg: 'gazes; your will falters —' }] },
    { name: 'Star Seraph', emoji: '😇', hp: 80, atk: 26, def: 11, abilities: [{ dmg: 1.9, chance: 0.3, heal: 0.2, msg: 'sings a hymn that burns —' }] },
    { name: 'Throne Guard', emoji: '🛡️', hp: 110, atk: 28, def: 18, abilities: [{ dmg: 2.0, chance: 0.3, msg: 'smites with a sword of dawn —' }] },
    { name: 'The Fallen Throne', emoji: '🌟', hp: 420, atk: 40, def: 20, boss: true, xpM: 7, goldM: 10, abilities: [
      { dmg: 2.6, chance: 0.3, msg: 'judges you with a pillar of light —' },
      { dmg: 2.0, chance: 0.25, status: { type: 'stun', turns: 1, chance: 0.5 }, msg: 'a chord of creation stuns you —' },
      { dmg: 0, chance: 0.15, heal: 0.15, msg: 'draws on the heavens and mends —' },
      { dmg: 3.2, chance: 0.1, msg: 'speaks a word that should end you —' } ] },
  ],
};

/* ───────────────────────────── DIFFICULTY ───────────────────────── */
const DIFFICULTIES = {
  easy:      { name: 'Acolyte',   emoji: '🕯️', desc: 'A gentler descent. Foes hit softly; rewards flow freely. For learning the dark.',
    enemyHp: 0.8, enemyDmg: 0.7, xp: 1.25, gold: 1.25, trap: 0.7, perma: false },
  normal:    { name: 'Adventurer', emoji: '⚔️', desc: 'The crypt as it was meant to be walked. Fair, but it bites.',
    enemyHp: 1.0, enemyDmg: 1.0, xp: 1.0, gold: 1.0, trap: 1.0, perma: false },
  hard:      { name: 'Veteran',   emoji: '💀', desc: 'Tougher foes, thinner loot. The dark has learned your tricks.',
    enemyHp: 1.35, enemyDmg: 1.3, xp: 1.1, gold: 0.9, trap: 1.3, perma: false },
  nightmare: { name: 'Nightmare', emoji: '☠️', desc: 'Brutal scaling — and death is permanent. Your save dies with you.',
    enemyHp: 1.7, enemyDmg: 1.6, xp: 1.3, gold: 1.0, trap: 1.6, perma: true },
};

/* ───────────────────────────── ENGINE ───────────────────────────── */
const xpToNext = (lvl) => Math.floor(80 * Math.pow(lvl, 1.5));

function equipBonus(hero) {
  const b = { str: 0, dex: 0, con: 0, int: 0, wis: 0, cha: 0 };
  for (const slot of ['weapon', 'armor', 'shield', 'ring', 'amulet']) {
    const it = hero.equipment[slot];
    if (it && it.bonus) for (const k in it.bonus) b[k] += it.bonus[k];
  }
  return b;
}

function recalc(hero) {
  const b = equipBonus(hero);
  hero.maxHp = 30 + (hero.stats.con + b.con) * 3 + hero.level * 8;
  hero.maxMp = 15 + (hero.stats.int + b.int) * 2 + (hero.stats.wis + b.wis) + hero.level * 4;
  hero.hp = Math.min(hero.hp, hero.maxHp);
  hero.mp = Math.min(hero.mp, hero.maxMp);
}

function attackPower(hero) {
  const b = equipBonus(hero);
  const wpn = hero.equipment.weapon ? hero.equipment.weapon.dmg : 2;
  const stat = CLASSES[hero.heroClass].atkStat;
  return wpn + Math.floor((hero.stats[stat] + b[stat]) * 0.8) + hero.level;
}
function defensePower(hero) {
  const b = equipBonus(hero);
  const armor = (hero.equipment.armor ? hero.equipment.armor.def : 0) + (hero.equipment.shield ? hero.equipment.shield.def : 0);
  return armor + Math.floor((hero.stats.con + b.con) * 0.4) + Math.floor(hero.level * 0.5);
}

function startingItems(cls) {
  const out = [cloneItem(CONSUMABLES[0]), cloneItem(CONSUMABLES[0]), cloneItem(CONSUMABLES[4]), cloneItem(CONSUMABLES[9])];
  const W = (n) => cloneItem(WEAPONS.find((w) => w.name === n));
  const A = (n) => cloneItem(ARMOR.find((a) => a.name === n));
  const S = (n) => cloneItem(SHIELDS.find((s) => s.name === n));
  if (cls === 'warrior') { out.push(W('Rusty Sword'), A('Leather Armor'), S('Wooden Shield')); }
  else if (cls === 'mage') { out.push(W('Wooden Staff'), A('Padded Robe')); }
  else if (cls === 'rogue') { out.push(W('Chipped Dagger'), A('Leather Armor')); }
  else if (cls === 'paladin') { out.push(W('Wooden Mace'), A('Leather Armor'), S('Wooden Shield')); }
  else if (cls === 'necromancer') { out.push(W('Bone Wand'), A('Padded Robe')); }
  return out;
}

function createHero(name, cls) {
  const base = Object.assign({}, CLASSES[cls].base);
  const skills = SKILLS[cls].filter((s) => s.lvl <= 1).map((s) => Object.assign({}, s));
  const hero = {
    name, heroClass: cls, level: 1, xp: 0, xpToNext: xpToNext(1),
    hp: 1, maxHp: 1, mp: 1, maxMp: 1, stats: base,
    equipment: { weapon: null, armor: null, shield: null, ring: null, amulet: null },
    inventory: [], skills, gold: 40, statPoints: 0,
  };
  for (const it of startingItems(cls)) {
    if (it.slot && !hero.equipment[it.slot]) hero.equipment[it.slot] = it;
    else hero.inventory.push(it);
  }
  recalc(hero); hero.hp = hero.maxHp; hero.mp = hero.maxMp;
  return hero;
}

// ── status helpers ──
function addStatus(target, st) {
  if (!st) return;
  if (st.chance !== undefined && !chance(st.chance)) return;
  target.statuses = target.statuses || [];
  const existing = target.statuses.find((s) => s.type === st.type);
  if (existing) { existing.turns = Math.max(existing.turns, st.turns); if (st.value) existing.value = st.value; }
  else target.statuses.push({ type: st.type, turns: st.turns, value: st.value || 0 });
}
function hasStatus(t, type) { return (t.statuses || []).some((s) => s.type === type); }
function statusValue(t, type) { const s = (t.statuses || []).find((x) => x.type === type); return s ? s.value : 0; }

// tick DoT/expiry at the start of an actor's turn. returns log lines, mutates actor.
function tickStatuses(actor, isHero, diff) {
  const log = [];
  if (!actor.statuses || !actor.statuses.length) return log;
  for (const s of actor.statuses) {
    if (s.type === 'poison' || s.type === 'burn') {
      const max = isHero ? actor.maxHp : actor.maxHp;
      let dmg = Math.max(1, Math.floor(max * s.value));
      if (isHero) dmg = Math.floor(dmg * (diff ? diff.enemyDmg : 1)); // DoT on hero scaled by diff
      actor.hp -= dmg;
      const icon = s.type === 'poison' ? '☠️' : '🔥';
      log.push(`${icon} ${isHero ? 'You suffer' : (actor.name + ' suffers')} ${dmg} ${s.type} damage.`);
    }
    if (s.type === 'regen') {
      const heal = Math.max(1, Math.floor(actor.maxHp * s.value));
      actor.hp = Math.min(actor.maxHp, actor.hp + heal);
      log.push(`💚 ${isHero ? 'You regenerate' : actor.name + ' regenerates'} ${heal} HP.`);
    }
    s.turns -= 1;
  }
  actor.statuses = actor.statuses.filter((s) => s.turns > 0);
  return log;
}

function playerDamage(hero, mult) {
  const base = attackPower(hero);
  const variance = 0.85 + Math.random() * 0.3;
  let might = 1 + statusValue(hero, 'might');
  return Math.max(1, Math.floor(base * mult * variance * might));
}
function enemyDamageRoll(enemy, mult, diff) {
  const variance = 0.8 + Math.random() * 0.4;
  const weak = 1 - statusValue(enemy, 'weaken');
  return Math.max(1, Math.floor(enemy.attack * mult * variance * weak * (diff ? diff.enemyDmg : 1)));
}

// Player offensive action. action: {kind:'attack'} | {kind:'skill', skill} | {kind:'item', item}
function playerAction(hero, enemy, action, diff) {
  const log = [];
  if (action.kind === 'skill') {
    const sk = action.skill;
    if (hero.mp < sk.mp) { log.push(`Not enough mana for ${sk.name}.`); return { log, spent: false }; }
    hero.mp -= sk.mp;
    if (sk.heal) { const h = Math.floor(hero.maxHp * sk.heal); hero.hp = Math.min(hero.maxHp, hero.hp + h); log.push(`${sk.emoji} ${sk.name} — you mend ${h} HP.`); }
    if (sk.selfStatus) { addStatus(hero, Object.assign({}, sk.selfStatus, { chance: 1 })); log.push(`✨ ${sk.name} empowers you.`); }
    if (sk.dmg > 0) {
      const raw = playerDamage(hero, sk.dmg);
      const dmg = Math.max(1, raw - Math.floor(enemy.defense * 0.5));
      enemy.hp -= dmg; log.push(`${sk.emoji} ${sk.name} hits ${enemy.name} for ${dmg}.`); log._float = { side: 'enemy', text: '-' + dmg };
      if (sk.lifesteal) { const h = Math.floor(dmg * sk.lifesteal); hero.hp = Math.min(hero.maxHp, hero.hp + h); log.push(`🩸 You drain ${h} HP.`); }
      if (sk.status) { addStatus(enemy, sk.status); if (hasStatus(enemy, sk.status.type)) log.push(`  ${enemy.name} is afflicted with ${sk.status.type}.`); }
    }
    return { log, spent: true };
  }
  if (action.kind === 'item') {
    const it = action.item; const idx = hero.inventory.findIndex((x) => x.id === it.id);
    if (idx === -1) { log.push('Item not found.'); return { log, spent: false }; }
    const r = applyConsumable(hero, it, enemy);
    log.push(`🧪 ${r}`);
    hero.inventory.splice(idx, 1);
    return { log, spent: true, fled: it.flee, town: it.town };
  }
  // basic attack
  const raw = playerDamage(hero, 1);
  let dmg = Math.max(1, raw - Math.floor(enemy.defense * 0.5));
  const critChance = 0.05 + hero.stats.dex * 0.005;
  if (chance(critChance)) { const bonus = Math.floor(dmg * 0.6); dmg += bonus; enemy.hp -= dmg; log.push(`⚔️ CRITICAL! You strike ${enemy.name} for ${dmg}.`); log._float = { side: 'enemy', text: '-' + dmg, crit: true }; }
  else { enemy.hp -= dmg; log.push(`⚔️ You strike ${enemy.name} for ${dmg}.`); log._float = { side: 'enemy', text: '-' + dmg }; }
  return { log, spent: true };
}

function enemyAction(hero, enemy, diff) {
  const log = [];
  if (hasStatus(enemy, 'freeze')) { log.push(`🧊 ${enemy.name} is frozen solid and cannot act!`); return log; }
  let ability = null;
  for (const ab of enemy.abilities) { if (chance(ab.chance)) { ability = ab; break; } }
  const ward = statusValue(hero, 'ward');
  const evasive = statusValue(hero, 'evasive');
  const baseDodge = hero.stats.dex * 0.003 + evasive;

  if (ability && ability.dmg === 0 && ability.heal) {
    const h = Math.floor(enemy.maxHp * ability.heal); enemy.hp = Math.min(enemy.maxHp, enemy.hp + h);
    log.push(`${enemy.emoji} ${enemy.name} ${ability.msg} heals ${h} HP.`); return log;
  }
  const mult = ability ? ability.dmg : 1;
  const msg = ability ? ability.msg : 'attacks —';
  let raw = enemyDamageRoll(enemy, mult, diff);
  // defending doubles armor effectiveness
  const def = hero.defending ? defensePower(hero) : Math.floor(defensePower(hero) * 0.5);
  let dmg = Math.max(1, raw - def);
  dmg = Math.floor(dmg * (1 - ward));
  if (chance(baseDodge)) { log.push(`💨 You slip aside — ${enemy.name}'s blow finds nothing!`); return log; }
  hero.hp -= Math.max(1, dmg);
  log.push(`${enemy.emoji} ${enemy.name} ${msg} ${Math.max(1, dmg)} damage${hero.defending ? ' (braced)' : ''}.`);
  log._float = { side: 'hero', text: '-' + Math.max(1, dmg) };
  if (ability && ability.heal) { const h = Math.floor(Math.max(1, dmg) * ability.heal); enemy.hp = Math.min(enemy.maxHp, enemy.hp + h); log.push(`  ${enemy.name} drinks ${h} HP from the wound.`); }
  if (ability && ability.status) { addStatus(hero, ability.status); if (hasStatus(hero, ability.status.type)) log.push(`  You are afflicted with ${ability.status.type}!`); }
  return log;
}

function applyConsumable(hero, it, enemyInCombat) {
  let msg = '';
  if (it.cure) { const before = (hero.statuses || []).length; hero.statuses = (hero.statuses || []).filter((s) => s.type !== 'poison' && s.type !== 'burn'); msg += before > (hero.statuses || []).length ? 'Toxins purged. ' : 'Nothing to cure. '; }
  if (it.heal) { const h = Math.min(it.heal, hero.maxHp - hero.hp); hero.hp += h; if (h > 0) msg += `Restored ${h} HP. `; }
  if (it.mp) { const m = Math.min(it.mp, hero.maxMp - hero.mp); hero.mp += m; if (m > 0) msg += `Restored ${m} MP. `; }
  if (it.buff) { addStatus(hero, Object.assign({}, it.buff, { chance: 1 })); msg += `${it.buff.type} for ${it.buff.turns} turns. `; }
  if (it.perm) { hero.stats[it.perm] += 1; recalc(hero); msg += `${it.perm.toUpperCase()} permanently raised! `; }
  if (it.damage && enemyInCombat) { enemyInCombat.hp -= it.damage; msg += `Hurled for ${it.damage} damage! `; }
  if (it.flee) msg += 'You vanish in smoke. ';
  if (it.town) msg += 'A portal tears open. ';
  return msg || 'Used.';
}

function combatRewards(enemy, diff) {
  return {
    xp: Math.floor(enemy.xpReward * diff.xp),
    gold: Math.floor(enemy.goldReward * diff.gold),
    items: generateLoot(enemy.level, enemy.isBoss),
  };
}

function checkLevelUp(hero) { return hero.xp >= hero.xpToNext; }
function performLevelUp(hero) {
  const log = [];
  while (hero.xp >= hero.xpToNext) {
    hero.xp -= hero.xpToNext; hero.level += 1; hero.xpToNext = xpToNext(hero.level); hero.statPoints += 3;
    for (const sk of SKILLS[hero.heroClass]) {
      if (sk.lvl === hero.level && !hero.skills.find((s) => s.id === sk.id)) { hero.skills.push(Object.assign({}, sk)); log.push(`🌟 New skill: ${sk.name}!`); }
    }
    log.push(`⬆️ Level ${hero.level}! +3 stat points to spend.`);
  }
  recalc(hero); hero.hp = hero.maxHp; hero.mp = hero.maxMp;
  return log;
}

function equipItem(hero, id) {
  const idx = hero.inventory.findIndex((i) => i.id === id);
  if (idx === -1) return 'Item not found.';
  const it = hero.inventory[idx];
  if (!it.slot) return 'That cannot be equipped.';
  if (it.lvl > hero.level) return `Requires level ${it.lvl}.`;
  const cur = hero.equipment[it.slot];
  if (cur) hero.inventory.push(cur);
  hero.equipment[it.slot] = it; hero.inventory.splice(idx, 1); recalc(hero);
  return `Equipped ${it.name}.`;
}
function unequip(hero, slot) {
  const it = hero.equipment[slot]; if (!it) return 'Nothing there.';
  hero.equipment[slot] = null; hero.inventory.push(it); recalc(hero); return `Unequipped ${it.name}.`;
}
function useConsumableInv(hero, id) {
  const idx = hero.inventory.findIndex((i) => i.id === id); if (idx === -1) return 'Item not found.';
  const it = hero.inventory[idx]; if (!it.consumable) return 'Cannot use that.';
  if (it.damage && !it.heal && !it.mp) return 'Save bombs for combat.';
  const msg = applyConsumable(hero, it, null); hero.inventory.splice(idx, 1); return msg;
}
function rest(hero) {
  const h = Math.floor(hero.maxHp * 0.40), m = Math.floor(hero.maxMp * 0.50);
  const hadStatus = hero.statuses && hero.statuses.length;
  hero.hp = Math.min(hero.maxHp, hero.hp + h); hero.mp = Math.min(hero.maxMp, hero.mp + m);
  hero.statuses = [];
  return `You make camp by torchlight. Recovered ${h} HP and ${m} MP${hadStatus ? ', and tended your wounds' : ''}.`;
}
function restFull(hero) {
  hero.hp = hero.maxHp; hero.mp = hero.maxMp; hero.statuses = [];
  return `You rest at Gallows Rest. Fully restored — HP and MP at maximum.`;
}

/* ───────────────────────────── LOOT ─────────────────────────────── */
function createEnemy(theme, floorLevel, isBoss, diff) {
  const pool = ENEMIES[theme] || ENEMIES.undead;
  let t = isBoss ? (pool.find((e) => e.boss) || pool[pool.length - 1]) : pick(pool.filter((e) => !e.boss));
  const scale = 1 + (floorLevel - 1) * 0.25;
  const level = Math.max(1, Math.floor(floorLevel + (isBoss ? 2 : rnd(-1, 2))));
  const hpM = diff ? diff.enemyHp : 1;
  return {
    id: 'enemy_' + uid(), name: t.name, emoji: t.emoji, level, boss: !!t.boss, isBoss: !!t.boss,
    hp: Math.floor(t.hp * scale * hpM), maxHp: Math.floor(t.hp * scale * hpM),
    attack: Math.floor(t.atk * scale), defense: Math.floor(t.def * scale),
    xpReward: Math.floor(level * 15 * (t.xpM || 1)),
    goldReward: Math.floor((5 + Math.random() * 10) * level * (t.goldM || 1)),
    abilities: t.abilities, statuses: [],
  };
}

function generateLoot(level, isBoss) {
  const items = [];
  const cons = CONSUMABLES.filter((c) => c.lvl <= level + 2 && !c.perm);
  if (cons.length) items.push(cloneItem(pick(cons)));
  const equip = ALL_EQUIP.filter((i) => i.lvl <= level + 2);
  if (chance(isBoss ? 1 : 0.35) && equip.length) {
    const pool = isBoss ? equip.filter((i) => i.rarity !== 'common') : equip;
    items.push(enchant(cloneItem(pick(pool.length ? pool : equip)), level, isBoss));
  }
  if (isBoss) {
    if (equip.length) items.push(enchant(cloneItem(pick(equip)), level, true)); // bosses always roll a magic chance
    if (cons.length) items.push(cloneItem(pick(cons)));
    if (chance(0.4)) { const tomes = CONSUMABLES.filter((c) => c.perm); items.push(cloneItem(pick(tomes))); }
  }
  return items;
}

function generateShopItems(level) {
  const items = [];
  const equip = ALL_EQUIP.filter((i) => i.lvl <= level + 3);
  const cons = CONSUMABLES.filter((c) => c.lvl <= level + 3);
  for (let i = 0; i < rnd(4, 6); i++) if (equip.length) items.push(enchant(cloneItem(pick(equip)), level, false));
  for (let i = 0; i < rnd(3, 4); i++) if (cons.length) items.push(cloneItem(pick(cons)));
  return items;
}

/* ───────────────────────── DUNGEON GENERATOR ────────────────────── */
const DW = 48, DH = 34, MINR = 4, MAXR = 9, MINROOMS = 9, MAXROOMS = 15;

function overlap(a, b, pad = 2) {
  return !(a.x + a.w + pad <= b.x || b.x + b.w + pad <= a.x || a.y + a.h + pad <= b.y || b.y + b.h + pad <= a.y);
}
function genRooms() {
  const rooms = []; const target = rnd(MINROOMS, MAXROOMS); let tries = 0;
  while (rooms.length < target && tries < 600) {
    tries++;
    const w = rnd(MINR, MAXR), h = rnd(MINR, MAXR);
    const x = rnd(1, DW - w - 1), y = rnd(1, DH - h - 1);
    const r = { x, y, w, h, cx: Math.floor(x + w / 2), cy: Math.floor(y + h / 2), type: 'normal' };
    if (!rooms.some((o) => overlap(o, r))) rooms.push(r);
  }
  return rooms;
}
function carveRoom(t, r) { for (let y = r.y; y < r.y + r.h; y++) for (let x = r.x; x < r.x + r.w; x++) t[y][x] = 'floor'; }
function carveCorr(t, x1, y1, x2, y2) {
  let cx = x1, cy = y1; const set = () => { if (cy >= 0 && cy < DH && cx >= 0 && cx < DW && t[cy][cx] === 'wall') t[cy][cx] = 'floor'; };
  if (chance(0.5)) { while (cx !== x2) { set(); cx += cx < x2 ? 1 : -1; } while (cy !== y2) { set(); cy += cy < y2 ? 1 : -1; } }
  else { while (cy !== y2) { set(); cy += cy < y2 ? 1 : -1; } while (cx !== x2) { set(); cx += cx < x2 ? 1 : -1; } }
  set();
}
function placeDoors(t, rooms) {
  for (const r of rooms) {
    const border = [];
    for (let i = 0; i < r.w; i++) { border.push({ x: r.x + i, y: r.y - 1 }, { x: r.x + i, y: r.y + r.h }); }
    for (let i = 0; i < r.h; i++) { border.push({ x: r.x - 1, y: r.y + i }, { x: r.x + r.w, y: r.y + i }); }
    for (const p of border) {
      if (p.x > 0 && p.x < DW - 1 && p.y > 0 && p.y < DH - 1 && t[p.y][p.x] === 'floor') {
        const walls = [t[p.y - 1][p.x], t[p.y + 1][p.x], t[p.y][p.x - 1], t[p.y][p.x + 1]].filter((c) => c === 'wall').length;
        if (walls >= 2 && chance(0.35)) t[p.y][p.x] = 'door';
      }
    }
  }
}
function generateFloor(floorNum, world, diff) {
  const tiles = Array.from({ length: DH }, () => Array.from({ length: DW }, () => 'wall'));
  const explored = Array.from({ length: DH }, () => Array.from({ length: DW }, () => false));
  const rooms = genRooms();
  rooms.forEach((r) => carveRoom(tiles, r));
  rooms.sort((a, b) => a.cx + a.cy - b.cx - b.cy);
  for (let i = 0; i < rooms.length - 1; i++) carveCorr(tiles, rooms[i].cx, rooms[i].cy, rooms[i + 1].cx, rooms[i + 1].cy);
  for (let i = 0; i < Math.floor(rooms.length / 3); i++) { const a = rnd(0, rooms.length - 1), b = rnd(0, rooms.length - 1); if (a !== b) carveCorr(tiles, rooms[a].cx, rooms[a].cy, rooms[b].cx, rooms[b].cy); }
  placeDoors(tiles, rooms);

  rooms[0].type = 'entrance';
  const last = floorNum === world.floors;
  rooms[rooms.length - 1].type = last ? 'boss' : 'exit';
  const mids = rooms.slice(1, -1).sort(() => Math.random() - 0.5);
  if (mids[0]) mids[0].type = 'treasure';
  if (mids[1]) mids[1].type = 'treasure';
  if (mids[2]) mids[2].type = 'shop';
  if (mids[3]) mids[3].type = 'trap';
  if (mids[4]) mids[4].type = 'trap';

  const enemies = {}, items = {};
  const effLevel = world.minLevel + floorNum - 1;
  let stairsDown = null, stairsUp = null;
  if (floorNum > 1) { tiles[rooms[0].cy][rooms[0].cx] = 'stairs_up'; stairsUp = { x: rooms[0].cx, y: rooms[0].cy }; }
  else tiles[rooms[0].cy][rooms[0].cx] = 'entrance';
  if (!last) { const ex = rooms[rooms.length - 1]; tiles[ex.cy][ex.cx] = 'stairs_down'; stairsDown = { x: ex.cx, y: ex.cy }; }

  for (const r of rooms) {
    if (r.type === 'entrance' || r.type === 'shop') continue;
    if (r.type === 'boss') { enemies[`${r.cx},${r.cy + 1}`] = createEnemy(world.theme, effLevel, true, diff); continue; }
    const n = r.type === 'treasure' ? rnd(1, 2) : rnd(0, 2);
    for (let i = 0; i < n; i++) {
      const ex = rnd(r.x + 1, r.x + r.w - 2), ey = rnd(r.y + 1, r.y + r.h - 2), k = `${ex},${ey}`;
      if (!enemies[k] && tiles[ey][ex] === 'floor') enemies[k] = createEnemy(world.theme, effLevel, false, diff);
    }
  }
  for (const r of rooms) {
    if (r.type === 'treasure') {
      const tx = rnd(r.x + 1, r.x + r.w - 2), ty = rnd(r.y + 1, r.y + r.h - 2), k = `${tx},${ty}`;
      if (tiles[ty][tx] === 'floor') { tiles[ty][tx] = 'chest'; items[k] = generateLoot(effLevel, false); }
    }
    if (r.type === 'trap') for (let i = 0; i < rnd(2, 4); i++) { const tx = rnd(r.x + 1, r.x + r.w - 2), ty = rnd(r.y + 1, r.y + r.h - 2); if (tiles[ty][tx] === 'floor') tiles[ty][tx] = 'trap'; }
    if (r.type === 'shop') tiles[r.cy][r.cx] = 'shop_tile';
  }
  for (let i = 0; i < rnd(2, 5); i++) {
    const rx = rnd(1, DW - 2), ry = rnd(1, DH - 2), k = `${rx},${ry}`;
    if (tiles[ry][rx] === 'floor' && !enemies[k] && !items[k]) {
      const cons = CONSUMABLES.filter((c) => c.lvl <= effLevel + 2 && !c.perm);
      if (cons.length) items[k] = [cloneItem(pick(cons))];
    }
  }
  const start = { x: rooms[0].cx + (stairsUp ? 1 : 0), y: rooms[0].cy + (stairsUp ? 0 : 1) };
  if (tiles[start.y][start.x] !== 'floor') {
    outer: for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
      const ty = rooms[0].cy + dy, tx = rooms[0].cx + dx;
      if (ty >= 0 && ty < DH && tx >= 0 && tx < DW && tiles[ty][tx] === 'floor') { start.x = tx; start.y = ty; break outer; }
    }
  }
  return { w: DW, h: DH, tiles, explored, enemies, items, rooms, start, stairsDown, stairsUp, depth: floorNum };
}
function reveal(floor, px, py, radius) {
  radius = radius || 5;
  for (let dy = -radius; dy <= radius; dy++) for (let dx = -radius; dx <= radius; dx++) {
    const x = px + dx, y = py + dy;
    if (x >= 0 && x < floor.w && y >= 0 && y < floor.h && Math.sqrt(dx * dx + dy * dy) <= radius) floor.explored[y][x] = true;
  }
}
const isWalkable = (t) => t !== 'wall';

/* ───────────────────────── MISC RENDER HELPERS ──────────────────── */
const TILE = { wall: '', floor: '', door: '🚪', stairs_down: '🔽', stairs_up: '🔼', chest: '🎁', trap: '', shop_tile: '🛒', entrance: '🚪' };
function roman(n) { const m = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']; return m[n] || ('' + n); }
function pct(c, m) { return Math.max(0, Math.min(100, Math.round((c / (m || 1)) * 100))); }
function strengthBits(it) {
  const m = [];
  if (it.dmg) m.push('⚔️' + it.dmg); if (it.def) m.push('🛡️' + it.def);
  if (it.heal) m.push('❤️' + (it.heal > 9000 ? 'full' : it.heal)); if (it.mp) m.push('💧' + (it.mp > 9000 ? 'full' : it.mp));
  if (it.damage) m.push('💥' + it.damage);
  if (it.bonus) for (const k in it.bonus) if (it.bonus[k]) m.push('+' + it.bonus[k] + ' ' + k.toUpperCase());
  return m;
}


/* ───────────────────────────── STYLES ───────────────────────────── */
const CSS = `
.cos-root{--accent:#e8a13a;position:fixed;inset:0;overflow:hidden;background:
  radial-gradient(120% 90% at 50% -10%, #1a1422 0%, #0e0c12 45%, #08070b 100%);
  color:#b6ab98;font-family:'Spectral','Iowan Old Style',Georgia,serif;}
.cos-root *{box-sizing:border-box;}
.cos-scroll{position:absolute;inset:0;overflow-y:auto;display:flex;flex-direction:column;align-items:center;}
.cos-shake{animation:cosShake .28s;}
@keyframes cosShake{0%,100%{transform:translate(0,0)}20%{transform:translate(-6px,3px)}40%{transform:translate(5px,-4px)}60%{transform:translate(-4px,-2px)}80%{transform:translate(4px,3px)}}
.cos-btn{font-family:'Cinzel','Trajan Pro',Georgia,serif;font-weight:600;letter-spacing:.04em;color:#e9dcc0;cursor:pointer;
  background:linear-gradient(#221c18,#15110e);border:1px solid #5d4a2c;border-radius:4px;padding:.6rem 1.1rem;transition:.15s;}
.cos-btn:hover{border-color:#c9a567;color:#fff;box-shadow:0 0 16px -3px var(--accent);transform:translateY(-1px);}
.cos-btn:active{transform:translateY(1px);}
.cos-btn:disabled{opacity:.4;cursor:not-allowed;filter:grayscale(.5);}
.cos-btn.pri{background:linear-gradient(#5a4119,#3a2a10);border-color:#c9a567;color:#fff;}
.cos-btn.dng{border-color:#5c2422;color:#d99;}
.cos-btn.dng:hover{border-color:#a3322b;background:linear-gradient(#3a1b18,#1f0f0d);box-shadow:0 0 14px -3px #a3322b;}
.cos-btn.sm{padding:.35rem .7rem;font-size:.8rem;}
.cos-btn.xs{padding:.18rem .5rem;font-size:.72rem;}
.cos-title{font-family:'Cinzel Decorative','Cinzel',Georgia,serif;font-weight:900;color:#e9dcc0;text-align:center;line-height:.95;
  text-shadow:0 0 28px rgba(232,161,58,.30),0 3px 0 #000;}
.cos-parch{background:radial-gradient(140% 120% at 20% 0%,#f3e9d2,#e9dcc0 40%,#d8c7a3);color:#2c2418;border:1px solid #b9a374;border-radius:5px;
  box-shadow:0 18px 50px -12px rgba(0,0,0,.9),inset 0 0 70px rgba(120,92,46,.28);position:relative;}
.cos-flicker{animation:cosFlicker 4s infinite;}
@keyframes cosFlicker{0%,100%{opacity:.92;filter:drop-shadow(0 0 18px rgba(232,161,58,.5))}45%{opacity:.7}55%{opacity:1}70%{opacity:.8}}
.cos-bar{position:relative;height:18px;border-radius:3px;margin:.3rem 0;overflow:hidden;background:rgba(0,0,0,.5);border:1px solid rgba(0,0,0,.6);}
.cos-bar > i{position:absolute;inset:0;border-radius:2px;transition:width .35s ease;display:block;}
.cos-bar > span{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:ui-monospace,monospace;font-size:.68rem;color:#fff;text-shadow:0 1px 2px #000;}
.cos-cell{display:flex;align-items:center;justify-content:center;line-height:1;transition:opacity .12s;position:relative;}
.cos-grid{display:grid;width:100%;height:100%;background:#05040a;}
.cos-vig{position:absolute;inset:0;pointer-events:none;background:radial-gradient(68% 68% at 50% 50%,transparent 45%,rgba(0,0,0,.32) 82%,rgba(0,0,0,.66) 100%);}
.cos-float{position:absolute;font-family:'Cinzel',serif;font-weight:700;font-size:1.5rem;pointer-events:none;animation:cosFloat .9s ease-out forwards;text-shadow:0 2px 6px #000;z-index:6;}
.cos-float.crit{font-size:2.1rem;}
@keyframes cosFloat{0%{transform:transl(0) scale(.7);opacity:0}18%{opacity:1;transform:translateY(-8px) scale(1.1)}100%{transform:translateY(-54px) scale(1);opacity:0}}
.cos-pill{display:inline-flex;align-items:center;gap:.3rem;font-size:.82rem;background:rgba(0,0,0,.4);border:1px solid var(--rc,#888);border-left:3px solid var(--rc,#888);border-radius:3px;padding:.2rem .5rem;color:#e9dcc0;}
.cos-card{background:linear-gradient(150deg,rgba(36,31,45,.92),rgba(14,12,18,.95));border:1px solid #5d4a2c;border-radius:5px;}
.cos-row{display:flex;align-items:center;gap:.5rem;background:rgba(255,255,255,.22);border-left:3px solid var(--rc,#888);border-radius:3px;padding:.28rem .55rem;color:#33260f;}
.cos-tt{position:fixed;z-index:50;max-width:300px;pointer-events:none;background:linear-gradient(#14101c,#0b0810);border:1px solid #9c7b46;border-radius:6px;padding:.55rem .7rem;box-shadow:0 14px 40px rgba(0,0,0,.8);color:#b6ab98;line-height:1.4;}
.cos-tt .nm{font-family:'Cinzel',serif;font-weight:600;font-size:1rem;}
.cos-tt .sub{font-family:ui-monospace,monospace;font-size:.7rem;color:#6f6657;margin:.05rem 0 .3rem;}
.cos-tt .st{font-family:ui-monospace,monospace;font-size:.78rem;color:#e9dcc0;}
.cos-tt .af{font-size:.78rem;color:#8fd0ff;font-style:italic;margin-top:.2rem;}
.cos-tt .ds{font-size:.8rem;font-style:italic;margin-top:.3rem;border-top:1px solid rgba(156,123,70,.3);padding-top:.25rem;}
.cos-tt .ft{font-family:ui-monospace,monospace;font-size:.7rem;color:#e3b85c;margin-top:.3rem;}
.cos-chip{font-family:ui-monospace,monospace;font-size:.66rem;padding:.1rem .4rem;border-radius:9px;background:rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.18);}
.cos-en{filter:drop-shadow(0 6px 16px rgba(0,0,0,.8));animation:cosBreath 2.6s ease-in-out infinite;}
@keyframes cosBreath{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-5px) scale(1.04)}}
.cos-link{color:#c9a567;cursor:pointer;text-decoration:underline;}
.cos-scroll::-webkit-scrollbar{width:9px}.cos-scroll::-webkit-scrollbar-thumb{background:#5d4a2c;border-radius:5px}
`;

const SAVE = {}; // in-session save store (no localStorage in this sandbox)
const clone = (o) => JSON.parse(JSON.stringify(o));
const RC = { Normal: '#cbd5e1', Rare: '#6f9dff', Epic: '#c061ff' };

function Bar({ cur, max, kind }) {
  const colors = { hp: ['#e0584f', '#b23b34'], mp: ['#5f93d6', '#3f6fae'], xp: ['#e3b85c', '#b58b3e'] };
  const [a, b] = colors[kind] || ['#888', '#555'];
  return (
    <div className="cos-bar" style={{ height: kind === 'xp' ? 12 : 18 }}>
      <i style={{ width: pct(cur, max) + '%', background: `linear-gradient(${a},${b})` }} />
      <span style={{ fontSize: kind === 'xp' ? '.6rem' : '.68rem' }}>{Math.max(0, Math.ceil(cur))} / {max}</span>
    </div>
  );
}

function Chips({ list }) {
  if (!list || !list.length) return null;
  const col = { poison: '#9bd07f', burn: '#f0a060', freeze: '#8fc4f0', weaken: '#c79bd0', stun: '#e8d77a', might: '#f08a8a', ward: '#7ad0e8', evasive: '#7ae8d0', regen: '#8af08a' };
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, justifyContent: 'center', marginTop: 4 }}>
      {list.map((s, i) => <span key={i} className="cos-chip" style={{ color: col[s.type] || '#b6ab98', borderColor: (col[s.type] || '#888') + '66' }}>{s.type}{s.turns ? ' ' + s.turns : ''}</span>)}
    </div>
  );
}

/* tooltip body for an item */
function itemTipNode(it) {
  const rar = rarityName(it), col = rarityColor(it);
  const type = it.consumable ? 'Consumable' : (it.slot ? it.slot[0].toUpperCase() + it.slot.slice(1) : 'Item');
  const bits = strengthBits(it);
  return (
    <>
      <div className="nm" style={{ color: col }}>{it.emoji} {it.name}</div>
      <div className="sub"><span style={{ color: col }}>{rar}{it.magic ? ' ✦ Magic' : ''}</span> · {type} · Lv.{it.lvl || 1}</div>
      {bits.length > 0 && <div className="st">{bits.join('   ')}</div>}
      {it.affixes && it.affixes.length > 0 && <div className="af">✦ {it.affixes.join('  ·  ')}</div>}
      {it.desc && <div className="ds">{it.desc}</div>}
      <div className="ft">Value {it.value || 0} 🪙</div>
    </>
  );
}

export default function App() {
  const G = useRef(null);
  if (!G.current) {
    G.current = {
      screen: 'menu', hero: null, difficulty: 'normal', world: null, floorNum: 0, floors: {},
      playerPos: { x: 0, y: 0 }, combat: null, completed: [], kills: 0, deepest: 0, bosses: 0, goldEarned: 0,
      dead: false, log: [], creation: { name: '', cls: 'warrior', diff: 'normal' }, shop: [], fx: [], shake: false,
      _return: 'town', _levelMsgs: [], _afterLevel: 'exploring', _enemyKey: null,
    };
  }
  const g = G.current;
  const [, setTick] = useState(0);
  const rr = useCallback(() => setTick((t) => t + 1), []);
  const [tip, setTip] = useState(null);

  // tooltip hover handlers
  const tipH = (it) => ({
    onMouseEnter: (e) => setTip({ it, x: e.clientX, y: e.clientY }),
    onMouseMove: (e) => setTip((p) => (p ? { it, x: e.clientX, y: e.clientY } : p)),
    onMouseLeave: () => setTip(null),
  });

  const log = (...lines) => { for (const l of lines) g.log.push(l); if (g.log.length > 60) g.log = g.log.slice(-60); };
  const autosave = () => { if (g.hero && !g.dead) SAVE.auto = makePayload(); };
  const makePayload = () => ({ v: 1, ts: Date.now(), hero: clone(g.hero), difficulty: g.difficulty, world: g.world, floorNum: g.floorNum, floors: clone(g.floors), playerPos: { ...g.playerPos }, completed: [...g.completed], kills: g.kills, deepest: g.deepest, bosses: g.bosses, goldEarned: g.goldEarned });
  const loadPayload = (p) => { Object.assign(g, { hero: clone(p.hero), difficulty: p.difficulty || 'normal', world: p.world, floorNum: p.floorNum || 0, floors: clone(p.floors || {}), playerPos: p.playerPos || { x: 0, y: 0 }, completed: p.completed || [], kills: p.kills || 0, deepest: p.deepest || 0, bosses: p.bosses || 0, goldEarned: p.goldEarned || 0, dead: false, combat: null }); if (g.hero) { g.hero.statuses = g.hero.statuses || []; recalc(g.hero); } };

  const doShake = () => { g.shake = true; rr(); setTimeout(() => { g.shake = false; rr(); }, 280); };
  const addFloat = (side, text, crit) => { const id = 'f' + Math.random().toString(36).slice(2); g.fx.push({ id, side, text, crit }); rr(); setTimeout(() => { g.fx = g.fx.filter((f) => f.id !== id); rr(); }, 900); };

  const curFloor = () => g.floors[g.floorNum];
  const diffObj = () => DIFFICULTIES[g.difficulty];

  // ---- run lifecycle ----
  const resetRun = () => Object.assign(g, { world: null, floorNum: 0, floors: {}, combat: null, completed: [], kills: 0, deepest: 0, bosses: 0, goldEarned: 0, log: [], dead: false, shop: [], fx: [] });
  const create = () => {
    const name = (g.creation.name || '').trim() || 'Nameless one';
    resetRun();
    g.hero = createHero(name, g.creation.cls); g.hero.statuses = [];
    g.difficulty = g.creation.diff; g.screen = 'town';
    log(`${name} the ${CLASSES[g.creation.cls].name} arrives at Gallows Rest.`);
    autosave(); rr();
  };
  const enterWorld = (w) => {
    g.world = w; g.floorNum = 1; g.floors = {};
    const f = generateFloor(1, w, diffObj());
    g.floors[1] = f; g.playerPos = { ...f.start }; g.deepest = Math.max(g.deepest, 1);
    reveal(f, f.start.x, f.start.y);
    g.log = [`═══ ${w.name} ═══`, w.desc, 'WASD / arrows to move. R to rest.'];
    g.screen = 'exploring'; autosave(); rr();
  };
  const returnTown = () => { Object.assign(g, { world: null, floorNum: 0, floors: {}, combat: null, screen: 'town' }); autosave(); rr(); };

  // ---- movement ----
  const descend = () => {
    const next = g.floorNum + 1;
    if (!g.floors[next]) g.floors[next] = generateFloor(next, g.world, diffObj());
    const nf = g.floors[next]; g.floorNum = next; g.playerPos = { ...nf.start };
    g.deepest = Math.max(g.deepest, next); reveal(nf, nf.start.x, nf.start.y);
    log(`🔻 You descend to depth ${roman(next)}.`); autosave(); rr();
  };
  const ascend = () => {
    const prev = g.floorNum - 1;
    if (prev >= 1 && g.floors[prev]) { g.floorNum = prev; const pf = g.floors[prev]; g.playerPos = { ...(pf.stairsDown || pf.start) }; log(`🔼 You climb to depth ${roman(prev)}.`); rr(); }
  };
  const death = () => { g.dead = true; if (diffObj().perma && SAVE.auto) delete SAVE.auto; g.screen = 'gameover'; rr(); };
  const move = (dx, dy) => {
    if (g.screen !== 'exploring') return;
    const f = curFloor(), p = g.playerPos; const nx = p.x + dx, ny = p.y + dy;
    if (nx < 0 || nx >= f.w || ny < 0 || ny >= f.h) return;
    const t = f.tiles[ny][nx]; if (!isWalkable(t)) return;
    const ek = nx + ',' + ny;
    if (f.enemies[ek]) return startCombat(f.enemies[ek], ek);
    g.hero.defending = false; g.playerPos = { x: nx, y: ny }; reveal(f, nx, ny);
    if (t === 'trap') {
      const dmg = Math.max(3, Math.floor((5 + g.hero.level * 2 - g.hero.stats.dex * 0.3) * diffObj().trap));
      g.hero.hp -= dmg; f.tiles[ny][nx] = 'floor'; log(`⚠️ A blade-trap! You take ${dmg} damage.`);
      if (g.hero.hp <= 0) return death();
    } else if (t === 'chest') {
      const loot = f.items[ek]; if (loot) { loot.forEach((i) => g.hero.inventory.push(i)); log(`🎁 A chest! You take ${loot.map((i) => i.name).join(', ')}.`); delete f.items[ek]; } f.tiles[ny][nx] = 'floor';
    } else if (f.items[ek]) {
      const loot = f.items[ek]; loot.forEach((i) => g.hero.inventory.push(i)); log(`✨ Found ${loot.map((i) => i.name).join(', ')}.`); delete f.items[ek];
    } else if (t === 'stairs_down') { return descend(); }
    else if (t === 'stairs_up') { return ascend(); }
    else if (t === 'shop_tile') { g.shop = generateShopItems(g.hero.level); g.screen = 'shop'; rr(); return; }
    rr();
  };

  // ---- combat ----
  const startCombat = (enemy, key) => {
    const f = curFloor(); g._enemyKey = key;
    g.combat = { enemy: clone(enemy), log: [`💀 A ${enemy.name} (Lv.${enemy.level}) bars the way!${enemy.boss ? ' 👑 A BOSS!' : ''}`], rewards: null, fled: false, sel: null, turn: 1 };
    g.combat.enemy.statuses = g.combat.enemy.statuses || []; g.hero.statuses = g.hero.statuses || [];
    delete f.enemies[key]; g.screen = 'combat'; rr();
  };
  const enemyDefeated = () => { g.combat.rewards = combatRewards(g.combat.enemy, diffObj()); rr(); };
  const resolveEnemyTurn = () => {
    const h = g.hero, e = g.combat.enemy;
    g.combat.log.push(...tickStatuses(e, false, null));
    if (e.hp <= 0) return enemyDefeated();
    const elog = enemyAction(h, e, diffObj());
    if (elog._float) { addFloat(elog._float.side, elog._float.text, elog._float.crit); doShake(); }
    g.combat.log.push(...elog);
    g.combat.log.push(...tickStatuses(h, true, diffObj()));
    g.combat.turn++;
    if (h.hp <= 0) { rr(); return death(); }
    g.combat.sel = null; trimLog(); rr();
  };
  const trimLog = () => { if (g.combat && g.combat.log.length > 40) g.combat.log = g.combat.log.slice(-40); };
  const afterPlayer = (r) => {
    const e = g.combat.enemy;
    if (r.log._float) { addFloat(r.log._float.side, r.log._float.text, r.log._float.crit); doShake(); }
    g.combat.log.push(...r.log); trimLog();
    if (r.town) { g.combat = null; log('📜 A town portal whisks you to safety.'); return returnTown(); }
    if (r.fled) { g.combat.fled = true; rr(); return; }
    if (e.hp <= 0) return enemyDefeated();
    if (!r.spent) { rr(); return; }
    resolveEnemyTurn();
  };
  const combatAttack = () => afterPlayer(playerAction(g.hero, g.combat.enemy, { kind: 'attack' }, diffObj()));
  const combatSkill = (sk) => { g.combat.sel = null; afterPlayer(playerAction(g.hero, g.combat.enemy, { kind: 'skill', skill: sk }, diffObj())); };
  const combatItem = (it) => { g.combat.sel = null; afterPlayer(playerAction(g.hero, g.combat.enemy, { kind: 'item', item: it }, diffObj())); };
  const combatDefend = () => { g.hero.defending = true; g.combat.log.push('🛡️ You set your guard.'); resolveEnemyTurn(); g.hero.defending = false; };
  const combatFlee = () => {
    const e = g.combat.enemy, h = g.hero;
    if (e.boss) { g.combat.log.push('There is no fleeing this.'); rr(); return; }
    const fc = clamp(0.3 + h.stats.dex * 0.02 - e.level * 0.02, 0.1, 0.8);
    if (chance(fc)) { g.combat.fled = true; g.combat.log.push('🏃 You break away and escape!'); rr(); return; }
    g.combat.log.push('🏃 You fail to escape!'); resolveEnemyTurn();
  };
  const collect = () => {
    const c = g.combat, h = g.hero, e = c.enemy;
    if (c.rewards) { h.xp += c.rewards.xp; h.gold += c.rewards.gold; g.goldEarned += c.rewards.gold; c.rewards.items.forEach((i) => h.inventory.push(i)); g.kills++; log(`Victory! +${c.rewards.xp} XP, +${c.rewards.gold} 🪙.`); }
    const wasBoss = e.boss;
    if (wasBoss) { g.bosses++; if (!g.completed.includes(g.world.id)) g.completed.push(g.world.id); }
    h.statuses = [];
    if (checkLevelUp(h)) { g._levelMsgs = performLevelUp(h); g._afterLevel = wasBoss ? 'victory' : 'exploring'; g.combat = null; g.screen = 'levelup'; autosave(); rr(); return; }
    g.combat = null; g.screen = wasBoss ? 'victory' : 'exploring'; autosave(); rr();
  };
  const fledOut = () => { g.combat = null; g.screen = 'exploring'; rr(); };

  // ---- inventory / character ----
  const equip = (id) => { log(equipItem(g.hero, id)); rr(); };
  const unequipSlot = (slot) => { log(unequip(g.hero, slot)); rr(); };
  const useInv = (id) => { log('🧪 ' + useConsumableInv(g.hero, id)); rr(); };
  const dropItem = (id) => { g.hero.inventory = g.hero.inventory.filter((i) => i.id !== id); rr(); };
  const allocate = (stat) => { if (g.hero.statPoints > 0) { g.hero.stats[stat]++; g.hero.statPoints--; recalc(g.hero); rr(); } };
  const buy = (id) => { const it = g.shop.find((i) => i.id === id); if (it && g.hero.gold >= it.value) { g.hero.gold -= it.value; g.hero.inventory.push(it); g.shop = g.shop.filter((i) => i.id !== id); rr(); } };
  const sell = (id) => { const it = g.hero.inventory.find((i) => i.id === id); if (it) { g.hero.gold += Math.floor(it.value * 0.4); g.hero.inventory = g.hero.inventory.filter((i) => i.id !== id); rr(); } };

  const restCamp = () => { log('🏕️ ' + rest(g.hero)); rr(); };
  const restTown = () => { log('🏕️ ' + restFull(g.hero)); rr(); };

  const openChar = () => { g._return = g.screen; g.screen = 'character'; rr(); };
  const closeChar = () => { g.screen = g._return || 'town'; rr(); };

  // ---- keyboard ----
  useEffect(() => {
    const onKey = (e) => {
      const s = g.screen;
      if (s === 'exploring') {
        const k = e.key.toLowerCase();
        if (['arrowup', 'w'].includes(k)) { e.preventDefault(); move(0, -1); }
        else if (['arrowdown', 's'].includes(k)) { e.preventDefault(); move(0, 1); }
        else if (['arrowleft', 'a'].includes(k)) { e.preventDefault(); move(-1, 0); }
        else if (['arrowright', 'd'].includes(k)) { e.preventDefault(); move(1, 0); }
        else if (k === 'i') openChar();
        else if (k === 'r') restCamp();
      } else if (s === 'combat' && g.combat && !g.combat.rewards && !g.combat.fled) {
        if (g.combat.sel) { if (e.key === 'Escape') { g.combat.sel = null; rr(); } return; }
        if (e.key === '1') combatAttack();
        else if (e.key === '2') { g.combat.sel = 'skill'; rr(); }
        else if (e.key === '3') { g.combat.sel = 'item'; rr(); }
        else if (e.key === '4') combatDefend();
        else if (e.key === '5' && !g.combat.enemy.boss) combatFlee();
      } else if (s === 'character') { if (e.key === 'Escape' || e.key.toLowerCase() === 'i') closeChar(); }
      else if (s === 'shop') { if (e.key === 'Escape') { g.screen = 'exploring'; rr(); } }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  /* ============================ SCREENS ============================ */
  const Pill = (it, extra) => <span key={it.id} className="cos-pill" style={{ '--rc': rarityColor(it) }} {...tipH(it)}>{it.emoji} {it.name}{extra}</span>;

  function ScreenMenu() {
    const canContinue = !!SAVE.auto;
    return (
      <div className="cos-scroll" style={{ justifyContent: 'center' }}>
        <div className="cos-flicker" style={{ fontSize: '3.4rem' }}>☠</div>
        <h1 className="cos-title" style={{ fontSize: 'clamp(2.4rem,8vw,5rem)' }}>Crypt<span style={{ fontSize: '.4em', color: '#c9a567', fontStyle: 'italic' }}> of </span>Shadows</h1>
        <p style={{ fontStyle: 'italic', color: '#6f6657', marginTop: '.8rem', maxWidth: '34ch', textAlign: 'center' }}>A gothic descent. Five heroes, nine worlds, and a dark that learns your name.</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '.7rem', marginTop: '2rem', width: 'min(92vw,360px)' }}>
          <button className="cos-btn pri" onClick={() => { g.creation = { name: '', cls: 'warrior', diff: 'normal' }; g.screen = 'creation'; rr(); }}>⚔️ New Descent</button>
          <button className="cos-btn" disabled={!canContinue} onClick={() => { if (SAVE.auto) { loadPayload(SAVE.auto); g.screen = g.world ? 'exploring' : 'town'; rr(); } }}>↺ Continue</button>
        </div>
        <p style={{ marginTop: '1.6rem', color: '#6f6657', fontSize: '.8rem', fontStyle: 'italic' }}>WASD / arrows move · I inventory · R rest</p>
      </div>
    );
  }

  function ScreenCreation() {
    const c = g.creation; const cls = CLASSES[c.cls];
    return (
      <div className="cos-scroll" style={{ paddingTop: '4vh' }}>
        <div className="cos-parch" style={{ width: 'min(96vw,640px)', padding: '1.4rem' }}>
          <h2 style={{ fontFamily: "'Cinzel Decorative',serif", color: '#3a2c14', textAlign: 'center', fontSize: '1.7rem', marginBottom: '1rem' }}>Forge Your Hero</h2>
          <label style={{ display: 'block', fontFamily: "'Cinzel',serif", fontSize: '.8rem', textTransform: 'uppercase', letterSpacing: '.06em', color: '#4a3818' }}>Name</label>
          <input defaultValue={c.name} onChange={(e) => { c.name = e.target.value; }} placeholder="Nameless one"
            style={{ width: '100%', fontFamily: "'Spectral',serif", fontSize: '1.1rem', color: '#2c2418', background: 'rgba(255,255,255,.4)', border: '1px solid #b09766', borderRadius: 3, padding: '.55rem .8rem', margin: '.3rem 0 1rem' }} />
          <div style={{ fontFamily: "'Cinzel',serif", fontWeight: 700, color: '#4a3818', fontSize: '.8rem', letterSpacing: '.12em', textTransform: 'uppercase', borderBottom: '1px solid rgba(120,92,46,.35)', paddingBottom: '.3rem', margin: '.4rem 0 .6rem' }}>Class</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(86px,1fr))', gap: '.5rem' }}>
            {CLASS_LIST.map((k) => { const cc = CLASSES[k]; const sel = c.cls === k; return (
              <div key={k} onClick={() => { c.cls = k; rr(); }} style={{ cursor: 'pointer', textAlign: 'center', padding: '.6rem .3rem', borderRadius: 4, color: '#3a2c14', background: sel ? 'rgba(255,255,255,.55)' : 'rgba(255,255,255,.22)', border: '1px solid ' + (sel ? cc.color : 'rgba(120,92,46,.4)'), boxShadow: sel ? `0 0 0 1px ${cc.color}` : 'none' }}>
                <div style={{ fontSize: '1.6rem' }}>{cc.emoji}</div><div style={{ fontWeight: 600, fontSize: '.8rem' }}>{cc.name}</div>
              </div>); })}
          </div>
          <div style={{ marginTop: '.8rem', padding: '.8rem 1rem', borderRadius: 4, background: 'rgba(120,92,46,.12)', borderLeft: '3px solid ' + cls.color }}>
            <div style={{ fontFamily: "'Cinzel',serif", fontWeight: 700, fontSize: '1.1rem', color: '#33260f' }}>{cls.emoji} {cls.name}</div>
            <div style={{ fontStyle: 'italic', color: '#2c2418', margin: '.3rem 0 .5rem', fontSize: '.92rem' }}>{cls.desc}</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.4rem' }}>
              {Object.entries(cls.base).map(([k, v]) => <span key={k} style={{ fontFamily: 'ui-monospace,monospace', fontSize: '.74rem', background: 'rgba(255,255,255,.35)', padding: '.18rem .5rem', borderRadius: 3, color: '#4a3818' }}>{k.toUpperCase()} <b>{v}</b></span>)}
            </div>
          </div>
          <div style={{ fontFamily: "'Cinzel',serif", fontWeight: 700, color: '#4a3818', fontSize: '.8rem', letterSpacing: '.12em', textTransform: 'uppercase', borderBottom: '1px solid rgba(120,92,46,.35)', paddingBottom: '.3rem', margin: '1rem 0 .6rem' }}>Difficulty</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: '.5rem' }}>
            {Object.entries(DIFFICULTIES).map(([k, d]) => { const sel = c.diff === k; return (
              <div key={k} onClick={() => { c.diff = k; rr(); }} style={{ cursor: 'pointer', padding: '.55rem .7rem', borderRadius: 4, color: '#3a2c14', background: sel ? 'rgba(255,255,255,.55)' : 'rgba(255,255,255,.22)', border: '1px solid ' + (sel ? '#7a5e2c' : 'rgba(120,92,46,.4)') }}>
                <div style={{ fontFamily: "'Cinzel',serif", fontSize: '.92rem' }}>{d.emoji} {d.name}</div>
                <div style={{ fontSize: '.74rem', color: '#6a5b41', fontStyle: 'italic', marginTop: '.15rem' }}>{d.desc}</div>
              </div>); })}
          </div>
          <div style={{ display: 'flex', gap: '.7rem', marginTop: '1.2rem' }}>
            <button className="cos-btn" style={{ flex: 1 }} onClick={() => { g.screen = 'menu'; rr(); }}>← Back</button>
            <button className="cos-btn pri" style={{ flex: 2 }} onClick={create}>Begin the Descent →</button>
          </div>
        </div>
      </div>
    );
  }

  function HeroStrip() {
    const h = g.hero;
    return <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: '.8rem', color: '#e3b85c' }}>❤️{Math.ceil(h.hp)}/{h.maxHp} 💧{Math.ceil(h.mp)}/{h.maxMp} 🪙{h.gold}</span>;
  }

  function ScreenTown() {
    const h = g.hero;
    return (
      <div className="cos-scroll" style={{ alignItems: 'stretch' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', padding: '.55rem 1rem', background: 'linear-gradient(#140f1a,#0b0810)', borderBottom: '1px solid #5d4a2c', flexWrap: 'wrap' }}>
          <div style={{ fontFamily: "'Cinzel',serif", color: '#e9dcc0' }}><span style={{ fontSize: '1.3rem' }}>🏚️</span> <b>Gallows Rest</b> <span style={{ color: '#6f6657', fontStyle: 'italic', fontFamily: "'Spectral',serif", fontSize: '.82rem' }}>— the last town above the dark</span></div>
          <div style={{ display: 'flex', gap: '.5rem', alignItems: 'center' }}><HeroStrip /><button className="cos-btn sm" onClick={openChar}>🎒 Character</button></div>
        </header>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(240px,300px)', gap: '1.2rem', width: '100%', maxWidth: 1100, margin: '0 auto', padding: '1.4rem' }}>
          <div>
            <h3 style={{ fontFamily: "'Cinzel',serif", color: '#e9dcc0', fontSize: '1.2rem', marginBottom: '.8rem' }}>Choose your descent</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(250px,1fr))', gap: '.7rem' }}>
              {WORLDS.map((w) => { const locked = h.level < w.minLevel; const done = g.completed.includes(w.id); return (
                <div key={w.id} className="cos-card" onClick={() => { if (!locked) enterWorld(w); }} style={{ '--accent': w.accent, cursor: locked ? 'not-allowed' : 'pointer', opacity: locked ? 0.5 : 1, display: 'flex', gap: '.7rem', padding: '.8rem .9rem', borderLeft: '3px solid ' + (done ? '#5a9e54' : w.accent) }}>
                  <span style={{ fontSize: '2rem', filter: `drop-shadow(0 0 10px ${w.accent})` }}>{w.emoji}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontFamily: "'Cinzel',serif", fontWeight: 600, color: '#fff' }}>{w.name} {done && <span style={{ color: '#5a9e54', fontSize: '.72rem' }}>✓ cleared</span>}</div>
                    <div style={{ fontStyle: 'italic', color: '#b6ab98', fontSize: '.84rem', margin: '.2rem 0 .35rem' }}>{w.desc}</div>
                    <div style={{ fontFamily: 'ui-monospace,monospace', fontSize: '.72rem', color: '#6f6657' }}>{roman(w.floors)} floors · {locked ? <span style={{ color: '#d65149' }}>requires Lv.{w.minLevel}</span> : `Lv.${w.minLevel}+`}</div>
                  </div>
                </div>); })}
            </div>
          </div>
          <aside>
            <div className="cos-card" style={{ padding: '1rem' }}>
              <h3 style={{ fontFamily: "'Cinzel',serif", color: '#e9dcc0', fontSize: '1.1rem' }}>{CLASSES[h.heroClass].emoji} {h.name}</h3>
              <div style={{ color: '#6f6657', fontSize: '.8rem', fontStyle: 'italic', margin: '.2rem 0 .6rem' }}>{CLASSES[h.heroClass].name} · Level {h.level}</div>
              <Bar cur={h.hp} max={h.maxHp} kind="hp" /><Bar cur={h.mp} max={h.maxMp} kind="mp" /><Bar cur={h.xp} max={h.xpToNext} kind="xp" />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '.45rem', marginTop: '.9rem' }}>
                <button className="cos-btn pri" onClick={restTown}>🏕️ Rest (full heal)</button>
                <button className="cos-btn" onClick={openChar}>🎒 Character & Inventory</button>
                <button className="cos-btn" onClick={() => { autosave(); SAVE['1'] = makePayload(); log('💾 Saved.'); rr(); }}>💾 Save game</button>
                <button className="cos-btn dng" onClick={() => { g.screen = 'menu'; rr(); }}>↩ Main menu</button>
              </div>
            </div>
            <div className="cos-card" style={{ padding: '1rem', marginTop: '.7rem', fontFamily: 'ui-monospace,monospace', fontSize: '.78rem', color: '#b6ab98' }}>
              <div>Kills: <b style={{ color: '#e3b85c' }}>{g.kills}</b></div><div>Bosses felled: <b style={{ color: '#e3b85c' }}>{g.bosses}</b></div><div>Deepest depth: <b style={{ color: '#e3b85c' }}>{roman(g.deepest) || 0}</b></div><div>Gold earned: <b style={{ color: '#e3b85c' }}>{g.goldEarned}</b></div>
            </div>
          </aside>
        </div>
      </div>
    );
  }

  function ScreenExploring() {
    const h = g.hero, f = curFloor(), p = g.playerPos; const VW = 21, VH = 15;
    const ox = clamp(p.x - (VW >> 1), 0, Math.max(0, f.w - VW));
    const oy = clamp(p.y - (VH >> 1), 0, Math.max(0, f.h - VH));
    const cells = [];
    for (let y = oy; y < oy + VH; y++) for (let x = ox; x < ox + VW; x++) {
      if (y >= f.h || x >= f.w) { cells.push(<div key={x + '_' + y} className="cos-cell" style={{ background: '#05040a' }} />); continue; }
      const t = f.tiles[y][x], explored = f.explored[y][x];
      const dist = Math.hypot(x - p.x, y - p.y); const lit = dist <= 6.8;
      const light = lit ? clamp(1.18 - dist / 9, 0.5, 1) : (explored ? 0.4 : 0);
      if (!explored && !lit) { cells.push(<div key={x + '_' + y} className="cos-cell" style={{ background: '#05040a' }} />); continue; }
      let glyph = TILE[t] || '', cls = '';
      let bg = t === 'wall' ? 'linear-gradient(135deg,#3a3450,#262036)' : `radial-gradient(circle at 50% 40%, ${shade(g.world.accent, 0.26)}, #1a1626)`;
      let textShadow = '';
      if (lit) {
        const ek = x + ',' + y;
        if (x === p.x && y === p.y) { glyph = CLASSES[h.heroClass].emoji; textShadow = `0 0 12px ${g.world.accent},0 0 4px #fff`; }
        else if (f.enemies[ek]) { const e = f.enemies[ek]; glyph = e.emoji; textShadow = e.boss ? '0 0 14px #d65149' : '0 0 8px #a3322b'; }
        else if (f.items[ek] && t !== 'chest') { glyph = '✨'; textShadow = '0 0 10px #e3b85c'; }
      }
      cells.push(<div key={x + '_' + y} className="cos-cell" style={{ opacity: light, background: bg, fontSize: 'clamp(.7rem,1.7vw,1.1rem)', textShadow, boxShadow: t === 'wall' ? 'inset 0 0 0 1px rgba(0,0,0,.45)' : 'none' }}>{glyph}</div>);
    }
    const quick = h.inventory.filter((i) => i.consumable && (i.heal || i.mp)).slice(0, 5);
    return (
      <div className="cos-scroll" style={{ alignItems: 'stretch' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', padding: '.55rem 1rem', background: 'linear-gradient(#140f1a,#0b0810)', borderBottom: '1px solid #5d4a2c', flexWrap: 'wrap' }}>
          <div style={{ fontFamily: "'Cinzel',serif", color: '#e9dcc0' }}><span style={{ fontSize: '1.3rem' }}>{g.world.emoji}</span> <b>{g.world.name}</b> <span style={{ color: '#6f6657', fontFamily: 'ui-monospace,monospace', fontSize: '.78rem' }}>Depth {roman(g.floorNum)} / {roman(g.world.floors)}</span></div>
          <div style={{ display: 'flex', gap: '.4rem', alignItems: 'center' }}><HeroStrip />
            <button className="cos-btn sm" onClick={restCamp}>🏕️ Rest</button>
            <button className="cos-btn sm" onClick={openChar}>🎒</button>
            <button className="cos-btn sm dng" onClick={returnTown}>⏏ Town</button>
          </div>
        </header>
        <div style={{ display: 'flex', gap: '1rem', width: '100%', maxWidth: 1100, margin: '0 auto', padding: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 280, aspectRatio: '21 / 15', maxHeight: '70vh', border: '2px solid #5d4a2c', borderRadius: 5, overflow: 'hidden', background: '#000' }}>
            <div className="cos-grid" style={{ gridTemplateColumns: `repeat(${VW},1fr)`, gridTemplateRows: `repeat(${VH},1fr)` }}>{cells}</div>
            <div className="cos-vig" />
          </div>
          <aside style={{ width: 'clamp(220px,28vw,300px)', display: 'flex', flexDirection: 'column', gap: '.6rem' }}>
            <div className="cos-card" style={{ padding: '.7rem .8rem' }}>
              <div style={{ fontFamily: "'Cinzel',serif", color: '#e9dcc0', marginBottom: '.3rem' }}>{CLASSES[h.heroClass].emoji} <b>{h.name}</b> <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: '.74rem', color: g.world.accent }}>Lv.{h.level}</span></div>
              <Bar cur={h.hp} max={h.maxHp} kind="hp" /><Bar cur={h.mp} max={h.maxMp} kind="mp" /><Bar cur={h.xp} max={h.xpToNext} kind="xp" />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'ui-monospace,monospace', fontSize: '.72rem', color: '#b6ab98', marginTop: '.35rem' }}><span>ATK {attackPower(h)}</span><span>DEF {defensePower(h)}</span>{h.statPoints ? <span style={{ color: '#e3b85c' }}>✦ {h.statPoints} pts</span> : <span />}</div>
              <Chips list={h.statuses} />
            </div>
            <div className="cos-card" style={{ padding: '.55rem .65rem' }}>
              <div style={{ fontFamily: "'Cinzel',serif", fontSize: '.72rem', color: '#6f6657', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: '.3rem' }}>Potions</div>
              <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap' }}>
                {quick.length ? quick.map((i) => <button key={i.id} className="cos-btn xs" {...tipH(i)} onClick={() => useInv(i.id)} style={{ fontSize: '1.1rem', padding: '.2rem .4rem' }}>{i.emoji}</button>) : <span style={{ fontStyle: 'italic', color: '#6f6657', fontSize: '.78rem' }}>none</span>}
              </div>
            </div>
            <div className="cos-card" style={{ padding: '.55rem .7rem', maxHeight: 180, overflowY: 'auto', fontSize: '.82rem', lineHeight: 1.5 }}>
              {g.log.slice(-9).map((l, i) => <div key={i} style={{ color: i === Math.min(8, g.log.length - 1) ? '#e9dcc0' : '#b6ab98', padding: '.05rem 0' }}>{l}</div>)}
            </div>
          </aside>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,56px)', gridTemplateRows: 'repeat(3,46px)', gap: '.4rem', justifyContent: 'center', margin: '.4rem auto 1.2rem' }}>
          <button className="cos-btn" style={{ gridColumn: 2 }} onClick={() => move(0, -1)}>▲</button>
          <button className="cos-btn" style={{ gridColumn: 1, gridRow: 2 }} onClick={() => move(-1, 0)}>◀</button>
          <button className="cos-btn" style={{ gridColumn: 2, gridRow: 2, fontSize: '.8rem' }} onClick={restCamp}>Rest</button>
          <button className="cos-btn" style={{ gridColumn: 3, gridRow: 2 }} onClick={() => move(1, 0)}>▶</button>
          <button className="cos-btn" style={{ gridColumn: 2, gridRow: 3 }} onClick={() => move(0, 1)}>▼</button>
        </div>
      </div>
    );
  }

  function ScreenCombat() {
    const h = g.hero, c = g.combat, e = c.enemy;
    const skills = SKILLS[h.heroClass].filter((s) => s.lvl <= h.level);
    const items = h.inventory.filter((i) => i.consumable);
    return (
      <div className="cos-scroll" style={{ justifyContent: 'center', gap: '1rem', padding: '1rem' }}>
        <div style={{ width: 'min(96vw,640px)', position: 'relative', background: `radial-gradient(120% 80% at 50% 0%, ${shade(g.world.accent, 0.12)}, #0b0810)`, border: '2px solid #5d4a2c', borderRadius: 6, padding: '1.2rem 1.2rem 1rem' }}>
          <div style={{ textAlign: 'center', position: 'relative' }}>
            <div className="cos-en" style={{ fontSize: 'clamp(3.4rem,12vw,5rem)' }}>{e.emoji}</div>
            <div style={{ fontFamily: "'Cinzel',serif", fontWeight: 600, color: '#fff', fontSize: '1.1rem', margin: '.3rem 0' }}>{e.name} <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: '.78rem', color: '#d65149' }}>Lv.{e.level}{e.boss ? ' 👑' : ''}</span></div>
            <div style={{ maxWidth: 340, margin: '0 auto' }}><Bar cur={e.hp} max={e.maxHp} kind="hp" /></div>
            <Chips list={e.statuses} />
            {g.fx.filter((fx) => fx.side === 'enemy').map((fx) => <span key={fx.id} className={'cos-float' + (fx.crit ? ' crit' : '')} style={{ left: '50%', top: '12%', color: fx.crit ? '#fff' : '#e3b85c' }}>{fx.text}</span>)}
          </div>
          <div style={{ margin: '.9rem auto', maxWidth: 460, maxHeight: 130, overflowY: 'auto', background: 'rgba(8,6,11,.7)', border: '1px solid #5d4a2c', borderRadius: 4, padding: '.5rem .8rem', fontSize: '.84rem', lineHeight: 1.5 }}>
            {c.log.slice(-12).map((l, i) => <div key={i}>{l}</div>)}
          </div>
          <div style={{ position: 'relative' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem', justifyContent: 'center', marginBottom: '.3rem' }}><span style={{ fontSize: '1.7rem' }}>{CLASSES[h.heroClass].emoji}</span><span style={{ fontFamily: "'Cinzel',serif", color: '#e9dcc0' }}>{h.name}</span></div>
            <div style={{ maxWidth: 340, margin: '0 auto' }}><Bar cur={h.hp} max={h.maxHp} kind="hp" /><Bar cur={h.mp} max={h.maxMp} kind="mp" /></div>
            <Chips list={h.statuses} />
            {g.fx.filter((fx) => fx.side === 'hero').map((fx) => <span key={fx.id} className="cos-float" style={{ left: '50%', top: '40%', color: '#d65149' }}>{fx.text}</span>)}
          </div>
        </div>
        <div style={{ width: 'min(96vw,640px)' }}>
          {c.rewards ? (
            <div className="cos-card" style={{ textAlign: 'center', padding: '1rem', border: '1px solid #c9a567' }}>
              <div style={{ fontFamily: "'Cinzel Decorative',serif", fontWeight: 700, color: '#e3b85c', fontSize: '1.4rem' }}>Victory!</div>
              <div style={{ fontFamily: 'ui-monospace,monospace', color: '#e9dcc0', margin: '.4rem 0' }}>+{c.rewards.xp} XP · +{c.rewards.gold} 🪙</div>
              {c.rewards.items && c.rewards.items.length > 0 && <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.4rem', justifyContent: 'center', margin: '.5rem 0' }}>{c.rewards.items.map((it) => Pill(it))}</div>}
              <button className="cos-btn pri" onClick={collect}>Collect & Continue</button>
            </div>
          ) : c.fled ? (
            <div className="cos-card" style={{ textAlign: 'center', padding: '1rem' }}><div style={{ marginBottom: '.6rem' }}>You slip back into the dark.</div><button className="cos-btn pri" onClick={fledOut}>Continue</button></div>
          ) : c.sel === 'skill' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '.5rem' }}>
              {skills.length ? skills.map((s) => { const can = h.mp >= s.mp; return (
                <button key={s.id} className="cos-btn" disabled={!can} onClick={() => combatSkill(s)} style={{ textAlign: 'left' }}>{s.emoji} {s.name} <span style={{ color: '#5f93d6', fontFamily: 'ui-monospace,monospace', fontSize: '.74rem' }}>{s.mp} MP</span><div style={{ fontSize: '.78rem', color: '#b6ab98', fontStyle: 'italic' }}>{s.desc}</div></button>); }) : <div style={{ textAlign: 'center', fontStyle: 'italic', color: '#6f6657' }}>No skills yet.</div>}
              <button className="cos-btn sm" onClick={() => { c.sel = null; rr(); }}>← Back</button>
            </div>
          ) : c.sel === 'item' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '.5rem' }}>
              {items.length ? items.map((it) => <button key={it.id} className="cos-btn" {...tipH(it)} onClick={() => combatItem(it)} style={{ textAlign: 'left' }}>{it.emoji} {it.name} <span style={{ fontSize: '.76rem', color: '#b6ab98' }}>{strengthBits(it).join(' · ')}</span></button>) : <div style={{ textAlign: 'center', fontStyle: 'italic', color: '#6f6657' }}>No usable items.</div>}
              <button className="cos-btn sm" onClick={() => { c.sel = null; rr(); }}>← Back</button>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(100px,1fr))', gap: '.5rem' }}>
              <button className="cos-btn pri" onClick={combatAttack}>⚔️ Attack</button>
              <button className="cos-btn" onClick={() => { c.sel = 'skill'; rr(); }}>✨ Skill</button>
              <button className="cos-btn" onClick={() => { c.sel = 'item'; rr(); }}>🧪 Item</button>
              <button className="cos-btn" onClick={combatDefend}>🛡️ Defend</button>
              <button className="cos-btn dng" disabled={e.boss} onClick={combatFlee}>🏃 Flee</button>
            </div>
          )}
        </div>
      </div>
    );
  }

  function ScreenCharacter() {
    const h = g.hero; const slots = ['weapon', 'armor', 'shield', 'ring', 'amulet'];
    const b = equipBonus(h);
    return (
      <div className="cos-scroll" style={{ paddingTop: '3vh' }}>
        <div className="cos-parch" style={{ width: 'min(96vw,940px)', padding: '1.4rem', maxHeight: '92vh', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.8rem' }}><span style={{ fontSize: '2.4rem' }}>{CLASSES[h.heroClass].emoji}</span><div><h2 style={{ fontFamily: "'Cinzel Decorative',serif", color: '#33260f', fontSize: '1.4rem' }}>{h.name}</h2><div style={{ fontStyle: 'italic', color: '#6a5b41', fontSize: '.86rem' }}>{CLASSES[h.heroClass].name} · Level {h.level} · 🪙 {h.gold}</div></div></div>
            <button className="cos-btn" onClick={closeChar}>Close ✕</button>
          </div>
          <div style={{ margin: '.6rem 0' }}><Bar cur={h.hp} max={h.maxHp} kind="hp" /><Bar cur={h.mp} max={h.maxMp} kind="mp" /><Bar cur={h.xp} max={h.xpToNext} kind="xp" /></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.2rem' }}>
            <div>
              <ColH>Equipped</ColH>
              {slots.map((s) => { const it = h.equipment[s]; return (
                <div key={s} style={{ display: 'flex', alignItems: 'center', gap: '.5rem', marginBottom: '.35rem', fontSize: '.86rem' }}>
                  <span style={{ fontFamily: "'Cinzel',serif", fontSize: '.7rem', textTransform: 'uppercase', color: '#6a5b41', width: 60 }}>{s}</span>
                  {it ? <div className="cos-row" {...tipH(it)} style={{ '--rc': rarityColor(it), flex: 1, justifyContent: 'space-between' }}><span>{it.emoji} {it.name} <em style={{ fontStyle: 'normal', color: RC[rarityName(it)] }}>· {rarityName(it)} Lv.{it.lvl || 1}</em></span><button className="cos-btn xs" onClick={() => unequipSlot(s)}>remove</button></div> : <span style={{ flex: 1, color: '#6a5b41', fontStyle: 'italic' }}>— empty —</span>}
                </div>); })}
              <ColH>Attributes {h.statPoints > 0 && <span style={{ color: '#a3322b', fontStyle: 'italic', fontSize: '.74rem' }}>✦ {h.statPoints} to spend</span>}</ColH>
              {Object.entries(h.stats).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', alignItems: 'center', gap: '.6rem', fontFamily: 'ui-monospace,monospace', fontSize: '.86rem', color: '#3a2c14' }}>
                  <span style={{ width: 46, color: '#6a5b41' }}>{k.toUpperCase()}</span><span style={{ flex: 1, fontWeight: 600 }}>{v}{b[k] ? <i style={{ color: '#5a9e54', fontStyle: 'normal' }}> +{b[k]}</i> : ''}</span>
                  {h.statPoints > 0 && <button className="cos-btn xs" onClick={() => allocate(k)}>+</button>}
                </div>))}
              <div style={{ display: 'flex', gap: '1rem', marginTop: '.6rem', fontSize: '.9rem', color: '#3a2c14' }}><span>Attack <b>{attackPower(h)}</b></span><span>Defense <b>{defensePower(h)}</b></span></div>
            </div>
            <div>
              <ColH>Pack ({h.inventory.length})</ColH>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '.35rem', maxHeight: 320, overflowY: 'auto' }}>
                {h.inventory.length ? h.inventory.map((it) => { const canEquip = it.slot && it.lvl <= h.level; const canUse = it.consumable && !(it.damage && !it.heal && !it.mp); return (
                  <div key={it.id} className="cos-row" style={{ '--rc': rarityColor(it) }}>
                    <span {...tipH(it)} style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{it.emoji} {it.name} {it.slot ? <em style={{ fontStyle: 'normal', color: RC[rarityName(it)] }}>· {rarityName(it)} Lv.{it.lvl || 1}</em> : ''}</span>
                    <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: '.72rem', color: '#6a5b41', flexShrink: 0 }}>{strengthBits(it).join(' · ')}</span>
                    <span style={{ display: 'flex', gap: '.3rem', flexShrink: 0 }}>
                      {canEquip && <button className="cos-btn xs" onClick={() => equip(it.id)}>equip</button>}
                      {it.slot && it.lvl > h.level && <span style={{ color: '#a3322b', fontFamily: 'ui-monospace,monospace', fontSize: '.7rem' }}>Lv.{it.lvl}</span>}
                      {canUse && <button className="cos-btn xs" onClick={() => useInv(it.id)}>use</button>}
                      <button className="cos-btn xs dng" onClick={() => dropItem(it.id)}>✕</button>
                    </span>
                  </div>); }) : <div style={{ fontStyle: 'italic', color: '#6a5b41' }}>Your pack is empty.</div>}
              </div>
              <ColH>Skills</ColH>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '.4rem' }}>
                {h.skills.map((s) => <div key={s.id} style={{ background: 'rgba(255,255,255,.18)', borderRadius: 3, padding: '.35rem .55rem', fontSize: '.84rem', color: '#33260f' }}><b>{s.emoji} {s.name}</b> <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: '.72rem', color: '#3f6fae', float: 'right' }}>{s.mp} MP</span><div style={{ fontSize: '.78rem', color: '#6a5b41', fontStyle: 'italic' }}>{s.desc}</div></div>)}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  function ScreenShop() {
    const h = g.hero;
    return (
      <div className="cos-scroll" style={{ paddingTop: '3vh' }}>
        <div className="cos-parch" style={{ width: 'min(96vw,940px)', padding: '1.4rem', maxHeight: '92vh', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.8rem' }}><span style={{ fontSize: '2.4rem' }}>🛒</span><div><h2 style={{ fontFamily: "'Cinzel Decorative',serif", color: '#33260f', fontSize: '1.4rem' }}>The Hollow Merchant</h2><div style={{ fontStyle: 'italic', color: '#6a5b41', fontSize: '.86rem' }}>"Coin for steel, steel for survival." · 🪙 {h.gold}</div></div></div>
            <button className="cos-btn" onClick={() => { g.screen = 'exploring'; rr(); }}>Leave ✕</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.2rem', marginTop: '.6rem' }}>
            <div><ColH>For sale</ColH><div style={{ display: 'flex', flexDirection: 'column', gap: '.35rem' }}>
              {g.shop.length ? g.shop.map((it) => { const afford = h.gold >= it.value; return (
                <div key={it.id} className="cos-row" style={{ '--rc': rarityColor(it) }}>
                  <span {...tipH(it)} style={{ flex: 1, minWidth: 0 }}>{it.emoji} {it.name} <em style={{ fontStyle: 'normal', color: RC[rarityName(it)] }}>· {rarityName(it)} Lv.{it.lvl || 1}</em></span>
                  <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: '.72rem', color: '#6a5b41' }}>{strengthBits(it).join(' · ')}</span>
                  <button className="cos-btn xs" disabled={!afford} onClick={() => buy(it.id)}>{it.value} 🪙</button>
                </div>); }) : <div style={{ fontStyle: 'italic', color: '#6a5b41' }}>Sold out.</div>}
            </div></div>
            <div><ColH>Sell from pack</ColH><div style={{ display: 'flex', flexDirection: 'column', gap: '.35rem' }}>
              {h.inventory.length ? h.inventory.map((it) => (
                <div key={it.id} className="cos-row" style={{ '--rc': rarityColor(it) }}>
                  <span {...tipH(it)} style={{ flex: 1, minWidth: 0 }}>{it.emoji} {it.name}</span>
                  <button className="cos-btn xs" onClick={() => sell(it.id)}>sell {Math.floor(it.value * 0.4)} 🪙</button>
                </div>)) : <div style={{ fontStyle: 'italic', color: '#6a5b41' }}>Nothing to sell.</div>}
            </div></div>
          </div>
        </div>
      </div>
    );
  }

  function ScreenLevelUp() {
    const h = g.hero;
    return (
      <div className="cos-scroll" style={{ justifyContent: 'center' }}>
        <div className="cos-parch" style={{ width: 'min(96vw,460px)', padding: '1.4rem', textAlign: 'center' }}>
          <div style={{ fontSize: '3rem' }}>✨</div>
          <h2 style={{ fontFamily: "'Cinzel Decorative',serif", color: '#33260f', fontSize: '1.6rem' }}>Level {h.level}!</h2>
          {g._levelMsgs.map((m, i) => <div key={i} style={{ color: '#3a2c14', fontSize: '.92rem' }}>{m}</div>)}
          <div style={{ fontFamily: "'Cinzel',serif", color: '#4a3818', margin: '.6rem 0' }}>{h.statPoints > 0 ? <>You have <b style={{ color: '#a3322b' }}>{h.statPoints}</b> points to spend.</> : 'All points spent.'}</div>
          <div style={{ maxWidth: 320, margin: '0 auto', textAlign: 'left' }}>
            {Object.entries(h.stats).map(([k, v]) => <div key={k} style={{ display: 'flex', alignItems: 'center', gap: '.6rem', fontFamily: 'ui-monospace,monospace', fontSize: '.9rem', color: '#3a2c14', padding: '.1rem 0' }}><span style={{ width: 46, color: '#6a5b41' }}>{k.toUpperCase()}</span><span style={{ flex: 1, fontWeight: 600 }}>{v}</span>{h.statPoints > 0 && <button className="cos-btn xs" onClick={() => allocate(k)}>+</button>}</div>)}
          </div>
          <button className="cos-btn pri" style={{ marginTop: '1rem' }} onClick={() => { g.screen = g._afterLevel === 'victory' ? 'victory' : 'exploring'; rr(); }}>Continue</button>
        </div>
      </div>
    );
  }

  function ScreenEnd({ win }) {
    const h = g.hero;
    return (
      <div className="cos-scroll" style={{ justifyContent: 'center' }}>
        <div className={win ? 'cos-flicker' : ''} style={{ fontSize: '4rem', filter: win ? 'drop-shadow(0 0 24px #e3b85c)' : 'drop-shadow(0 0 24px #d65149)' }}>{win ? '🏆' : '☠️'}</div>
        <h1 className="cos-title" style={{ fontSize: 'clamp(2rem,7vw,3.4rem)' }}>{win ? 'The World is Cleansed' : 'You Have Fallen'}</h1>
        <p style={{ fontStyle: 'italic', color: '#6f6657', margin: '.8rem 0', textAlign: 'center', maxWidth: '40ch' }}>{win ? `${h.name} drove the dark from ${g.world ? g.world.name : 'the depths'} and lived to tell it.` : `${h.name} the ${CLASSES[h.heroClass].name} fell at depth ${roman(g.deepest) || 'I'}. The crypt keeps its own.`}</p>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center', margin: '1rem 0', fontFamily: 'ui-monospace,monospace', fontSize: '.9rem', color: '#b6ab98' }}>
          <span className="cos-card" style={{ padding: '.35rem .7rem' }}>Level {h.level}</span><span className="cos-card" style={{ padding: '.35rem .7rem' }}>Kills {g.kills}</span><span className="cos-card" style={{ padding: '.35rem .7rem' }}>Bosses {g.bosses}</span>
        </div>
        <div style={{ display: 'flex', gap: '.7rem' }}>
          {win ? <button className="cos-btn pri" onClick={returnTown}>Return to Gallows Rest</button> : <>
            <button className="cos-btn pri" onClick={() => { if (SAVE.auto && !diffObj().perma) { loadPayload(SAVE.auto); g.screen = g.world ? 'exploring' : 'town'; } else { g.creation = { name: '', cls: 'warrior', diff: 'normal' }; resetRun(); g.screen = 'creation'; } rr(); }}>{SAVE.auto && !diffObj().perma ? 'Reload last camp' : 'New hero'}</button>
            <button className="cos-btn" onClick={() => { g.screen = 'menu'; rr(); }}>Main menu</button></>}
        </div>
      </div>
    );
  }

  const SCREENS = { menu: ScreenMenu, creation: ScreenCreation, town: ScreenTown, exploring: ScreenExploring, combat: ScreenCombat, character: ScreenCharacter, shop: ScreenShop, levelup: ScreenLevelUp, victory: () => <ScreenEnd win />, gameover: () => <ScreenEnd win={false} /> };
  const Active = SCREENS[g.screen] || ScreenMenu;

  return (
    <div className={'cos-root' + (g.shake ? ' cos-shake' : '')} style={{ '--accent': g.world ? g.world.accent : '#e8a13a' }}>
      <style>{CSS}</style>
      <Active />
      {tip && (
        <div className="cos-tt" style={{ left: Math.min(tip.x + 16, (typeof window !== 'undefined' ? window.innerWidth : 1200) - 312), top: tip.y + 14 }}>
          {itemTipNode(tip.it)}
        </div>
      )}
    </div>
  );
}

function ColH({ children }) {
  return <h3 style={{ fontFamily: "'Cinzel',serif", fontWeight: 700, color: '#4a3818', fontSize: '.82rem', letterSpacing: '.08em', textTransform: 'uppercase', margin: '.9rem 0 .45rem', borderBottom: '1px solid rgba(120,92,46,.35)', paddingBottom: '.25rem' }}>{children}</h3>;
}

/* lighten/mix a hex accent toward a base for floor tiles */
function shade(hex, amt) {
  try {
    const h = hex.replace('#', ''); const r = parseInt(h.slice(0, 2), 16), gg = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
    const mix = (c, base) => Math.round(c * amt + base * (1 - amt));
    return `rgb(${mix(r, 42)},${mix(gg, 36)},${mix(b, 56)})`;
  } catch (e) { return '#2a2438'; }
}
