import json
import unittest
from unittest.mock import patch

from app.config import settings
from app.dialogue import form_npc_beliefs


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "affinity_delta": -8,
                                "trust_delta": -12,
                                "fear_delta": 2,
                                "respect_delta": -3,
                                "add_belief_tags": ["PLAYER_MAY_BE_THIEF"],
                                "remove_belief_tags": [],
                                "belief_summary": "The NPC suspects the player stole the relic.",
                                "memories": [
                                    {
                                        "text": "The theft confirmed an old suspicion.",
                                        "importance": 0.9,
                                        "source": "interpretation",
                                    }
                                ],
                            }
                        )
                    }
                }
            ]
        }


class StructuredDialogueTests(unittest.TestCase):
    def setUp(self):
        self.original_key = settings.openai_api_key
        settings.openai_api_key = "test-key"

    def tearDown(self):
        settings.openai_api_key = self.original_key

    @patch("app.dialogue.httpx.post", return_value=FakeResponse())
    def test_belief_update_uses_strict_schema_and_top_level_output(self, post):
        result = form_npc_beliefs(
            npc={"name": "Varyon"},
            faction={"name": "Ashen Temple"},
            current_state={},
            events=[{"event_type": "ITEM_STOLEN"}],
            gossip=[],
        )

        response_format = post.call_args.kwargs["json"]["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertEqual(result["trust_delta"], -12)
        self.assertEqual(result["memories"][0]["source"], "interpretation")


if __name__ == "__main__":
    unittest.main()
