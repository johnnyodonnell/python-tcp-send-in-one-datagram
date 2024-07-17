import socket

from lib.disable_auto_rst import disable
from lib.IP_Datagram import IP_Datagram
from lib.TCP_Segment import TCP_Segment
from lib.TCP_Flags import TCP_Flags



def get_response(sock, dst_port):
    while True:
        data = sock.recv(1024)
        ip_datagram = IP_Datagram(data)
        tcp_segment = ip_datagram.get_tcp_segment()
        if tcp_segment.get_dst_port() == dst_port:
            return ip_datagram

def establish_connection(
        sock, src_addr, dst_addr, src_port, dst_port):
    # Send Syn packet
    flags = TCP_Flags()
    flags.set_syn_flag(True)
    req_segment = TCP_Segment(src_port, dst_port, 0, 0, flags)
    sock.sendall(req_segment.get_bytes(src_addr, dst_addr))

    # Receive Syn-Ack
    res_dgram = get_response(sock, src_port)
    res_segment = res_dgram.get_tcp_segment()
    flags = res_segment.get_flags()
    if not flags.get_syn_flag():
        seq_num = res_segment.get_ack_num()
        ack_num = res_segment.get_seq_num()
        terminate_connection(
                sock, src_addr, dst_addr, src_port, dst_port, seq_num, ack_num)
        return establish_connection(
                sock, src_addr, dst_addr, src_port, dst_port)

    # Send Ack packet
    flags = TCP_Flags()
    flags.set_ack_flag(True)
    seq_num = res_segment.get_ack_num()
    ack_num = res_segment.get_seq_num() + 1
    req_segment = TCP_Segment(src_port, dst_port, seq_num, ack_num, flags)
    sock.sendall(req_segment.get_bytes(src_addr, dst_addr))

    return (seq_num, ack_num)

def terminate_connection(
        sock, src_addr, dst_addr, src_port, dst_port, seq_num, ack_num):
    # Send Fin packet
    flags = TCP_Flags()
    flags.set_fin_flag(True)
    # For some reason, closing the connection doesn't work without this
    flags.set_ack_flag(True)
    req_segment = TCP_Segment(src_port, dst_port, seq_num, ack_num, flags)
    sock.sendall(req_segment.get_bytes(src_addr, dst_addr))

    # Receive Fin-Ack
    res_dgram = get_response(sock, src_port)
    res_segment = res_dgram.get_tcp_segment()

    # Send Ack packet
    flags = TCP_Flags()
    flags.set_ack_flag(True)
    seq_num = res_segment.get_ack_num()
    ack_num = res_segment.get_seq_num() + 1
    req_segment = TCP_Segment(src_port, dst_port, seq_num, ack_num, flags)
    sock.sendall(req_segment.get_bytes(src_addr, dst_addr))

def send_in_one_datagram(dst_addr, dst_port, payload):
    src_port = 55555

    # Needed for preventing OS from resetting TCP connection
    cleanup = disable(src_port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
    sock.connect((dst_addr, dst_port))
    (src_addr, _) = sock.getsockname()

    (seq_num, ack_num) = establish_connection(
            sock, src_addr, dst_addr, src_port, dst_port)

    # Send data
    flags = TCP_Flags()
    flags.set_ack_flag(True)
    flags.set_psh_flag(True)
    req_segment = TCP_Segment(
            src_port, dst_port, seq_num, ack_num, flags, payload)
    sock.sendall(req_segment.get_bytes(src_addr, dst_addr))

    # Receive Fin-Ack
    res_dgram = get_response(sock, src_port)
    res_segment = res_dgram.get_tcp_segment()
    seq_num = res_segment.get_ack_num()
    ack_num = res_segment.get_seq_num()

    terminate_connection(
            sock, src_addr, dst_addr, src_port, dst_port,
            seq_num, ack_num)

    sock.close()
    cleanup()

    return


if __name__ == "__main__":
    print("Sending...")
    send_in_one_datagram("127.0.0.1", 4444, b"Hello TCP.\n")

