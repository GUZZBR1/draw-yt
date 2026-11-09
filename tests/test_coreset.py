import unittest

import numpy as np

from drawyt.coreset import assign_clusters, kcenter_greedy, medoid_index


class TestCoreset(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        cluster_a = rng.normal([0.0, 0.0], 0.05, size=(30, 2))
        cluster_b = rng.normal([5.0, 5.0], 0.05, size=(30, 2))
        self.points = np.concatenate([cluster_a, cluster_b])

    def test_budget_is_respected(self):
        chosen = kcenter_greedy(self.points, 10, seed_index=medoid_index(self.points))
        self.assertEqual(len(chosen), 10)
        self.assertEqual(len(set(chosen)), 10)

    def test_cover_reaches_both_clusters(self):
        chosen = kcenter_greedy(self.points, 4, seed_index=0)
        chosen_points = self.points[chosen]
        self.assertTrue((chosen_points[:, 0] < 1).any())
        self.assertTrue((chosen_points[:, 0] > 4).any())

    def test_assign_clusters_covers_all_points(self):
        chosen = kcenter_greedy(self.points, 4, seed_index=0)
        labels = assign_clusters(self.points, chosen)
        self.assertEqual(len(labels), len(self.points))
        self.assertGreaterEqual(labels.min(), 0)


if __name__ == "__main__":
    unittest.main()
