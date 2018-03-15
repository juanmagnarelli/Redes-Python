simple Hub
{
    parameters:
        @display("i=device/hub");
    gates:
        input in[];
        output out[];
}

simple Node
{
    parameters:
        @display("i=device/pc");
        volatile double delayTime @unit(s) = exponential(2s);
        int myindex;
    gates:
        input in;
        output out;
}

simple Docente
{
    parameters:
        @display("i=device/pc");
        volatile double delayTime @unit(s) = exponential(2s);
        int myindex;
    gates:
        input in;
        output out;
}


network HubNetwork
{
    parameters:
        int numClients @prompt("Number of clients") = default(6);
    submodules:
        hub: Hub {
            gates:
                in[numClients];
                out[numClients];
        }
        node[3]: Node;
        docente[3]: Docente;
    connections:
        for i=0..2 {
            node[i].out --> {  delay = 10ms; } --> hub.in[i];
            node[i].in <-- {  delay = 10ms; } <-- hub.out[i];
        }
        for i=0..2 {
            docente[i].out --> {  delay = 10ms; } --> hub.in[i + 3];
            docente[i].in <-- {  delay = 10ms; } <-- hub.out[i + 3];
        }
}
