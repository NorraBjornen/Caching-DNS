import binascii
import socket
import codecs


responses = dict()


def replace_at(s, i, c):
    s = list(s)
    s[i] = c
    return "".join(s)


def hex_to_bin(h):
    should = len(h) * 4
    b = str(bin(int(h, 16)))[2:]
    length = len(b)

    if length != should:
        b = b.rjust(should - length, '0')

    return b


def decimal_to_binary(n):
    return bin(n).replace("0b", "")


def to_bin_add_zeros(number, bits):
    temp = str(decimal_to_binary(number))
    zeros = (bits - len(temp)) * "0"
    return str(zeros + temp)


def add_zeroes(number, bits):
    zeros = (bits - len(str(number))) * "0"
    return str(zeros + str(number))


def binary_to_hex(n):
    return hex(int(n, 2)).replace("0x", "")


def send_udp_message(msg, address, port):
    msg = msg.replace(" ", "").replace("\n", "")
    server_address = (address, port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.sendto(binascii.unhexlify(msg), server_address)
        data, _ = sock.recvfrom(4096)
    finally:
        sock.close()
    return binascii.hexlify(data).decode("utf-8")


def format_hex(hexstr):
    """format_hex returns a pretty version of a hex string"""
    octets = [hexstr[i:i + 2] for i in range(0, len(hexstr), 2)]
    pairs = [" ".join(octets[i:i + 2]) for i in range(0, len(octets), 2)]
    return "\n".join(pairs)


def build_request(domain_name):
    res = []

    q_id = to_bin_add_zeros(43690, 16)
    qr = to_bin_add_zeros(0, 1)
    optcode = to_bin_add_zeros(0, 4)
    aa = to_bin_add_zeros(0, 1)
    tc = to_bin_add_zeros(0, 1)
    rd = to_bin_add_zeros(1, 1)
    ra = to_bin_add_zeros(0, 1)
    z = to_bin_add_zeros(0, 3)
    rcode = to_bin_add_zeros(0, 4)
    qdcount = to_bin_add_zeros(1, 16)
    ancount = to_bin_add_zeros(0, 16)
    nscount = to_bin_add_zeros(0, 16)
    arcount = to_bin_add_zeros(0, 16)

    header = binary_to_hex(q_id + qr + optcode + aa + tc + rd + ra + z + rcode + qdcount + ancount + nscount + arcount)

    res.append(header)

    sections = domain_name.split(".")

    for s in sections:
        result = []
        l = add_zeroes(len(s), 2)
        result.append(l)

        for c in s:
            s = str(codecs.encode(c.encode("utf-8"), "hex")).replace("'", "")[1:]
            result.append(s)

        res.append("".join(result))

    res.append("00")

    qtype = add_zeroes(1, 4)
    qclass = add_zeroes(1, 4)

    res.append(qtype)
    res.append(qclass)

    return "".join(res)


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
    name, offset = get_name(r)
    dot_count = name.count(".")
    char_count = len(name) - dot_count
    total_len = char_count * 2 + (dot_count + 2) * 2
    answer_header_index = 24 + total_len + 8
    ttl = r[answer_header_index + 16: answer_header_index + 20]

    ip = []

    data_len = r[answer_header_index + 20: answer_header_index + 24]

    l = int(data_len, 16)


    # data = r[answer_header_index + 24: answer_header_index + 24 + data_len]

    for i in range(0, 8, 2):
        ip.append(str(int(r[answer_header_index + 24 + i: answer_header_index + 26 + i], 16)))

    ip = ".".join(ip)

    print(ip)


def extract(r):
    name, offset = get_name(r)
    return r[:24], r[24:34+offset], r[34+offset:]


def parse_request(r):
    q_header, q_question, _ = extract(r)
    s = hex_to_bin(q_header[4:8])

    name = q_question[:-8]
    t = q_question[-8:-4]
    c = q_question[-4:]

    if t not in responses:
        responses[t] = dict()

    if name in responses[t]:
        resp = responses[t][name]
    else:
        r_header, r_question, resp = extract(send_udp_message(r, "8.8.8.8", 53))
        s = hex_to_bin(r_header[4:8])
        if s[-4:] == "0000":
            responses[t][name] = resp
