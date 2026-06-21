import unittest

from app.seed import DEFAULT_WORLD_FILE
from app.world_definition import TRACK_IDS, load_world_definition


class WorldDefinitionTests(unittest.TestCase):
    def test_aelryn_definition_is_complete(self):
        definition = load_world_definition(DEFAULT_WORLD_FILE)

        self.assertEqual(definition.world.id, "aelryn")
        self.assertEqual(len(definition.factions), 3)
        self.assertEqual(len(definition.quests), 4)
        self.assertEqual(len(definition.npcs), 5)
        for npc in definition.npcs.values():
            self.assertEqual(set(npc.tracks), TRACK_IDS)
            self.assertIn(npc.quest, definition.quests)

    def test_essential_quests_have_base_dialogue(self):
        definition = load_world_definition(DEFAULT_WORLD_FILE)

        for quest in definition.quests.values():
            if quest.essential:
                self.assertTrue(quest.base_dialogue)

if __name__ == "__main__":
    unittest.main()
