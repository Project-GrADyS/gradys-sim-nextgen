import unittest

from gradysim.simulator.handler.visualization import VisualizationHandler, VisualizationController


class TestVisualization(unittest.TestCase):
    def test_visualization_controller(self):
        dummy_handler = VisualizationHandler()

        controller = VisualizationController()

        controller.paint_node(0, (0, 0, 0))
        controller.resize_nodes(10)
        controller.paint_environment((0, 0, 0))

        self.assertEqual(dummy_handler.command_queue.qsize(), 3)

        paint_command = dummy_handler.command_queue.get()
        self.assertEqual(paint_command['command'], "paint_node")
        self.assertEqual(paint_command['payload']['node_id'], 0)
        self.assertEqual(paint_command['payload']['color'], (0, 0, 0))

        resize_command = dummy_handler.command_queue.get()
        self.assertEqual(resize_command['command'], "resize_nodes")
        self.assertEqual(resize_command['payload']['size'], 10)

        paint_environment_command = dummy_handler.command_queue.get()
        self.assertEqual(paint_environment_command['command'], "paint_environment")
        self.assertEqual(paint_environment_command['payload']['color'], (0, 0, 0))

        self.assertTrue(dummy_handler.command_queue.empty())