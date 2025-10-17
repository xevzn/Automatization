from netmiko import ConnectHandler
import re
import csv
from datetime import datetime


DEVICE_CREDENTIALS = {
    'username': 'cisco',
    'password': 'cisco99',
    'device_type': 'cisco_ios',
    'secret': 'cisco'
}

# Dispositivo inicial (gateway VLAN 10)
INITIAL_DEVICE = {'host': '192.168.1.1', **DEVICE_CREDENTIALS}

CSV_FILENAME = 'buscador_ip_resultados.csv'


# ==============================================
# Función para guardar resultados en CSV
# ==============================================
def write_to_csv(data):
    fieldnames = ['Fecha', 'IP Buscada', 'MAC', 'Switch', 'Puerto', 'Dispositivo Conectado', 'IP Dispositivo']
    file_exists = False
    try:
        with open(CSV_FILENAME, 'r', newline='') as f:
            file_exists = f.readline() != ''
    except FileNotFoundError:
        pass

    with open(CSV_FILENAME, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)


# ==============================================
# Función recursiva que busca la MAC en la red
# ==============================================
def buscar_mac_en_switch(device, mac_address, ip_objetivo, visitados=None):
    if visitados is None:
        visitados = set()

    host = device['host']
    if host in visitados:
        return None
    visitados.add(host)

    print(f"\n[+] Conectando a {host}...")
    try:
        with ConnectHandler(**device) as net_connect:
            net_connect.enable()

            # Intentar búsqueda específica
            mac_output = net_connect.send_command(f"show mac address-table | include {mac_address}")
            if not mac_output.strip():
                print(f"⚠ No se encontró directamente la MAC {mac_address} en {host}. Buscando en toda la tabla...")
                mac_output = net_connect.send_command("show mac address-table dynamic")

            if mac_address not in mac_output:
                print(f"❌ MAC {mac_address} no encontrada en {host}.")
                return None

            # Intentar extraer el puerto
            port_match = re.search(r"(?:Gi|Fa|Te|Eth|GigabitEthernet|FastEthernet|TenGigabitEthernet)[0-9/]+", mac_output)
            if not port_match:
                print(f"⚠ No se pudo identificar el puerto de la MAC en {host}.")
                print("DEBUG salida MAC:\n", mac_output[:300])
                return None

            port = port_match.group(0)
            print(f"✅ MAC {mac_address} encontrada en {host}, puerto {port}")

            # Buscar si ese puerto tiene vecino
            cdp_output = net_connect.send_command(f"show cdp neighbor {port} detail")
            lldp_output = net_connect.send_command(f"show lldp neighbor {port} detail")

            neighbor_name, neighbor_ip = None, None
            if "System Name" in lldp_output:
                name_match = re.search(r"System Name:\s*(\S+)", lldp_output)
                ip_match = re.search(r"Management Address:\s*(\d{1,3}(?:\.\d{1,3}){3})", lldp_output)
                neighbor_name = name_match.group(1) if name_match else None
                neighbor_ip = ip_match.group(1) if ip_match else None
            elif "Device ID" in cdp_output:
                name_match = re.search(r"Device ID:\s*(\S+)", cdp_output)
                ip_match = re.search(r"IP address:\s*(\d{1,3}(?:\.\d{1,3}){3})", cdp_output)
                neighbor_name = name_match.group(1) if name_match else None
                neighbor_ip = ip_match.group(1) if ip_match else None

            # Si hay vecino, seguir hacia ese switch
            if neighbor_ip:
                print(f"➡ El puerto {port} conecta con {neighbor_name} ({neighbor_ip})")
                next_device = {'host': neighbor_ip, **DEVICE_CREDENTIALS}
                return buscar_mac_en_switch(next_device, mac_address, ip_objetivo, visitados)

            # Si no hay vecino, es el host final
            print(f"🎯 Host encontrado en {host}, puerto {port}")
            data = {
                'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'IP Buscada': ip_objetivo,
                'MAC': mac_address,
                'Switch': host,
                'Puerto': port,
                'Dispositivo Conectado': "Host final",
                'IP Dispositivo': ip_objetivo
            }
            write_to_csv(data)
            print("✅ Información guardada en el CSV.")
            return data

    except Exception as e:
        print(f"❌ Error al conectar con {host}: {e}")
        return None


# ==============================================
# Función principal: busca la IP en el gateway
# ==============================================
def buscar_ip(ip_objetivo):
    print(f"\nBuscando {ip_objetivo} desde el gateway {INITIAL_DEVICE['host']}...")
    try:
        with ConnectHandler(**INITIAL_DEVICE) as net_connect:
            net_connect.enable()
            arp_output = net_connect.send_command(f"show ip arp | include {ip_objetivo}")
            mac_match = re.search(r"(\w{4}\.\w{4}\.\w{4})", arp_output)
            if not mac_match:
                print(f"❌ No se encontró la IP {ip_objetivo} en la tabla ARP del gateway.")
                print("DEBUG salida ARP:\n", arp_output)
                return
            mac_address = mac_match.group(1)
            print(f"✅ MAC asociada a {ip_objetivo}: {mac_address}")
    except Exception as e:
        print(f"❌ Error al conectar con el gateway: {e}")
        return

    # Buscar la MAC en la red siguiendo los enlaces
    resultado = buscar_mac_en_switch(INITIAL_DEVICE, mac_address, ip_objetivo)
    if not resultado:
        print("❌ No se pudo ubicar la IP en la topología.")


# ==============================================
# Main loop
# ==============================================
def main():
    print("=" * 60)
    print("🔎 Buscador inteligente de IPs en topología Cisco")
    print("=" * 60)
    while True:
        ip_objetivo = input("Ingrese la IP a buscar (ENTER para salir): ").strip()
        if not ip_objetivo:
            print("Saliendo del programa...")
            break
        buscar_ip(ip_objetivo)
        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()


'''
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

'''