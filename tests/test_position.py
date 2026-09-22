import unittest

from gradysim.protocol.position import rotate_position_2d


class PositionTestCase(unittest.TestCase):
    def test_rotate_position_2d_zero_degrees(self):
        pos = (10.0, 20.0, 5.0)
        rotated = rotate_position_2d(pos, 0.0)
        self.assertAlmostEqual(rotated[0], 10.0)
        self.assertAlmostEqual(rotated[1], 20.0)
        self.assertEqual(rotated[2], 5.0)

    def test_rotate_position_2d_90_degrees(self):
        pos = (1.0, 0.0, 3.0)
        rotated = rotate_position_2d(pos, 90.0)
        self.assertAlmostEqual(rotated[0], 0.0)
        self.assertAlmostEqual(rotated[1], 1.0)
        self.assertEqual(rotated[2], 3.0)

    def test_rotate_position_2d_180_degrees(self):
        pos = (1.0, 0.0, 3.0)
        rotated = rotate_position_2d(pos, 180.0)
        self.assertAlmostEqual(rotated[0], -1.0)
        self.assertAlmostEqual(rotated[1], 0.0)
        self.assertEqual(rotated[2], 3.0)

    def test_rotate_position_2d_270_degrees(self):
        pos = (1.0, 0.0, 3.0)
        rotated = rotate_position_2d(pos, 270.0)
        self.assertAlmostEqual(rotated[0], 0.0)
        self.assertAlmostEqual(rotated[1], -1.0)
        self.assertEqual(rotated[2], 3.0)

    def test_rotate_position_2d_negative_90_degrees(self):
        pos = (1.0, 0.0, 3.0)
        rotated = rotate_position_2d(pos, -90.0)
        self.assertAlmostEqual(rotated[0], 0.0)
        self.assertAlmostEqual(rotated[1], -1.0)
        self.assertEqual(rotated[2], 3.0)

    def test_rotate_position_2d_preserves_distance_and_z(self):
        pos = (3.0, 4.0, 10.0)
        for angle in [15, 30, 45, 60, 120, 215, 330, 360]:
            rotated = rotate_position_2d(pos, float(angle))
            # Distance in XY plane should be conserved (3^2 + 4^2 = 25)
            self.assertAlmostEqual(rotated[0] ** 2 + rotated[1] ** 2, 25.0, places=7)
            # Z coordinate must be invariant
            self.assertEqual(rotated[2], 10.0)


if __name__ == '__main__':
    unittest.main()
