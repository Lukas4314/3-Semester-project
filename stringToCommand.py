import turtleController
# Converting strings into actions

# I want to map multiple strings to the same action, the actions have to be in order of direction, distance, unit. If the strings are not in that order the function doesn't do anything, it just keeps reading the input.
# An example of a valid input would be "forward 10 meters" or "move 1 meter".

# For example move, go, forward, straight all map to the same action "move".

"""
def stop():
    print("Stopping")

def move_forward(distance, unit):
    print(f"Moving forward {distance} {unit}")

def move_backward(distance, unit):
    print(f"Moving backward {distance} {unit}")

def turn_left(angle, unit):
    print(f"Turning left {angle} {unit}")

def turn_right(angle, unit):
    print(f"Turning right {angle} {unit}")
"""
    
def string_to_command(input_string):
    actions = {
        "move": ["move", "go", "drive"],
        "turn": ["turn", "rotate", "spin"],
        "stop": ["stop", "halt", "pause", "brake", "no"]
    }

    # synonyms for the same direction
    directions = {
        "forward": ["forward", "straight"],
        "backward": ["backward", "back", "reverse"],
        "left": ["left"],
        "right": ["right"]
    }

    # reverse lookups
    action_lookup = {syn: act for act, syns in actions.items() for syn in syns}
    direction_lookup = {syn: canon for canon, syns in directions.items() for syn in syns}

    units = {"centimeters", "centimeter", "millimeters", "millimeter", "meters", "meter", 
             "radians", "radian", "degrees", "degree"}

    # Defaults used when distance/unit aren't included
    DEFAULTS = {
        "move": {"distance": 1, "unit": "meters"},   
        "turn": {"distance": 90, "unit": "degrees"}  
    }

    # Normalize and remove punctuation (keep letters, digits, spaces)
    cleaned = ''.join(ch for ch in input_string.lower() if ch.isalnum() or ch.isspace())
    words = cleaned.split()

    # collect all occurrences (don't overwrite earlier ones)
    actions_found = []        # list of (index, action)
    directions_found = []     # list of (index, direction)
    distance = None
    distance_index = None
    unit = None
    unit_index = None

    for i, w in enumerate(words):
        if w in action_lookup:
            actions_found.append((i, action_lookup[w]))
        if w in direction_lookup:
            directions_found.append((i, direction_lookup[w]))
        if distance is None and w.isdigit():
            distance = int(w)
            distance_index = i
        if unit is None and w in units:
            unit = w
            unit_index = i

    if any(a == "stop" for _, a in actions_found):
        turtleController.stop()
        return

    # If a distance exists, ensure any explicit unit (if present) comes after it
    if distance is not None and unit is not None and unit_index <= distance_index:
        return None

    # Choose action & base_index depending on whether distance is present
    if distance is not None:
        # pick the action that occurs before the distance and is closest to it
        actions_before = [(i, a) for i, a in actions_found if i < distance_index]
        if actions_before:
            base_index, action = max(actions_before, key=lambda t: t[0])
        else:
            # no explicit action before distance: try to use a direction before distance as implicit move
            directions_before = [(i, d) for i, d in directions_found if i < distance_index]
            if directions_before:
                base_index, dir_candidate = max(directions_before, key=lambda t: t[0])
                action = "move"
                direction = dir_candidate
            else:
                return None

        # if unit missing, default by action type
        if unit is None:
            unit = DEFAULTS["turn"]["unit"] if action == "turn" else DEFAULTS["move"]["unit"]

    else:
        # No distance provided: require at least one action and one direction to apply defaults
        if not actions_found or not directions_found:
            return None

        # Prefer pairs where action occurs before direction and is closest to it
        best_pair = None
        best_gap = None
        for actioni, a in actions_found:
            for directioni, d in directions_found:
                gap = directioni - actioni
                if gap >= 0:
                    if best_pair is None or gap < best_gap:
                        best_pair = (actioni, a, directioni, d)
                        best_gap = gap
        # If no action-before-direction pair, pick the closest pair (any order)
        if best_pair is None:
            for actioni, a in actions_found:
                for directioni, d in directions_found:
                    gap = abs(directioni - actioni)
                    if best_pair is None or gap < best_gap:
                        best_pair = (actioni, a, directioni, d)
                        best_gap = gap

        if best_pair is None:
            return None

        actioni, action, directioni, direction = best_pair
        base_index = actioni if actioni <= directioni else directioni

        # Apply defaults for missing distance/unit based on action
        defaults = DEFAULTS.get(action, DEFAULTS["move"])
        distance = defaults["distance"]
        unit = defaults["unit"]
        distance_index = base_index  # logical position for ordering checks

    # choose the most relevant direction:
    # prefer a direction that appears between the chosen base_index and the distance (if distance index known)
    if distance_index is not None:
        in_between_dirs = [(i, d) for i, d in directions_found if base_index < i < (distance_index if distance_index is not None else float("inf"))]
        if in_between_dirs:
            direction = max(in_between_dirs, key=lambda t: t[0])[1]
        else:
            # fallback: take the nearest direction before distance (could be before base_index)
            directions_before = [(i, d) for i, d in directions_found if distance_index is None or i < distance_index]
            if directions_before:
                direction = max(directions_before, key=lambda t: t[0])[1]
            else:
                direction = None

    if action == "stop":
        turtleController.stop()

    if action == "move":
        if direction == "forward":
            turtleController.move(distance, unit)
        elif direction == "backward":
            turtleController.move(-distance, unit)
        else:
            return None
        
    if action == "turn":
        if direction == "left":
            turtleController.turn(distance, unit)
        elif direction == "right":
            turtleController.turn(-distance, unit)
        else:
            return None
"""        
    return {
        "action": action,
        "direction": direction,
        "distance": distance,
        "unit": unit
    }
"""
# Test the function in the console
if __name__ == "__main__":
    while True:
        user_input = input("Enter a command: ")
        command = string_to_command(user_input)
        if command:
            print("Parsed command:", command)
