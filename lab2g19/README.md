## Servidor paralelo, implementacion con poll

###Funcionamiento del servidor

Al iniciar el servidor se crea un diccionario **clients** (descriptor de archivo, conexion) en el cual se va guardar la conexión de cada cliente. 

Y un objeto **poll**  que  va permitir diferenciar cada cliente a partir de su ***fd*** y su operación o evento que tiene(POLLIN, POLLOUT, POLLHUP)

Primero se registra el servidor con el evento de tipo POLLIN en el poll, luego cada vez que se conecte un cliente nuevo, se acepta la conexion, se registra en el objeto poll como evento POLLIN, y se crear su respectiva conexion almacenandola en **clients**.

Cuando un cliente tiene algun evento de cualquier tipo, el servidor va responder segun el caso, si un evento es :
		
POLLIN Esto indica que el cliente quiere enviar un pedido al servidor. Este toma el objeto Connection asociado al cliente del diccionario clients y llama a ***handle_input()*** el cual se va encargar de tomar el pedido y almacenarlo en un buffer **input**, luego estos pedidos almacenados en el buffer input se van procesando de la misma manera que en el laboratorio anterior, separándolos en cada EOL, viendo si estan correctamente formulados, llamanado a la función pertinente en ese caso.

POLLOUT Los eventos de este tipo indican que el servidor tiene elementos para ser enviados al cliente. Se procede haciendo un llamado a ***handle_output()***, aquí se verificará primero que generador tenga asignado un objeto generador, lo que indica que se esta haciendo un ***get_slice*** o ***get_file_listing***. Se procede a hacer una iteración sobre el objeto con next() para enviar el siguiente bloque, asignándolo al buffer output. Posteriormente handle_output() vérifica que hayan elemenentos en el buffer de salida e intenta hacer un send() al cliente. Todas las funciones de connection agregan sus datos de salida al buffer output 

POLLHUP A esta máscara no le damos el uso explícito que se le da en Select, es decir, no le asignamos este tipo de evento al objeto poll. Se la utiliza únicamente para saber que un cliente se ha desconectado. Se proceda a desregistrar el cliente de poll, cerrar el socket y eliminar la conneción del diccionario de clientes.

***Event()*** se encarga de modificar los eventos, es decir, si un evento paso a ser POLLIN, POLLOUT, POLLHUP. Esta función se llama en serve() y nos devolverá la máscara a asociar a esa conneción en poll.

