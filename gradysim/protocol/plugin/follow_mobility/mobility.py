
LEADER_TAG = "FollowMobilityPlugin__leader"
"""
The leader will broadcast its position using a packet with this tag, make sure it doesn't conflict with other packets
"""

BROADCAST_TIMER_TAG = "FollowMobilityPlugin__leader_broadcast_timer"
"""
The leader will broadcast its position using a timer with this name, make sure it doesn't conflict with other timers
"""

FOLLOWER_TAG = "FollowMobilityPlugin__follower"
FOLLOWER_TIMER_TAG = "FollowMobilityPlugin__follower_timer"