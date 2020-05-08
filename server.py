from socket import *
from answer import Answer, get_all_responses
import binascii

from utils import send_udp_message, decimal_to_hex

cache = dict()

# храним доменное имя (dns.local) для ip 127.0.0.1 нашего днс сервера
cache[("1.0.0.127.in-addr.arpa", "000c")] = [Answer("000c", "03646e73056c6f63616c00", "100")]


def get_name(r):
    start_name_index = 24

    name = []

    offset = 0

    while True:
        index = start_name_index + offset

        length = int(r[index:index + 2], 16)

        if length == 0:
            break

        i = 2
        while i <= length * 2:
            decoded = chr(int(r[index + i:index + i + 2], 16))
            name.append(decoded)
            i += 2

        name.append(".")
        offset += length * 2 + 2

    return "".join(name[:-1]), offset


def parse_response(r):
    header = r[0:24]
    question = r[24:]

    name, offset = get_name(r)

    t = question[offset - 8: offset - 4]

    dot_count = name.count(".")
    char_count = len(name) - dot_count
    question_len = char_count * 2 + (dot_count + 2) * 2

    answer = r[24 + question_len + 8:]

    an_count = header[12:16]

    count = int(an_count, 16)

    answers = []
    rest = answer

    for i in range(count):
        t = rest[4:8]
        ttl = rest[12:20]
        data_len = rest[20:24]

        data_length = int(data_len, 16) * 2
        data = rest[24:24+data_length]

        ans = Answer(t, data, ttl)

        answers.append(ans)
        rest = rest[24+data_length:]

    cache[(name, t)] = answers

    return r


def parse_request(request):
    header = request[0:24]
    question = request[24:]

    name, _ = get_name(request)

    t = question[-8: -4]

    if (name, t) in cache:
        content, count = get_all_responses(cache[(name, t)])

        if count != 0:
            _id = header[0:4]
            flags = "8180"
            qd_count = header[8:12]
            an_count = decimal_to_hex(count).rjust(4, '0')
            ns_count = header[16:20]
            ar_count = header[20:24]

            new_header = _id + flags + qd_count + an_count + ns_count + ar_count

            print("cache")

            return new_header + question + content

    print("server")

    return parse_response(send_udp_message(request, "8.8.8.8", 53))


host = 'localhost'
port = 53
addr = (host, port)

udp_socket = socket(AF_INET, SOCK_DGRAM)
udp_socket.bind(addr)

print(f"started on {addr}")
while True:
    received, addr = udp_socket.recvfrom(1024)
    received = binascii.hexlify(received).decode("utf-8")

    response = parse_request(received)

    udp_socket.sendto(binascii.unhexlify(response), addr)
