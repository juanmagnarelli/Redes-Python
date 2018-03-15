#ifndef _ETHERFRAME_H_
#define _ETHERFRAME_H_

#include <omnetpp.h>
#include "EtherFrame_m.h"
#define ETHERFRAME_SIZE 1514
#define IP_PAYLOAD_SIZE 1500


class EtherFrame : public EtherFrame_Base
{
  public:
    EtherFrame(const char *name=NULL) : EtherFrame_Base(name) {}
    EtherFrame(const EtherFrame& other) : EtherFrame_Base(other) {}
    EtherFrame& operator=(const EtherFrame& other) {
        EtherFrame_Base::operator=(other);
        return *this;
    }
    virtual EtherFrame *dup() const {
        return new EtherFrame(*this);
    }

    void setFrame(const void *data, const unsigned int size) {
        const char *bytes = reinterpret_cast<const char *>(data);
        for (unsigned int i = 0; i != size; ++i) {
            setData(i, bytes[i]);
        }
    }

    void getFrame(void *data) {
        char *bytes = reinterpret_cast<char *>(data);
        for (unsigned int i = 0; i != ETHERFRAME_SIZE; ++i) {
            bytes[i] = getData(i);
        }            
    }
};


Register_Class(EtherFrame);

#endif // _ETHERFRAME_H_
