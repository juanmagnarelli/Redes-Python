### Como almacenamos las direcciones Mac

Definimos una tabla que contiene la direcciones MAC de cada nodo ***arp_table[]*** en la red, usando como indice la direccion IP del nodo, al ser la direccion ip de clase C, podemos usar los ultimos 3 digitos como indice.

Usamos **htons()** en la funcion **send_to_ip()** y **ntohs()** en la funcion **receive_ethernet_frame()** para que comparar los campos con el mismo formato, ya sea big-endian o little-endian

Teniamos un error al correr el programa por que estabamos haciendo mal los memcpy y memcmp, esta fue la mayor dificultad.