import varyon from "@/assets/game/varyon.png";
import cassian from "@/assets/game/cassian.png";
import elara from "@/assets/game/elara.png";
import pell from "@/assets/game/pell.png";
import mira from "@/assets/game/mira.png";
import bren from "@/assets/game/bren.png";

export type Faction = "ashen_temple" | "mages_guild" | "merchant_house";

export interface NPC {
  id: string;
  name: string;
  faction: Faction;
  factionLabel: string;
  color: string;       // CSS hex
  glow: number;        // three hex
  position: [number, number, number];
  sprite: string;
}

export const FACTION_COLORS: Record<Faction, string> = {
  ashen_temple: "#e2433b",
  mages_guild: "#a259ff",
  merchant_house: "#e8b84a",
};

export const NPCS: NPC[] = [
  { id: "varyon",  name: "Varyon the Priest",   faction: "ashen_temple",   factionLabel: "Ashen Temple",   color: FACTION_COLORS.ashen_temple,   glow: 0xff3c2f, position: [-13, 0,  2.5], sprite: varyon },
  { id: "cassian", name: "Cassian the Guard",   faction: "ashen_temple",   factionLabel: "Ashen Temple",   color: FACTION_COLORS.ashen_temple,   glow: 0xff3c2f, position: [-13, 0, -2.5], sprite: cassian },
  { id: "elara",   name: "Elara the Archmage",  faction: "mages_guild",    factionLabel: "Mages Guild",    color: FACTION_COLORS.mages_guild,    glow: 0xa259ff, position: [ 13, 0,  2.5], sprite: elara },
  { id: "pell",    name: "Pell the Apprentice", faction: "mages_guild",    factionLabel: "Mages Guild",    color: FACTION_COLORS.mages_guild,    glow: 0xa259ff, position: [ 13, 0, -2.5], sprite: pell },
  { id: "mira",    name: "Mira the Merchant",   faction: "merchant_house", factionLabel: "Merchant House", color: FACTION_COLORS.merchant_house, glow: 0xffc857, position: [  2.5, 0, -13], sprite: mira },
  { id: "bren",    name: "Bren the Serf",       faction: "merchant_house", factionLabel: "Merchant House", color: FACTION_COLORS.merchant_house, glow: 0xffc857, position: [ -2.5, 0, -13], sprite: bren },
];
