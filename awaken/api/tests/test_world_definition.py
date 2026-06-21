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

    def test_optional_quests_have_refusal_branches(self):
        definition = load_world_definition(DEFAULT_WORLD_FILE)

        for quest in definition.quests.values():
            if not quest.essential:
                self.assertTrue(quest.quest_dialogue.refused_base)

    def test_every_quest_has_active_and_completed_status_dialogue(self):
        definition = load_world_definition(DEFAULT_WORLD_FILE)

        for quest in definition.quests.values():
            self.assertTrue(quest.quest_dialogue.active_base)
            self.assertTrue(quest.quest_dialogue.completed_base)


if __name__ == "__main__":
    unittest.main()
