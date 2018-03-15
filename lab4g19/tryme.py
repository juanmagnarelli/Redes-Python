from scapy.utils import PcapReader
import scapy.layers.inet
filename = "example.pcap"

xs = [x for x in PcapReader(filename)]
ys = [x for x in xs if "TCP" in x and "Raw" in x]
