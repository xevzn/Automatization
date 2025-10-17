================================================================================
🔎 Buscador inteligente de IPs en topología Cisco

Descripción:
Este script permite localizar la ubicación de un host en una red Cisco basada en VLANs,
siguiendo la ruta hacia la IP buscada sin necesidad de conectarse a todos los switches.

Funcionamiento general:
1. Se conecta inicialmente al switch gateway de la VLAN (configurado en INITIAL_DEVICE).
2. Obtiene la MAC asociada a la IP objetivo usando la tabla ARP del switch.
3. Busca la MAC en la tabla de direcciones MAC del switch:
   - Si el puerto corresponde a un host final, guarda la información en un CSV.
   - Si el puerto conecta a otro switch (uplink), utiliza CDP para identificar 
     al vecino y se conecta únicamente a ese switch, repitiendo el proceso recursivamente.
4. Evita conectarse a switches que no estén en la ruta hacia la MAC, permitiendo
   escalabilidad en topologías grandes.
5. Guarda los resultados en un archivo CSV con información detallada:
   - Fecha de la búsqueda
   - IP buscada
   - MAC del host
   - Switch donde se encontró
   - Puerto del switch
   - Dispositivo conectado al puerto
   - IP del dispositivo conectado

Requisitos:
- Librerías Python: netmiko
- Switches Cisco IOS accesibles vía SSH
- Credenciales correctas en DEVICE_CREDENTIALS

Notas:
- El script asume que la IP buscada está en una VLAN conocida y que los switches
  usan CDP para identificar vecinos.
- Para hosts cuya MAC no está aprendida en el switch inicial, se puede generar
  tráfico (ping) desde el host hacia la VLAN para que la MAC aparezca en la tabla.
- Funciona para topologías de múltiples switches, evitando exploración innecesaria 
  de todos los dispositivos.
================================================================================

Ejemplo de funcionamiento desde terminal de un dispositivo:

1.Busca la mac add del host.

    SW_CORE#sh ip arp 192.168.1.18
    Protocol  Address          Age (min)  Hardware Addr   Type   Interface
    Internet  192.168.1.18            0   f80d.ac59.366a  ARPA   Vlan10

2.Busca la mac add en la tabla mac address

    SW_CORE#show mac address-table address f80d.ac59.366a

        SW_CORE#show mac address-table address f80d.ac59.366a
            Mac Address Table
    -------------------------------------------

        Vlan    Mac Address       Type        Ports
    ----    -----------       --------    -----
    10    f80d.ac59.366a    DYNAMIC     Fa1/0/47

3.Para conocer si el puerto es un host o un switch
    SW_CORE#sh cdp neighbors fastEthernet1/0/47 detail 
    Capability Codes: R - Router, T - Trans Bridge, B - Source Route Bridge
                    S - Switch, H - Host, I - IGMP, r - Repeater, P - Phone,
                    D - Remote, C - CVTA, M - Two-port Mac Relay

    Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
    SW2.cisco.com    Fas 1/0/47        163              S I   WS-C3750- Fas 1/0/48




4.Ahora sabiendo que es un switch, buscamos su IP buscando SW2.cisco.com

    SW_CORE#sh cdp neighbors detail
    -------------------------
    Device ID: SW1.cisco.com
    Entry address(es):
    IP address: 192.168.1.11
    Platform: cisco WS-C3750-48P,  Capabilities: Switch IGMP
    Interface: FastEthernet1/0/48,  Port ID (outgoing port): FastEthernet1/0/48
    Holdtime : 147 sec

    Version :
    Cisco IOS Software, C3750 Software (C3750-IPSERVICESK9-M), Version 12.2(55)SE10, RELEASE SOFTWARE (fc2)
    Technical Support: http://www.cisco.com/techsupport
    Copyright (c) 1986-2015 by Cisco Systems, Inc.
    Compiled Wed 11-Feb-15 11:40 by prod_rel_team

    advertisement version: 2
    Protocol Hello:  OUI=0x00000C, Protocol ID=0x0112; payload len=27, value=00000000FFFFFFFF010221FF000000000000001C58B90580FF0000
    VTP Management Domain: 'cisco'
    Native VLAN: 10
    Duplex: full
    Management address(es):
    IP address: 192.168.1.11

    -------------------------
    Device ID: SW2.cisco.com
    Entry address(es):
    IP address: 192.168.1.12
    Platform: cisco WS-C3750-48P,  Capabilities: Switch IGMP
    Interface: FastEthernet1/0/47,  Port ID (outgoing port): FastEthernet1/0/48
    Holdtime : 144 sec

    Version :
    Cisco IOS Software, C3750 Software (C3750-IPSERVICESK9-M), Version 12.2(55)SE10, RELEASE SOFTWARE (fc2)
    Technical Support: http://www.cisco.com/techsupport
    Copyright (c) 1986-2015 by Cisco Systems, Inc.
    Compiled Wed 11-Feb-15 11:40 by prod_rel_team

    advertisement version: 2
    Protocol Hello:  OUI=0x00000C, Protocol ID=0x0112; payload len=27, value=00000000FFFFFFFF010221FF000000000000001C58956800FF0000
    VTP Management Domain: 'pod2.local'
    Native VLAN: 10
    Duplex: full
    Management address(es):
    IP address: 192.168.1.12

5. Una vez tenido la IP, volvemos al paso 1 pero ahora en SW2.cisco.com

    Se realiza el paso 1,2 
    Y luego se ejecuta SW2# show cdp neighbor Fa0/5 para saber si es host o switch, si no aparaece nada es un host.
