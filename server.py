# Модуль socket для сетевого программирования
from socket import *
import binascii

# данные сервера
from main import send_udp_message, hex_to_bin, get_name

cache = dict()


def hex_to_ip(h):
    return str(int(h[:2], 16)) + "." + str(int(h[2:4], 16)) + "." + str(int(h[4:6], 16)) + "." + str(int(h[6:8], 16))


def parse_response(r):
    header = r[0:24]
    question = r[24:]

    name, offset = get_name(r)

    t = question[offset - 8: offset - 4]

    dot_count = name.count(".")
    char_count = len(name) - dot_count
    total_len = char_count * 2 + (dot_count + 2) * 2
    answer_header_index = 24 + total_len + 8

    answer = r[answer_header_index:]

    _id = header[0:4]
    flags = header[4:8]
    qd_count = header[8:12]
    an_count = header[12:16]
    ns_count = header[16:20]
    ar_count = header[20:24]

    count = int(an_count, 16)

    answers = []
    rest = answer

    for i in range(count):
        # name = rest[0:4]
        t = rest[4:8]
        c = rest[8:12]
        ttl = rest[12:20]
        rdlen = rest[20:24]

        data_length = int(rdlen, 16) * 2
        # rdata = rest[24:24+data_length]
        rdata = rest[:24+data_length]

        answers.append(rdata)
        rest = rest[24+data_length:]

    cache[(name, t)] = answers

    # for item in answers:
        # print(item)

    return r


def parse_request(r):
    header = r[0:24]
    question = r[24:]

    name, offset = get_name(r)

    t = question[-8: -4]

    if t == "000c":
        answer = "c00c000c0001000051ba000b03646e73056c6f63616c00"
        header = header[0:4] + "81800001000100000000"
        return header + question + answer

    if (name, t) in cache:
        answers = cache[(name, t)]
        _id = header[0:4]
        flags = "8180"
        qd_count = header[8:12]
        an_count = str(hex(len(answers)))[2:]
        an_count = an_count.rjust(4, '0')
        ns_count = header[16:20]
        ar_count = header[20:24]

        new_header = _id + flags + qd_count + an_count + ns_count + ar_count

        print("from cache")

        return new_header + question + "".join(answers)

    print("from google server")
    return parse_response(send_udp_message(r, "8.8.8.8", 53))


host = 'localhost'
port = 53
addr = (host, port)

udp_socket = socket(AF_INET, SOCK_DGRAM)
udp_socket.bind(addr)

# Бесконечный цикл работы программы
print(f"started on {addr}")
while True:
    data, addr = udp_socket.recvfrom(1024)
    data = binascii.hexlify(data).decode("utf-8")

    response = parse_request(data)

    udp_socket.sendto(binascii.unhexlify(response), addr)
