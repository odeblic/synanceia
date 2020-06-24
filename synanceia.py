import hashlib
import os
from PIL import Image
import struct


class Synanceia(object):
    def __init__(self, original_image_file=None, modified_image_file=None):
        self.__image_file = modified_image_file
        if original_image_file is None:
            self.__image = Image.new('RGB', (255, 255), 'black')
        else:
            self.__image = Image.open(original_image_file)
        self.__image = self.__image.convert('RGB')  # RGBA

    def __get_capacity(self):
        width, height = self.__image.size
        return width * height

    def __set_capacity(self, value):
        ratio = (value / self.__get_capacity()) ** 0.5
        width, height = self.__image.size
        width *= ratio
        height *= ratio
        self.__image.resize(width, height)

    def hide(self, data_file, passphrase=None):
        byte_count = os.path.getsize(data_file)
        if byte_count > 1000000:
            raise Exception('File too big')
        filename = os.path.basename(data_file)
        with open(data_file, 'rb') as f:
            content = f.read()

        payload = self.__serialize(filename, content)

        payload = self.__makeup(payload)

        if passphrase is not None:
            payload = self.__encrypt(payload, passphrase)

        cursor = 0

        pixels = self.__image.load()
        for i in range(self.__image.size[0]): # image.width
            for j in range(self.__image.size[1]): # image.heigth
                if cursor < len(payload):
                    pixels[i, j] = self.__hide_into_pixel(pixels[i, j], payload[cursor])
                    cursor += 1
                else:
                    pixels[i, j] = self.__hide_into_pixel(pixels[i, j], 0)
        self.__image.save(self.__image_file)

    def reveal(self, passphrase=None):
        payload = bytearray()

        pixels = self.__image.load()
        for i in range(self.__image.size[0]): # image.width
            for j in range(self.__image.size[1]): # image.heigth
                payload.append(self.__reveal_from_pixel(pixels[i, j]))

        if passphrase is not None:
            payload = self.__decrypt(payload, passphrase)

        payload = self.__checkup(payload)

        filename, content = self.__deserialize(payload)

        with open('X-' + filename, 'wb') as f:
            f.write(content)

    def erase(self):
        pixels = self.__image.load()
        for i in range(self.__image.size[0]):
            for j in range(self.__image.size[1]):
                pixels[i, j] = self.__hide_into_pixel(pixels[i, j], 0)
        self.__image.save(self.__image_file)

    def __makeup(self, payload):
        m = hashlib.md5()

        new_capacity = len(payload) + m.digest_size

        while new_capacity > self.__get_capacity():
            print('adjust picture size to {} pixels'.format(new_capacity))
            self.__set_capacity(new_capacity)
            new_capacity += 1

        unused_capacity = self.__get_capacity() - len(payload) - m.digest_size
        padding = os.urandom(unused_capacity)

        m.update(payload)
        m.update(padding)
        checksum = m.digest()

        payload = payload + padding + checksum

        return payload

    @staticmethod
    def __checkup(payload):
        m = hashlib.md5()
        checksum = payload[-m.digest_size:]
        payload = payload[:-m.digest_size]
        m.update(payload)

        if checksum != m.digest():
            raise Exception('checksum error')

        return payload

    @staticmethod
    def __encrypt(payload, passphrase):
        payload_encrypted = bytearray(payload[:])
        key = Synanceia.__make_rolling_key(passphrase)
        for cursor in range(len(payload)):
            payload_encrypted[cursor] = payload[cursor] ^ next(key)
        return payload_encrypted

    @staticmethod
    def __decrypt(payload, passphrase):
        payload_decrypted = bytearray(payload[:])
        key = Synanceia.__make_rolling_key(passphrase)
        for cursor in range(len(payload)):
            payload_decrypted[cursor] = payload[cursor] ^ next(key)
        return payload_decrypted

    @staticmethod
    def __make_rolling_key(passphrase):
        m = hashlib.sha256()
        m.update(passphrase.encode('utf-8'))
        data = m.digest()
        cursor = 0
        while True:
            yield data[cursor]
            cursor += 1
            if cursor >= len(data):
                cursor = 0

    @staticmethod
    def __serialize(filename, content):
        filename = filename.encode('utf-8')
        schema = '!I{}sI{}s'.format(len(filename), len(content))
        payload = struct.pack(schema, len(filename), filename, len(content), content)
        return payload

    @staticmethod
    def __deserialize(payload):
        cursor = 0
        length, = struct.unpack('!I', payload[cursor:cursor+4])
        cursor += struct.calcsize('!I')
        filename, = struct.unpack('{}s'.format(length), payload[cursor:cursor+length])
        filename = filename.decode('utf-8')
        cursor += struct.calcsize('{}s'.format(length))
        length, = struct.unpack('!I', payload[cursor:cursor+4])
        cursor += struct.calcsize('!I')
        content, = struct.unpack('{}s'.format(length), payload[cursor:cursor+length])
        return (filename, content)

    @staticmethod
    def __hide_into_pixel(pixel, data):
        r_pixel = pixel[0] & ~ 0x03
        g_pixel = pixel[1] & ~ 0x07
        b_pixel = pixel[2] & ~ 0x07

        data &= 0xFF

        r_data = (data >> 6) & 0x03
        g_data = (data >> 3) & 0x07
        b_data = (data >> 0) & 0x07

        return (r_pixel | r_data, g_pixel | g_data, b_pixel | b_data)

    @staticmethod
    def __reveal_from_pixel(pixel):
        r_data = pixel[0] & 0x03
        g_data = pixel[1] & 0x07
        b_data = pixel[2] & 0x07

        data = r_data << 6 | g_data << 3 | b_data << 0

        return data

    @staticmethod
    def demo():
        img = Image.new('RGB', (255, 255), 'black')
        pixels = img.load()
        for i in range(img.size[0]):
            for j in range(img.size[1]):
                pixels[i, j] = (i, j, 100)
        img.show()


synanceia = Synanceia('input.bmp', 'output.bmp')

#synanceia.demo()
#synanceia.erase()

synanceia.hide('data.txt', 'secret')
synanceia.reveal('secret')
