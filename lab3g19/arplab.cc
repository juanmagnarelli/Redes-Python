#include "node.h"
#include <arpa/inet.h>


// Formato de paquete ethernet
struct __attribute__((__packed__)) ether_hdr{
  MACAddress destination;                     // 6 bytes, Ethernet address of destination
  MACAddress source;                          // 6 bytes, Ethernet address of sender
  unsigned short type;                        // 2 bytes, Tipo
  unsigned char payload[PAYLOAD_LENGTH];      // 1500 bytes, Payload
};

// Formato de paquete ARP
struct __attribute__((__packed__)) arp_hdr{
  uint16_t hwd_type;
  uint16_t protocol_type;
  uint8_t hwd_leng;
  uint8_t protocol_leng;
  uint16_t opcode;
  MACAddress addr_hwd_source;
  IPAddress addr_protocol_source;
  MACAddress addr_hwd_dest;
  IPAddress addr_protocol_dest;
};


MACAddress BROADCAST_ADDR = {255,255,255,255,255,255};

// Agregamos una nueva direccion en la tabla
void Node::add_mac(MACAddress mac, IPAddress ip){
      memcpy(arp_table[ip[3]], mac, sizeof(MACAddress));
      return;
}

int Node::send_to_ip(IPAddress ip, void *data) {

  struct ether_hdr frame;
  if(arp_table[ip[3]][0] == '\0'){
    // La ip no esta en la tabla

    struct arp_hdr arp_pack;
    //Creamos el pack arp
    arp_pack.hwd_type = htons(ETHERNET);                                 // solicitud ethernet
    arp_pack.protocol_type = htons(IPv4);                                // pack tipo ipv4
    arp_pack.hwd_leng = LENGTH_MAC;                                      // largo de una mac
    arp_pack.protocol_leng = LENGTH_IPV4;                                // largo de una ip
    arp_pack.opcode = htons(REQUEST);                                    // solicitud de mac
    get_my_mac_address(arp_pack.addr_hwd_source);                        // mi mac
    get_my_ip_address(arp_pack.addr_protocol_source);                    // mi ip

    // Copia los primeros n bytes BROADCAST_ADDR a arp_pack.addr_hwd_dest
    memcpy(arp_pack.addr_hwd_dest, BROADCAST_ADDR, sizeof(MACAddress));  //enviar a todos
    memcpy(arp_pack.addr_protocol_dest, ip, sizeof(IPAddress));          // ip buscada

    //Creamos el pack ethernet
    memcpy(frame.destination, BROADCAST_ADDR, sizeof(MACAddress));
    get_my_mac_address(frame.source);
    frame.type = htons(ARP);                                            // pack tipo arp
    memcpy(frame.payload, &arp_pack, sizeof(frame.payload));

    send_ethernet_frame(&frame);
    return 1;
  } else {
    // La ip y mac son conocidas
    memcpy(frame.destination, arp_table[ip[3]], sizeof(MACAddress));
    get_my_mac_address(frame.source);
    frame.type = htons(IPv4);
    memcpy(frame.payload, data, sizeof(frame.payload));
    send_ethernet_frame(&frame);
    return 0;
  }
}

void Node::receive_ethernet_frame(void *frame) {
  struct ether_hdr pack_frame;
  IPAddress ip_null = {0,0,0,0};

  // nuestra ip y mac
  IPAddress ip;
  MACAddress mac;
  get_my_mac_address(mac);
  get_my_ip_address(ip);
  unsigned short merge_flag = 0;

  memcpy(&pack_frame, frame, sizeof(struct ether_hdr));

  if(pack_frame.type == htons(ARP)){
    //El pack es tipo arp
    struct arp_hdr pack_arp;
    memcpy(&pack_arp, pack_frame.payload, sizeof(struct arp_hdr));
    if(pack_arp.hwd_type == htons(ETHERNET)){
      if(pack_arp.protocol_type == htons(IPv4)){
        if(memcmp(arp_table[pack_arp.addr_protocol_source[3]], ip_null, sizeof(MACAddress))){
          //Si esta la actualiza.
          add_mac(pack_arp.addr_hwd_source, pack_arp.addr_protocol_source);
          merge_flag = 1;
        }
        if(memcmp(pack_arp.addr_protocol_dest, ip, sizeof(IPAddress)) == 0){
          // Nos preguntan a nosotros
          if(!merge_flag) {
            add_mac(pack_arp.addr_hwd_source, pack_arp.addr_protocol_source);
	      }
          if(pack_arp.opcode == htons(REQUEST)){
            // Es un pedido de mac addr, Se crea el paquete arp de respuesta
            pack_arp.opcode = htons(REPLY);               // respuesta de mac
            memcpy(pack_arp.addr_hwd_dest, pack_arp.addr_hwd_source , sizeof(MACAddress)); //enviar al host que pidio
            memcpy(pack_arp.addr_protocol_dest, pack_arp.addr_protocol_source, sizeof(IPAddress)); // ip buscada
            memcpy(pack_arp.addr_hwd_source, mac,sizeof(MACAddress));
            memcpy(pack_arp.addr_protocol_source, ip ,sizeof(IPAddress));
            //Se crea el paquete ethernet de respuesta
            memcpy(pack_frame.destination, pack_arp.addr_hwd_dest, sizeof(MACAddress));
            memcpy(pack_frame.source, mac, sizeof(MACAddress));
            memcpy(pack_frame.payload, &pack_arp, sizeof(pack_frame.payload));

            //Se envia
            send_ethernet_frame(&pack_frame);
            return;
          } 
        } 
      }
    }
   } else if (memcmp(pack_frame.destination, mac, sizeof(MACAddress)) == 0){
      receive_ip_packet(&pack_frame.payload);
   } 
}

/*
 * Constructor de la clase. Poner inicialización aquí.
 */
Node::Node()
{
    timer = NULL;
    for (unsigned int i = 0; i != AMOUNT_OF_CLIENTS; ++i) {
        seen[i] = 0;
    }
    for (unsigned int i = 0; i < MAX_ADDR; i++) {
        for(unsigned int j = 0; j < 6; j++)
          arp_table[i][j] = '\0';
    }
}
