from lyra_robot import RobotAgent
class TestRobot:
    def test_sense(self):
        r = RobotAgent(); s = r.sense("temperature", 25.5); assert s.value == 25.5
    def test_move(self):
        r = RobotAgent(); r.move(5, 10); assert r.stats["position"] == [5, 10]
