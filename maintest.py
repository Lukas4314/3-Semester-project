
from mqqtInterface import MQTTInterface
from pc_code.turtleController import TurtleController
from pc_code.stringToCommand import string_to_command
from pc_code.transcriber import transcriber
from consts import MQTT_SERVER, MQTT_PORT, MQTT_TOPIC_VEL, MQTT_TOPIC_AUD1, MQTT_TOPIC_AUD0, RED, RED_END

def main():
    # --- Motion MQTT interface ---
    mqtt_vel = MQTTInterface(
        server=MQTT_SERVER,
        port=MQTT_PORT,
        topic=MQTT_TOPIC_VEL
    )

    # Turtle controller (goal-based)
    turtle = TurtleController(mqtt_vel)

    print("\nType commands like:")
    print("  go forward 1 meter")
    print("  move backward 0.5 meters")
    print("  turn left 90 degrees")
    print("  turn right pi radians")
    print("  stop")
    print("Type 'quit' to exit.\n")

    try:
        while True:
            text = input("> ").strip()

            if not text:
                continue

            if text.lower() in ("q", "quit", "exit"):
                break

            cmd = string_to_command(text)

            if cmd is None:
                print(
                    f"{RED}Could not parse command.{RED_END} "
                    "Try: 'go forward 1 meter' or 'turn left 90 degrees'"
                )
                continue

            # cmd = {
            #   "action": "move"/"turn"/"stop",
            #   "direction": "forward"/"backward"/"left"/"right",
            #   "distance": <meters or radians>
            # }

            turtle.execute_command(
                cmd["action"],
                cmd.get("direction"),
                cmd.get("distance")
            )

    except KeyboardInterrupt:
        pass

    finally:
        print("\nStopping robot and disconnecting...")
        try:
            turtle.stop()
        except Exception:
            pass

        mqtt_vel.disconnect()


if __name__ == "__main__":
    main()
