import json
import unittest
from types import SimpleNamespace

from app import hydra
from app.config import settings


def ns(**values):
    return SimpleNamespace(**values)


class FakeContext:
    def __init__(self):
        self.ingest_call = None

    def ingest(self, **kwargs):
        self.ingest_call = kwargs
        return ns(data=ns(results=[ns(id="memory-1")]))

    def status(self, **kwargs):
        return ns(data=ns(statuses=[ns(indexing_status="completed")]))


class FakeClient:
    def __init__(self):
        self.context = FakeContext()
        self.tenants = ns(status=lambda **_: ns(data=ns(infra=ns(ready_for_ingestion=True))))
        self.query_call = None

    def query(self, **kwargs):
        self.query_call = kwargs
        return ns(
            data=ns(
                chunks=[
                    ns(
                        chunk_content="The player returned the relic.",
                        additional_metadata={"importance": 0.9, "source": "event"},
                        relevancy_score=0.95,
                    )
                ]
            )
        )


class HydraDBIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.original_client = hydra._client
        self.original_key = settings.hydra_db_api_key
        self.original_tenant = settings.hydra_tenant_id
        settings.hydra_db_api_key = "test-key"
        settings.hydra_tenant_id = "awaken_test"
        hydra._client = FakeClient()

    def tearDown(self):
        hydra._client = self.original_client
        settings.hydra_db_api_key = self.original_key
        settings.hydra_tenant_id = self.original_tenant

    def test_stores_structured_memory_and_waits_for_indexing(self):
        hydra.store_memories(
            "world-1",
            "npc-1",
            [{"text": "The player helped.", "importance": 0.8, "source": "event"}],
        )

        call = hydra._client.context.ingest_call
        self.assertEqual(call["type"], "memory")
        self.assertEqual(call["tenant_id"], "awaken_test")
        self.assertEqual(call["sub_tenant_id"], "world_world1__npc_npc1")
        memory = json.loads(call["memories"])[0]
        self.assertFalse(memory["infer"])
        self.assertEqual(memory["additional_metadata"]["importance"], 0.8)

    def test_recalls_ranked_memories_from_the_same_scope(self):
        memories = hydra.recall_memories("world-1", "npc-1", "relic", limit=3)

        self.assertEqual(memories[0]["text"], "The player returned the relic.")
        self.assertEqual(memories[0]["relevancy_score"], 0.95)
        self.assertEqual(hydra._client.query_call["type"], "memory")
        self.assertEqual(hydra._client.query_call["max_results"], 3)
        self.assertEqual(
            hydra._client.query_call["sub_tenant_id"], "world_world1__npc_npc1"
        )

    def test_validates_the_configured_tenant(self):
        hydra.validate_connection()

    def test_upserts_world_knowledge_without_npc_scope(self):
        ids = hydra.store_world_knowledge(
            [
                {
                    "id": "world_test",
                    "title": "Test World",
                    "type": "custom",
                    "content": {"text": "Canonical lore"},
                }
            ]
        )

        call = hydra._client.context.ingest_call
        self.assertEqual(ids, ["memory-1"])
        self.assertEqual(call["type"], "knowledge")
        self.assertNotIn("sub_tenant_id", call)
        self.assertEqual(json.loads(call["app_knowledge"])[0]["id"], "world_test")


if __name__ == "__main__":
    unittest.main()
