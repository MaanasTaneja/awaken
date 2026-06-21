export interface WorldEvent {
  id: string;
  label: string;
  faction: string;          // stable_key matching seed factions map
  event_type: string;
  summary: string;
  importance: number;
  visibility: "PUBLIC" | "PRIVATE";
}

export const EVENTS: WorldEvent[] = [
  { id: "steal_relic",    label: "⚔ Steal Sacred Relic",      faction: "ashen_temple",   event_type: "ITEM_STOLEN",         summary: "Player stole the Sacred Relic from the Ashen Temple",              importance: 0.9,  visibility: "PUBLIC" },
  { id: "return_relic",   label: "✦ Return Sacred Relic",      faction: "ashen_temple",   event_type: "QUEST_COMPLETED",     summary: "Player returned the Sacred Relic to Varyon at the Ashen Temple",   importance: 0.85, visibility: "PUBLIC" },
  { id: "calibrate_lens", label: "✦ Calibrate the Star Lens",  faction: "mages_guild",    event_type: "QUEST_COMPLETED",     summary: "Player calibrated the Star Lens for Elara of the Mages Guild",     importance: 0.8,  visibility: "PUBLIC" },
  { id: "deliver_letter", label: "✦ Deliver Sealed Letter",    faction: "merchant_house", event_type: "QUEST_COMPLETED",     summary: "Player delivered the sealed letter for Mira of the Merchant House", importance: 0.75, visibility: "PUBLIC" },
  { id: "map_tunnels",    label: "✦ Map Smuggler Tunnels",     faction: "merchant_house", event_type: "QUEST_COMPLETED",     summary: "Player mapped the smuggler tunnels for Bren of the Merchant House", importance: 0.7,  visibility: "PUBLIC" },
  { id: "attack",         label: "⚔ Attack Villager",          faction: "ashen_temple",   event_type: "PLAYER_ATTACKED_NPC", summary: "Player attacked a villager in the town square",                     importance: 0.9,  visibility: "PUBLIC" },
];
