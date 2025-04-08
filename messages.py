def sdk_mode():
    return bytes([0x01, 0x0d, 0x01])

def set_speed(speed: int, accel: int = 1000, decel: int = 1000, offset: int = 1):
    speed_bytes = speed.to_bytes(2, byteorder="little")
    accel_bytes = accel.to_bytes(2, byteorder="little")
    decel_bytes = decel.to_bytes(2, byteorder="little")
    return bytes([0x06, 0x24]) + speed_bytes + accel_bytes + bytes([offset])

def stop_car():
    return set_speed(0)
