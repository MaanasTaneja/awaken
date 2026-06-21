export interface WorldEvent {
  id: string;
  label: string;
  event_type: string;
  summary: string;
  importance: number;
  visibility: "PUBLIC" | "PRIVATE";
}

export const EVENTS: WorldEvent[] = [
  { id: "steal",   label: "Steal Sacred Relic",  event_type: "ITEM_STOLEN",        summary: "Player stole the Sacred Relic from the Ashen Temple", importance: 0.9,  visibility: "PUBLIC" },
  { id: "return",  label: "Complete Relic Quest",event_type: "QUEST_COMPLETED",    summary: "Player returned the Sacred Relic to Varyon",          importance: 0.8,  visibility: "PUBLIC" },
  { id: "attack",  label: "Attack Villager",     event_type: "PLAYER_ATTACKED_NPC",summary: "Player attacked a villager in the town square",       importance: 0.85, visibility: "PUBLIC" },
  { id: "donate",  label: "Donate to Temple",    event_type: "PLAYER_DONATED",     summary: "Player donated gold to the Ashen Temple",             importance: 0.6,  visibility: "PUBLIC" },
];
