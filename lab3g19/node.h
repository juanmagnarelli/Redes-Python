#ifndef __NODE_H
#define __NODE_H

#include <omnetpp.h>
#include "EtherFrame.h"

using omnetpp::cSimpleModule;
using omnetpp::cMessage;

#define AMOUNT_OF_CLIENTS 6
typedef unsigned char IPAddress[4];
typedef unsigned char MACAddress[6];

#define MAX_ADDR 256        // Maxima cantidad de direcciones ip
#define IPv4 0x0800         // Paquete tipo ipv4
#define ARP  0x0806         // Paquete tipo ARP
#define ETHERNET 0x0001     // Tipo ethernet
#define LENGTH_MAC 6        // Longitud MAC
#define LENGTH_IPV4 4       // Longitud ipv4
#define REQUEST 1           // Mensaje de solicitud
#define REPLY 2             // Mensaje de repuesta
#define PAYLOAD_LENGTH 1500 // Tamaño del mensaje

class Node : public cSimpleModule
{
  private:
    cMessage *timer;
    unsigned char seen[AMOUNT_OF_CLIENTS];
    MACAddress arp_table[MAX_ADDR];

  public:
    Node();
    virtual ~Node();

  protected:
    virtual void initialize();
    virtual void handleMessage(cMessage *msg);
    virtual void updateDisplay(void);

    /*
     * To implement!
     * Try to send `data` to a specified `ip`.
     * `data` is a buffer with IP_PAYLOAD_SIZE bytes.
     * If the MAC address for that IP is unknown, an ARP request should be sent.
     * Returns 0 on success and non-zero if it's necessary to retry later (because
     * ARP is figuring out the correct MAC address).
     */
    virtual int send_to_ip(IPAddress ip, void *data);

    /*
     * To implement!
     * Handle a packet.
     * If it's an ARP packet: Processes, if it's a regular data
     * packet then it forwards the data to the network layer using
     * receive_ip_packet.
     * `frame` is a buffer with ETHERFRAME_SIZE bytes.
        An ethernet frame has:
         - 6 bytes destination MAC
         - 6 bytes source MAC
         - 2 bytes type
         - 46-1500 bytes of data payload (in this application is always 1500)
        Total max size: 1514 bytes

     */
    virtual void receive_ethernet_frame(void *frame);

    /*
     * Delivers the `data` buffer with IP_PAYLOAD_SIZE bytes to the network layer
     * as it was delivered to send_to_ip in the node that originated the message.
     */
    virtual void receive_ip_packet(void *data);

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
    virtual void send_ethernet_frame(void *frame);

    virtual void add_mac(MACAddress mac, IPAddress ip);

    /*
     * Assigns this node's IP addresss into `ip`.
     */
    virtual void get_my_ip_address(IPAddress ip);

    /*
     * Assigns this node's MAC addresss into `mac`.
     */
    virtual void get_my_mac_address(MACAddress mac);
};

#endif
