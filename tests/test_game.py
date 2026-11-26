import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

spec = importlib.util.spec_from_file_location("game", Path(__file__).resolve().parents[1] / "Friday13-II-v2.py")
game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game)


class GameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        original = game.SAVE_FILE
        self.addCleanup(setattr, game, "SAVE_FILE", original)
        game.SAVE_FILE = Path(self.temp.name) / "records.json"

    def test_record_roundtrip(self):
        self.assertEqual(game.load_record(), 0)
        self.assertTrue(game.save_record(42))
        self.assertEqual(game.load_record(), 42)

    def test_corrupt_record(self):
        game.SAVE_FILE.write_text("invalid")
        self.assertEqual(game.load_record(), 0)

    def test_chunk_determinism(self):
        a = game.generate_chunk(-2, 3)
        game.generate_chunk.cache_clear()
        self.assertEqual(a, game.generate_chunk(-2, 3))
        self.assertEqual(len(a), game.CHUNK_SIZE)
        self.assertTrue(all(len(row) == game.CHUNK_SIZE for row in a))

    def test_safe_start(self):
        world = game.World()
        x, y = world.find_start()
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                self.assertFalse(world.is_blocked(x + dx, y + dy))

    def test_food_spawn(self):
        g = game.Game.__new__(game.Game)
        g.start_game()
        self.assertTrue(g.foods)
        for pos in g.foods:
            self.assertNotIn(pos, g.occupied)
            self.assertFalse(g.world.is_blocked(*pos))
