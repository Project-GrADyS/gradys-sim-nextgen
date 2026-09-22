"""
This module declares two plugin for the protocol: a leader and a follower. The leader broadcasts its position and the
follower follows it.

Beware that this plugin controls your protocol's mobility to implement its behaviour, so you should not use any other
mobility plugin with it or implement any mobility behaviour in your protocol. The MobilityLeaderPlugin does not affect
the node's movement and thus should be fine to use with other mobility plugin or mobility behaviour.
"""


from gradysim.protocol.plugin.follow_mobility.follower import MobilityFollowerConfiguration, MobilityFollowerPlugin
from gradysim.protocol.plugin.follow_mobility.leader import MobilityLeaderConfiguration, MobilityLeaderPlugin

__all__ = [
    'MobilityFollowerConfiguration',
    'MobilityFollowerPlugin',
    'MobilityLeaderConfiguration',
    'MobilityLeaderPlugin'
]