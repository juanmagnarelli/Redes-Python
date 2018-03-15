import time
import array
import logging
from constants import KEEP, DROP, DONTKNOW, MAXSEQ


def istcp(p):
    """
    Return true if 'p' represents a packet TCP/IP, and false otherwise
    """
    if 'IP' in p and 'TCP' in p:
        return True
    return False


def pkey(p):
    src = (p['IP'].src, p['TCP'].sport)
    dst = (p['IP'].dst, p['TCP'].dport)
    if src > dst:
        src, dst = dst, src
    return (src, dst)


class TCPState:
    """
    Lists each of the TCP states in a TCP connection
    """
    closed = 'Closed'
    listen = 'Listen'
    synReceived = 'SynReceived'
    synSent = 'SynSent'
    established = 'Established'
    finWait1 = 'FinWait1'
    finWait2 = 'FinWait2'
    closing = 'Closing'
    timeWait = 'TimeWait'
    closeWait = 'CloseWait'
    lastAck = 'LastAck'


class StateTransitionDiagram:
    """
    Represents a state transition diagram.
    The states are lists by TCPState class.
    A TCP connection progresses from one state to another in response
    to events. The events are the user calls, OPEN, SEND, RECEIVE, CLOSE;
    the incoming segments, particularly those containing
    the SYN, ACK, RST and FIN flags
    """
    def __init__(self, address, role, state):
        """
        address represents a host address
        role represents a host role (Client or Server)
        state represents the TCP state
        trace represents a sequence of segments and state changes, where
        each element of trace follow the format {"src": src, "dst": dst,
        "flags": flags, "state": state, "new_state": new_state}
        """
        self.address = address
        self.role = role
        self.state = state
        self.trace = []

    def transition(self, src, dst, flags):
        """
        Update state transition diagram, based on
        src, dst, flags, address, and state. View rfc793 (figure 6)
        src, dst, and flags represents field of a TCP segment header
        """
        new_state = self.state
        if dst == self.address:
            # Update state transition diagram: Case received messages
            # Host en listen recibe un pedido de conexion y pasa SynReceived        
            if self.state == TCPState.listen and "S" in flags:
                new_state = TCPState.synReceived
            # Host en SynReceived recibe RST pasa a listen            
            elif self.state == TCPState.synReceived and "R" in flags:
                new_state = TCPState.listen
            # Host en SynReceived recibe ACK pasa a establecido
            elif self.state == TCPState.synReceived and "A" in flags:
                new_state = TCPState.established
            # Host en established y recibe FIN pasa closewait
            elif self.state == TCPState.established and "F" in flags:
                new_state = TCPState.closeWait
            # Host mando un SYN y recibe SYN+ACK
            elif self.state == TCPState.synSent and "SA" in flags:
                new_state = TCPState.established
            # Host recibe FIN+ACK pasa timewait
            elif self.state == TCPState.finWait1 and "FA" in flags:
                new_state = TCPState.timeWait
            # Host recibe FIN pasa closing
            elif self.state == TCPState.finWait1 and "F" in flags:
                new_state = TCPState.closing
            # Host en finWait1 y recibe ACK pasa finWait2
            elif self.state == TCPState.finWait1 and "A" in flags:
                new_state = TCPState.finWait2
            # Host recibe ACK pasa timewait
            elif self.state == TCPState.closing and "A" in flags:
                new_state = TCPState.timeWait
            # Host en finwait2 y recibe un FIN+ACK pasa timewait
            elif self.state == TCPState.finWait2 and "F" in flags:
                new_state = TCPState.timeWait
            # Host en lastAck y recibe ACK de liberacion
            elif self.state == TCPState.lastAck and "A" in flags:
                new_state = TCPState.closed 
	
        elif src == self.address:
            # Update state transition diagram: Case sent messages
            # Host solicita establecer una conexion             
            if self.state == TCPState.closed and "S" in flags:
                new_state = TCPState.synSent
            # Host ejecuta primitiva CLOSED y manda FIN
            elif self.state == TCPState.established and "F" in flags:
                new_state = TCPState.finWait1
            # Host recibe el SYN+ACK y manda ACK
            elif self.state == TCPState.synSent and "A" in flags:
                new_state = TCPState.established
            # Host llama close() y manda FIN
            elif self.state == TCPState.synReceived and "F" in flags:
                new_state = TCPState.finWait1
            # Host recibe FIN y manda FIN+ACK
            elif self.state == TCPState.closeWait and "F" in flags:
                new_state = TCPState.lastAck 

        self.state = new_state

    def get_state(self):
        return self.state

    def set_address(self, address):
        self.address = address

    def add(self, segment):
        self.trace.append(segment)

    def get_trace(self):
        return self.trace


class Connection_status:
    """
    A class that has to be able to answer about the status of a TCP connection
    by watching the packets of that conversation.
    A connection cannot be established and closed at the same time,
    nevertheless a connection can be in none of those state.
    It's guaranteed that every packet delivered will be from src->dst
    or dst->src where src and dst are the same for all packets.
    """

    def __init__(self, src, dst, std_enabled):
        """
        src and dst are 2-uples with ip and port.
        The ip is a string, and the port is an integer.
        Every single packet delivered to this class (through add) is
        from src to dst or from dst to src.
        """
        self.est = False
        self.clo = False
        if src > dst:
            src, dst = dst, src
        self.src = src
        self.dst = dst
        self.std_enabled = std_enabled
        self.std_started = False
        self.client_std = None
        self.server_std = None
        self.traces = []

    def add(self, p):
        """
        Add packet p for consideration.
        p is an instance of scapy.packet.Packet.

        PRE: p goes from self.src to self.dst or from self.dst to self.src
        """
        assert self.src, self.dst == pkey(p)

        flags = p.sprintf("%TCP.flags%")
        if not self.clo:
            if not self.est and flags == "S":
                self.est = True
            elif "F" in flags:
                self.est = False
                self.clo = True
        if self.std_enabled:
            self.add_trace(p)

    def add_trace(self, p):
	"""
        Add a new segment to traces
        """
        flags = p.sprintf("%TCP.flags%")
        src = p.sprintf("%IP.src%:%TCP.sport%")
        dst = p.sprintf("%IP.dst%:%TCP.dport%")
        if not self.std_started:
            if flags == "S":
                self.client_std = StateTransitionDiagram(src, "Client",
                                                         TCPState.closed)
                self.server_std = StateTransitionDiagram(dst, "Server",
                                                         TCPState.listen)
                logging.debug("STDs starded for client(src)={0}, " +
                              "server(dst)={1}".format(src, dst))
                self.std_started = True

        if self.std_started:
            segment = {"src": src, "dst": dst, "flags": flags}
            segment["client_state"] = self.client_std.get_state()
            segment["server_state"] = self.server_std.get_state()
            self.client_std.transition(src, dst, flags)
            self.server_std.transition(src, dst, flags)
            segment["client_new_state"] = self.client_std.get_state()
            segment["server_new_state"] = self.server_std.get_state()
            logging.debug("Adding trace: " + str(segment))
            self.traces.append(segment)

    def established(self):
        """
        Returns True if the connection has been established.
        Returns False otherwise.
        """
        return self.est

    def closed(self):
        """
        Returns True if the connection has been closed.
        Returns False otherwise.
        """
        return self.clo

    def get_traces(self):
        return [self.traces]


class Reassembler:
    """
    The reassembler recieves (through add) all the packages involved
    in a TCP connection and it is its task to assamble the payload of
    the source->destination data stream (not the other way).
    """

    def __init__(self, src, dst):
        """
        src and dst are (ip, port) tuples.
        ip is a string and port is an integer.
        Every single packet given (through add) will belong to that
        particular TCP conversation between source and destination.
        All packages will be from source to destination, or from
        destination to source.
        """
        self.payload = array.array('B')
        self.src = src
        self.dst = dst
        self.ignore = False
        self.seq_start = None
        self.dic = {}

    def add(self, p):
        """
        This function should incrementally create the
        src->dst payload from each p given.

        PRE: p is an instance of scapy.packet.Packet.
        It's safe to assume that IP and TCP layers are present.
        Raw layer may or may not be present.
        Given the source and destination given in __init__ p
        will be from source to destination, or from
        destination to source and nothing else.
        Packets given to this method will be from established
        connections only (not handshakes and such).
        """
        assert (self.src, self.dst) == pkey(p) or \
               (self.dst, self.src) == pkey(p)
        src = (p["IP"].src, p["TCP"].sport)
        if self.ignore or (self.src != src) or "Raw" not in p:
            return
        if p["TCP"].seq not in self.dic:
        	self.dic[p["TCP"].seq] = p["Raw"].load
        return

    def get_payload(self):
        """
        Returns the payload gathered so far.
        If self.is_closed() then the payload must be the complete
        source->destination data stream.
        """
	self.payload = array.array('B')
        res = sorted(self.dic.items(), key=lambda x: x[0])
        for key, elem in res:
        	self.payload.fromstring(elem)
        return self.payload

    def ignore_the_rest(self):
        """
        Releases all resources used and starts to ignore every following
        packets given through add.
        """
        self.ignore = True
        del self.payload


class Connection_tracker:

    def __init__(self, key, std_enabled):
        src, dst = key
        self.status = Connection_status(src, dst, std_enabled)
        self.src = src
        self.dst = dst
        self.pairs = [(src, dst), (dst, src)]
        self.rs = [Reassembler(*x) for x in self.pairs]
        self.starttime = time.time()
        self.packettime = None
        self.useful = [DONTKNOW for x in self.pairs]
        self.finalized_connection = False

    def add(self, p):
        self.status.add(p)
        if self.status.established():
            for r in self.rs:
                r.add(p)
            self.packettime = time.time()

    def classify(self, clas):
        for i in xrange(len(self.rs)):
            if self.useful[i] == DONTKNOW:
                self.useful[i] = clas(self.rs[i].get_payload())
                if self.useful[i] == DROP:
                    self.rs[i].ignore_the_rest()

    def get_useful_payloads(self):
        for pair, r, useful in zip(self.pairs, self.rs, self.useful):
            if useful == KEEP:
                yield r.get_payload()

    def get_traces(self):
        return self.status.get_traces()

    def is_closed(self):
        return self.status.closed()

    def lifetime(self):
        return time.time() - self.starttime

    def activetime(self):
        return time.time() - self.packettime


class Connection_keeper:
    """
    Used to keep track TCP conversatios.
    It classifies conversations as useful or not
    Packets can be stored and assembled or dropped in expectation
    of the end of conection.
    """

    def __init__(self, classifier, action_callback, tracer=None):
        """
        classifier takes a conection and returns KEEP, DROP or DONTKNOW.
        action_callback gets called every time a KEEP conection it is
        closed.
        tracer gets called every time a connnection it is closed.
        """
        self.trackers = {}
        self.classifier = classifier
        self.callback = action_callback
        self.tracer = tracer
        self.std_enabled = tracer is not None

    def add(self, p):
        """
        Process the packet p.
        """
        if not istcp(p):
            return
        key = pkey(p)
        if key not in self.trackers:
            tracker = Connection_tracker(key, self.std_enabled)
            self.trackers[key] = tracker
        else:
            tracker = self.trackers[key]
        tracker.add(p)
        tracker.classify(self.classifier)

        if tracker.is_closed() and not tracker.finalized_connection:
            src = p.sprintf("%IP.src%:%TCP.sport%")
            dst = p.sprintf("%IP.dst%:%TCP.dport%")
            tracker.finalized_connection = True
            logging.info("Successful Connection finalized for pair " +
                         "src={0}, dst={1}".format(src, dst))

    def save(self):
        """
        Write payload extracted and generared traces
        to files for trackers with finalized connection
        """
        for key in self.trackers.keys():
            tracker = self.trackers[key]
            if tracker.finalized_connection:
                for payload in tracker.get_useful_payloads():
                    self.callback(payload)
                if self.std_enabled:
                    for trace in tracker.get_traces():
                        self.tracer(trace)
            del self.trackers[key]

    def check_timeouts(self, activity_thres, life_thres=0):
        """
        Discards connections based on given timeouts.
        activity_thres is seconds since last packet.
        life_thres is seconds since the connection exists.
        """
        for key, tracker in self.trackers.iteritems():
            if activity_thres < tracker.activetime():
                del self.trackers[key]
        if life_thres != 0:
            for key, tracker in self.trackers.iteritems():
                if life_thres < tracker.lifetime():
                    del self.trackers[key]

    def __len__(self):
        return len(self.trackers)
