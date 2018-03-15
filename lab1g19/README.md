## Modelo cliente-servidor secuencial

### Funcionamiento del servidor

**Creación del socket servidor y configuraciones**

**Bind** Se define por donde se van a escuchar las peticiones del cliente, "enlazando" la direccion y el puerto.

**Listen** Cantidad de conexiones clientes que tendrá el servidor.

**Servidor encendido**

El servidor se pone en ejecución a la espera de una conexión cliente, cuando se acepta una conexión, se obtiene un socket cliente, con su dirección y puerto. Luego la función *handle()* es la encargada de manejar los request del cliente y enviar las correspondientes response.


**Mecanismo de buffering**

Definido en la función *receive()* que va leyendo los datos recibidos del cliente con *recv()* hasta que recibe un *EOL*, entonces corta en ese punto dejando en request el comando ingresado hasta el *\r\n* y en self.buffer deja todo lo que hay después del *EOL*. Luego retorna un comando a tratar. Si no se recive ningún dato del cliente entonces la conexión se pierde.

**Mecanismo generador para enviar datos**

Para evitar problemas de lectura de datos cuando se desean enviar archivos muy peasados, se creo una funcion block_generator, que va leyendo el archivo a enviar por bloques del mismo tamaño que usa la funcion send(), es decir, 4096 bytes. Se utiliza *yield* para lograrlo.

**Función get_slice**

Esta función se encarga de hacer send() del archivo requerido por el cliente. En primer lugar se hace un parseo de los datos que se exigen y se verifica que esté todo bien (Que el archivo exista, que el offset y el size esten dentro de los parámetros correctos). Luego se calculan la cantidad de paquetes de tamaño BUFSIZE (4096) que serán necesarios para enviar la totalidad del archivo. Esto lo hacemos dividiendo el tamaño total del envio sobre los bloques, agregando otro paquete si exite un resto. Aquí usamos la función arriba definida *block_generator*.

**Parseo de comando**

La función *parser_command* simplemente se encarga de verificar que los argumentos que se reciben del cliente cumplen con el protocolo. En caso de que lo requerido por el cliente este bien formulado, se prosigue con el llamado a la función correspondiente. En caso contrario se envia un mensaje detallando que tipo de error se cometió.


