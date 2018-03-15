#include "node.h"

using namespace omnetpp;

Define_Module(Node);
static void ip_from_index(unsigned char i, IPAddress ip);
static void mac_from_index(unsigned char i, MACAddress mac);


/*
 * Delivers the `data` buffer with IP_PAYLOAD_SIZE bytes to the network layer
 * as it was delivered to send_to_ip in the node that originated the message.
 */
void Node::receive_ip_packet(void *data){
    unsigned char sender, destination;
    sender = ((unsigned char *) data)[0];
    destination = ((unsigned char *) data)[1];
    if ((int) par("myindex") == destination) {
        if (!seen[sender]) {
            bubble("New host knows my IP!");
        }
        seen[sender] = 1;
    } else {
        seen[sender] = 0;
        EV << "Dropping invalid network layer package because: Data was addressed to another host\n";
    }
}


/*
 * Sends a frame through ethernet. `frame` is a buffer with ETHERFRAME_SIZE
 * bytes containing the frame to be sent.
    An ethernet frame has:
     - 6 bytes destination MAC
     - 6 bytes source MAC
     - 2 bytes type
     - 46-1500 bytes of data payload (in this application is always 1500)
    Total max size: 1514 bytes

 */
void Node::send_ethernet_frame(void *frame) {
    EtherFrame *msg = new EtherFrame;
    msg->setFrame(frame, ETHERFRAME_SIZE);
    send(msg, "out");
}


/*
 * Assigns this node's IP addresss into `ip`.
 */
void Node::get_my_ip_address(IPAddress ip) {
    ip_from_index(par("myindex"), ip);
}


/*
 * Assigns this node's MAC addresss into `mac`.
 */
void Node::get_my_mac_address(MACAddress mac) {
    mac_from_index(par("myindex"), mac);
}


Node::~Node()
{
    cancelAndDelete(timer);
}


void Node::initialize()
{
    simtime_t delay = par("delayTime");
    timer = new cMessage("event");
    scheduleAt(simTime() + delay, timer);
    if (getEnvir()->isGUI()) {
        updateDisplay();
    }
}

void Node::handleMessage(cMessage *event)
{
    char frame[ETHERFRAME_SIZE];
    EtherFrame *msg;
    IPAddress destination;
    long i = 0;
    int myindex = par("myindex");
    simtime_t delay = par("delayTime");
    if (event==timer)
    {
        i = myindex;
        while (i == myindex) {
            i = (random() % AMOUNT_OF_CLIENTS);
        }
        ip_from_index(i, destination);
        frame[0] = myindex;
        frame[1] = i;
        send_to_ip(destination, (void *) frame);
        scheduleAt(simTime() + delay, timer);
    } else {
        msg = (EtherFrame *) event;
        msg->getFrame(frame);
        receive_ethernet_frame(frame);
        if (getEnvir()->isGUI()) {
            updateDisplay();
        }
        delete event;
    }
}


static void ip_from_index(unsigned char i, IPAddress ip) {
    ip[0] = 192;
    ip[1] = 168;
    ip[2] = 1;
    ip[3] = i + 100;
}


static void mac_from_index(unsigned char i, MACAddress mac) {
    mac[0] = i + 1;
    mac[1] = i + 1;
    mac[2] = i + 1;
    mac[3] = i + 1;
    mac[4] = i + 1;
    mac[5] = i + 1;
}


void Node::updateDisplay(void)
{
    char buf[40];
    unsigned int i;
    unsigned int c = 0;
    for (i = 0; i != AMOUNT_OF_CLIENTS; i++) {
        if (seen[i]) {
            c += 1;
        }
    }
    sprintf(buf, "%i/%i", c, AMOUNT_OF_CLIENTS - 1);
    getDisplayString().setTagArg("t", 0, buf);
}
