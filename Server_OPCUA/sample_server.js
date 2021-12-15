/*global require,setInterval,console */
const opcua = require("node-opcua");
const os = require("os");
const zmq = require("zeromq")

// TAMANHO DA PIZZA
let tamanhoPizza = 0;
// INICIAR PRODUCAO
let iniciarProd = 0;
let linhaStandby = 0;


async function run() {

    const sock = new zmq.Reply

    await sock.bind("tcp://*:5555")

    let recvTamanhoPizza = 0
    
    for await (const [msg] of sock) {
        tamanhoPizza = parseInt(msg, 10)
        await sock.send(recvTamanhoPizza)
    }
}
run()

// Let's create an instance of OPCUAServer
const server = new opcua.OPCUAServer({
    port: 4334, // the port of the listening socket of the server
    resourcePath: "/UA/RaspberryPi", // this path will be added to the endpoint resource name
     buildInfo : {
        productName: "ServidorOPCUA",
        buildNumber: "7658",
        buildDate: new Date(2014,5,2)
    }
});

function post_initialize() {
    console.log("initialized");
    function construct_my_address_space(server) {
    
        const addressSpace = server.engine.addressSpace;
        const namespace = addressSpace.getOwnNamespace();
    
        // declare a new object
        const device = namespace.addObject({
            organizedBy: addressSpace.rootFolder.objects,
            browseName: "RaspberryPi"
        });
        
        // emulate tamanhoPizza changing every 500 ms
/*       
        setInterval(function(){ 
            if(tamanhoPizza == 0)
                tamanhoPizza = 1; 
            else 
                if(tamanhoPizza == 1)
                    tamanhoPizza = 2;
                else 
                    if(tamanhoPizza == 2)
                        tamanhoPizza = 3; 
                    else
                        if(tamanhoPizza == 3)
                            tamanhoPizza = 4; 
                        else
                            if(tamanhoPizza == 4)
                                tamanhoPizza = 0; 
            }, 1500);
*/        
        namespace.addVariable({
            componentOf: device,
            browseName: "TamanhoPizza",
            dataType: "Double",
            //value: new opcua.Variant({dataType: opcua.DataType.Double, value: tamanhoPizza })
            value: {
                get: function () {
                    return new opcua.Variant({dataType: opcua.DataType.Double, value: tamanhoPizza });
                }
            }
        });
        
        
        
        // emulate tamanhoPizza changing every 500 ms
        //setInterval(function(){  iniciarProd+=1; }, 500);
        
        //namespace.addVariable({
            //componentOf: device,
            //browseName: "IniciarProd",
            //dataType: "Double",
            //value: new opcua.Variant({dataType: opcua.DataType.Double, value: iniciarProd })
            ////value: {
                ////get: function () {
                    ////return new opcua.Variant({dataType: opcua.DataType.Double, value: iniciarProd });
                ////}
            ////}
        //});
        
        //namespace.addVariable({
            //componentOf: device,
            //browseName: "LinhaStandby",
            //dataType: "Double",
            //value: new opcua.Variant({dataType: opcua.DataType.Double, value: linhaStandby })
            ////value: {
                ////get: function () {
                    ////return new opcua.Variant({dataType: opcua.DataType.Double, value: iniciarProd });
                ////}
            ////}
        //});
        
        
        /**
         * returns the percentage of free memory on the running machine
         * @return {double}
         */
        function available_memory() {
            // var value = process.memoryUsage().heapUsed / 1000000;
            const percentageMemUsed = os.freemem() / os.totalmem() * 100.0;
            return percentageMemUsed;
        }
        namespace.addVariable({
        
            componentOf: device,
        
            nodeId: "s=free_memory", // a string nodeID
            browseName: "MemoriaDisponivel",
            dataType: "Double",    
            value: {
                get: function () {return new opcua.Variant({dataType: opcua.DataType.Double, value: available_memory() });}
            }
        });
    }
    
    
    construct_my_address_space(server);
    server.start(function() {
        console.log("Server is now listening ... ( press CTRL+C to stop)");
        console.log("port ", server.endpoints[0].port);
        const endpointUrl = server.endpoints[0].endpointDescriptions()[0].endpointUrl;
        console.log(" the primary server endpoint url is ", endpointUrl );
    });
}
server.initialize(post_initialize);
