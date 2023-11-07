"""
The encapsulator module is a middle-man between protocols and environments. One of GrADyS-SIM TNG's features is the
construction of protocols that can be used in different environments without changes to their code. These environments
are called execution modes. Protocols are wrapped in encapsulators that handle the effects of the environment on the
protocol and are injected with provider instances that provide them with the necessary tools to interact with the
environment.

This module provides encapsulators that enable users to run their protocols inside a python simulation
([prototype-mode][]), integrated with a realistic network simulator OMNeT++ ([integrated-mode][]) and, in the future,
connected to real-life nodes.

All encapsulators implement the [IEncapsulator][gradysim.encapsulator.interface.IEncapsulator] interface.
"""