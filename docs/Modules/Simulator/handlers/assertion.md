:::gradysim.simulator.handler.assertion.AssertionHandler

## Creating assertions
Assertions can be created using one of the provided assertion decorators. They should be
applied to a function implementing the condition you wish to verify is met during the 
simulation. 

The parameters received by the decorated function changes depending on the decorator
being used, but a common characteristic is that they always should return a Boolean,
indicating whether the condition is met or not.

Here is an example of how a function is decorated to generate an assertion:

```py
@assert_always_true_for_simulation(name="received_equals_sent")
def assert_received_equals_sent(nodes: List[Node[PingProtocol]]) -> bool:
    received = 0
    sent = 0
    for node in nodes:
        received += node.protocol_encapsulator.protocol.received
        sent += node.protocol_encapsulator.protocol.received
    return received == sent
```

:::gradysim.simulator.handler.assertion.assert_always_true_for_protocol
:::gradysim.simulator.handler.assertion.assert_eventually_true_for_protocol
:::gradysim.simulator.handler.assertion.assert_always_true_for_simulation
:::gradysim.simulator.handler.assertion.assert_eventually_true_for_simulation