#include <string.h>
#include <omnetpp.h>

using namespace omnetpp;

class Hub : public cSimpleModule
{
  protected:
    virtual void initialize();
    virtual void handleMessage(cMessage *msg);
};
Define_Module(Hub);


void Hub::initialize()
{
}


void Hub::handleMessage(cMessage *msg)
{
    int ngates = gateSize("out");
    int ignore = msg->getArrivalGate()->getIndex();
    for (int gate = 0; gate < ngates; ++gate) {
        if (gate != ignore) {
            cMessage *copy = msg->dup();
            send(copy, "out", gate);
        }
    }
    delete msg;
}
