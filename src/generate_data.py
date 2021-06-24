from random import randint, choice

dev_types = ["emeter", "zigbee", "lora", "gsm"]


def get_random_dev_type() -> str:
    return choice(dev_types)


def get_random_mac_address() -> str:
    return "%02x:%02x:%02x:%02x:%02x:%02x" % (
        randint(0, 255),
        randint(0, 255),
        randint(0, 255),
        randint(0, 255),
        randint(0, 255),
        randint(0, 255)
    )
