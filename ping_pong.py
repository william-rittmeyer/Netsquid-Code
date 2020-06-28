import netsquid as ns
from netsquid.nodes import Node
node_A = Node(name="A")
node_B = Node(name="B")

from netsquid.components.models import DelayModel

class PingPongDelayModel(DelayModel):
    def __init__(self, speed_of_light_fraction=0.9, standard_deviation=0.05):
        super().__init__()
        # (the speed of light is about 300,000 km/s)
        self.properties["speed"] = speed_of_light_fraction * 3e5
        self.properties["std"] = standard_deviation
        self.required_properties = ['length']  # in km

    def generate_delay(self, **kwargs):
        avg_speed = self.properties["speed"]
        std = self.properties["std"]
        # The 'rng' property contains a random number generator
        # We can use that to generate a random speed
        speed = self.properties["rng"].normal(avg_speed, avg_speed * std)
        delay = 1e9 * kwargs['length'] / speed  # in nanoseconds
        return delay

from netsquid.components import QuantumChannel

atl_2_nyc = 1200 #distance from ATL to NYC in km

distance = atl_2_nyc / 1000  # default unit of length in channels is km
delay_model = PingPongDelayModel()
channel_1 = QuantumChannel(name="qchannel[A to B]",
                           length=distance,
                           models={"delay_model": delay_model})
channel_2 = QuantumChannel(name="qchannel[B to A]",length=distance,
                           models={"delay_model": delay_model})

from netsquid.nodes import DirectConnection

connection = DirectConnection(name="conn[A|B]",
                              channel_AtoB=channel_1,
                              channel_BtoA=channel_2)
node_A.connect_to(remote_node=node_B, connection=connection,
                     local_port_name="qubitIO", remote_port_name="qubitIO")





from netsquid.protocols import NodeProtocol

class PingPongProtocol(NodeProtocol):
    def __init__(self, node, observable, qubit=None):
        super().__init__(node)
        self.observable = observable
        self.qubit = qubit
        # Define matching pair of strings for pretty printing of basis states:
        self.basis = ["|0>", "|1>"] if observable == ns.Z else ["|+>", "|->"]

    def run(self):
        if self.qubit is not None:
            # Send (TX) qubit to the other node via port's output:
            self.node.ports["qubitIO"].tx_output(self.qubit)
        while True:
            # Wait (yield) until input has arrived on our port:
            yield self.await_port_input(self.node.ports["qubitIO"])
            # Receive (RX) qubit on the port's input:
            message = self.node.ports["qubitIO"].rx_input()
            qubit = message.items[0]
            meas, prob = ns.qubits.measure(qubit, observable=self.observable)
            print(f"{ns.sim_time():5.1f}: {self.node.name} measured "
                  f"{self.basis[meas]} with probability {prob:.2f}")
            # Send (TX) qubit to the other node via connection:
            self.node.ports["qubitIO"].tx_output(qubit)

qubits = ns.qubits.create_qubits(1)
A_protocol = PingPongProtocol(node_A, observable=ns.Z, qubit=qubits[0])
B_protocol = PingPongProtocol(node_B, observable=ns.X)

A_protocol.start()
B_protocol.start()
run_stats = ns.sim_run(duration=100000)
print(run_stats)
