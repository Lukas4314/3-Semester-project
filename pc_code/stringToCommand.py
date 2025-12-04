import math
import enum
import re
# Converting strings into actions

# I want to map multiple strings to the same action, the actions have to be in order of direction, distance, unit. If the strings are not in that order the function doesn't do anything, it just keeps reading the input.
# An example of a valid input would be "forward 10 meters" or "move 1 meter".

# For example move, go, forward, straight all map to the same action "move".
  
class actionEnum(enum.Enum):
    MOVE = "move"
    COME = "come here"
    TURN = "turn"
    STOP = "stop"
    

class directionEnum(enum.Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"
    

class unitEnum(enum.Enum):
    METERS = "meters"
    CENTIMETERS = "centimeters"
    MILLIMETERS = "millimeters"
    DEGREES = "degrees"
    RADIANS = "radians"


ACTIONS = {
    "move": actionEnum.MOVE,
    "go": actionEnum.MOVE,
    "drive": actionEnum.MOVE,
    "dry": actionEnum.MOVE,
    "going": actionEnum.MOVE,
    "oh": actionEnum.MOVE,
    "so": actionEnum.MOVE,
    
    "turn": actionEnum.TURN,
    "rotate": actionEnum.TURN,
    "spin": actionEnum.TURN,
    
    "stop": actionEnum.STOP,
    "halt": actionEnum.STOP,
    "pause": actionEnum.STOP,
    "brake": actionEnum.STOP,
    "no": actionEnum.STOP,

    "come here": actionEnum.COME
}

DIRECTIONS = {
    "forward": directionEnum.FORWARD,
    "forwards": directionEnum.FORWARD,
    "straight": directionEnum.FORWARD,
    "for": directionEnum.FORWARD,
    "false": directionEnum.FORWARD,
    
    "backward": directionEnum.BACKWARD,
    "backwards": directionEnum.BACKWARD,
    "back": directionEnum.BACKWARD,
    "reverse": directionEnum.BACKWARD,
    "thank": directionEnum.BACKWARD,
    "bag": directionEnum.BACKWARD,
    "backwalks": directionEnum.BACKWARD,
    
    "left": directionEnum.LEFT,
    "lift": directionEnum.LEFT,
    
    "right": directionEnum.RIGHT,
}
UNITS = {
    "meter":     unitEnum.METERS,
    "meters":    unitEnum.METERS,
    "metre":     unitEnum.METERS,
    "metres":    unitEnum.METERS,
    "metered":    unitEnum.METERS,
    "m":         unitEnum.METERS,
    "minute":    unitEnum.METERS,
    "minutes":   unitEnum.METERS,
    "media":     unitEnum.METERS,

    "centimeter":    unitEnum.CENTIMETERS,
    "centimeters":   unitEnum.CENTIMETERS,
    "centimetre":    unitEnum.CENTIMETERS,
    "centimetres":   unitEnum.CENTIMETERS,
    "cm":            unitEnum.CENTIMETERS,

    "millimeter":    unitEnum.MILLIMETERS,
    "millimeters":   unitEnum.MILLIMETERS,
    "millimetre":    unitEnum.MILLIMETERS,
    "millimetres":   unitEnum.MILLIMETERS,
    "mm":            unitEnum.MILLIMETERS,

    "degree":    unitEnum.DEGREES,
    "degrees":   unitEnum.DEGREES,
    "deg":       unitEnum.DEGREES,

    "radian":    unitEnum.RADIANS,
    "radians":   unitEnum.RADIANS,
    "rad":       unitEnum.RADIANS,
}

# Defaults used when distance/unit aren't included
DEFAULTS = {
    "move": {"distance": 1.0,  "unit": "meters"},
    "turn": {"distance": 90.0, "unit": "degrees"},
}

def clean_string(input_string: str) -> str:
    """
    Lowercase, remove punctuation, keep spaces and digits.
    Treat decimal commas like '1,5' as '1.5'.
    """
    result = []
    last_was_digit = False

    for ch in input_string.lower():
        if ch.isalnum() or ch.isspace() or ch == "_":
            result.append(ch)
            last_was_digit = ch.isdigit()
        elif ch == "," and last_was_digit:
            # decimal comma → convert to dot
            result.append(".")
        elif ch.isspace():
            result.append(" ")
            last_was_digit = False
        else:
            # ignore other punctuation
            last_was_digit = False

    return "".join(result)

def collapse_multiword_actions(s):
    # Turn spaces into underscores for multi-word actions (e.g. "come here" -> "come_here") ()
    # sort by length desc so "come here" matches before "come"
    for phrase in sorted(ACTIONS.keys(), key=len, reverse=True):
        if " " in phrase:
            token = phrase.replace(" ", "_")
            s = re.sub(r"\b" + re.escape(phrase) + r"\b", token, s, flags=re.IGNORECASE)
    return s

def apply_unit_conversion(distance: float, unit: str):
    """
    Convert linear units to meters. `unit` is the canonical string.
    """
    linear_factors = {
        "millimeters": 0.001,
        "centimeters": 0.01,
        "meters":      1.0,
    }
    if unit in linear_factors:
        factor = linear_factors[unit]
        return distance * factor, "meters"
    return distance, unit  # No conversion applied (e.g. degrees/radians)

def string_to_command(input_string):
    # Preprocess input string
    s = input_string.lower()
    s = collapse_multiword_actions(s)

    text_numbers = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",

        "further": "30",
        "while": "1",
        "we're": "1",
        "with": "1",
        
    }

    for word, digit in text_numbers.items():
        # replace digit words with digits
        s = re.sub(r"\b" + re.escape(word) + r"\b", digit, s)

    cleaned = clean_string(s)
    words = cleaned.split()
    
    # collect all occurrences
    actions_found = []        # list of (index, action)
    directions_found = []     # list of (index, direction)
    distances_found = []      # list of (index, distance)
    units_found = []         # list of (index, unit)

    for i, w in enumerate(words):
        w_action_key = w.replace("_", " ")
        if w_action_key in ACTIONS:
            actions_found.append((i, ACTIONS[w_action_key].value))
        if w in DIRECTIONS:
            directions_found.append((i, DIRECTIONS[w].value))
        if w in UNITS:
            # convert to canonical unit string (e.g. "cm" -> "centimeters")
            canonical_unit = UNITS[w].value
            units_found.append((i, canonical_unit))
        
            units_found.append((i, w))

        if w == "pi":
            distances_found.append((i, math.pi))
        else:
            try:
                distances_found.append((i, float(w)))
            except ValueError:
                pass

    # If a 'stop' action was spoken, prefer it and return immediately.
    if any(action == "stop" for _, action in actions_found):
        return {"action": "stop", "direction": None, "distance": None, "unit": None}

    # If a 'come' action was spoken, return come immediately (no direction/distance)
    if any(action == "come here" for _, action in actions_found):
        return {"action": "come here", "direction": None, "distance": None, "unit": None}

    if actions_found == [] or directions_found == []:
        print("No actions or directions found.")
        return None
       
    distance_unit_pairs = []    
    # Gets all the pairs where the unit comes right after the distance
    for di, dist in distances_found:
        for ui, un in units_found:
            if ui == di + 1:
                distance_unit_pairs.append((di, dist, un))
        
    # Takes the reversed order of commands to find the newest action
    actions_found_reversed = list(reversed(actions_found))
    for ai, action in actions_found_reversed:
        
        next_direction = None
        
        # Takes the first direction which comes after the action
        for di, direction in directions_found:
            if ai > di:
                continue
            next_direction = direction
            break
        
        if next_direction is None:
            print("No direction found after action.")
            continue
        
        next_direction = None
        # restrict which directions are valid for each action
        allowed_dirs = {
            "move": {directionEnum.FORWARD.value, directionEnum.BACKWARD.value},
            "turn": {directionEnum.LEFT.value, directionEnum.RIGHT.value},
            "stop": set(),
        }
        # find the first direction after the action that is valid for this action
        for di, direction in directions_found:
            if ai > di:
                continue
            if direction in allowed_dirs.get(action, set()):
                next_direction = direction
                break

        if next_direction is None:
            print(f"No valid direction found after action '{action}'.")
            return None
        
        next_unit = None
        next_distance = None
        
        for di, dist, un in distance_unit_pairs:
            if ai > di:
                continue
            next_distance = dist
            next_unit = un
            break
        
        if next_distance is None and next_unit is None:
            continue
        
        # unit handling
        # For MOVE: convert linear units to meters
        # For TURN: convert degrees/radians to radians
        if action != "turn":
            next_distance, next_unit = apply_unit_conversion(next_distance, next_unit)
        else:
            # next_unit is canonical "degrees" or "radians"
            if next_unit == "degrees":
                next_distance = float(next_distance) * (math.pi / 180.0)
                next_unit = "radians"
            elif next_unit == "radians":
                next_distance = float(next_distance)
            else:
                # invalid unit for a turn
                print(f"Invalid unit '{next_unit}' for turn.")
                return None
        
        cmd = {
            "action": action,
            "direction": next_direction,
            "distance": float(next_distance),
            "unit": next_unit,
        }
        print("Parsed command:", cmd)
        return cmd

    return None

"""



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

    # normalize distance to a numeric value
    try:
        dist_val = float(distance)
    except Exception:
        dist_val = None

    if action == "stop":
        return {"action": "stop", "direction": None, "distance": None, "unit": None}

    if action == "move":
        if dist_val is None:
            return None
        linear_factors = {
            "millimeter": 0.001,
            "millimeters": 0.001,
            "centimeter": 0.01,
            "centimeters": 0.01,
            "meter": 1.0,
            "meters": 1.0
        }
        factor = linear_factors.get(unit)
        if factor is None:
            return None
        meters = dist_val * factor
        return {"action": "move", "direction": direction, "distance": float(meters), "unit": "meters"}
    
    if action == "turn":
        if dist_val is None:
            return None
        if unit in ("degree", "degrees"):
            radians = dist_val / (180 / math.pi)
        elif unit in ("radian", "radians"):
            radians = dist_val
        else:
            return None
        return {"action": "turn", "direction": direction, "distance": float(radians), "unit": "radians"}

"""


# Test the function in the console
if __name__ == "__main__": 
    while True:
        user_input = input("Enter a command: ")
        command = string_to_command(user_input)
        if command:
            print("Parsed command:", command)