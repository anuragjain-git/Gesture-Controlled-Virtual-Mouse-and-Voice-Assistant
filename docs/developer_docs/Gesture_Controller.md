# Gesture_Controller.py - Developer Documentation

## Overview
`Gesture_Controller.py` is the core module responsible for detecting hand gestures using **MediaPipe** and executing system-level controls like **mouse movement, scrolling, brightness, and volume adjustments**. It captures video frames, processes them for hand landmarks, classifies gestures, and maps them to system commands.

## Classes and Their Functions

### 1. `Gest (Enum)`
This **enumeration** assigns unique integer values to different hand gestures. It helps in gesture recognition by representing each gesture as a **binary-encoded integer**.

#### Gesture Encoding:
- `FIST = 0` → All fingers closed.
- `PINKY = 1` → Only pinky finger open.
- `INDEX = 8` → Only index finger open.
- `PALM = 31` → Open palm (all fingers extended).
- `PINCH_MAJOR = 35` → Pinch detected with the major (dominant) hand.
- `PINCH_MINOR = 36` → Pinch detected with the minor (non-dominant) hand.

### 2. `HLabel (Enum)`
This **enumeration** differentiates between the left and right hand:
- `MINOR = 0` → Left hand.
- `MAJOR = 1` → Right hand.

### 3. `HandRecog`
This class is responsible for **detecting hand landmarks**, **converting them into gestures**, and **reducing false detections due to noise**.

#### Methods:

#### `__init__(self, hand_label)`
**Initializes** the `HandRecog` object for either the left or right hand.

- `hand_label (int)`: Specifies whether the hand is `MINOR` (left) or `MAJOR` (right).
- Initializes gesture tracking variables like `finger`, `prev_gesture`, `frame_count`, etc.

#### `update_hand_result(self, hand_result)`
Updates the **current hand landmarks** detected by MediaPipe.

- `hand_result`: The detected hand landmarks (from MediaPipe).

#### `get_signed_dist(self, point)`
Computes the **signed** Euclidean distance between two hand landmark points.

- **Returns:** Signed distance (**positive or negative**) depending on hand movement direction.

#### `get_dist(self, point)`
Computes the **absolute** Euclidean distance between two points.

- **Returns:** Always **positive** distance value.

#### `get_dz(self, point)`
Calculates the difference in **depth (z-axis)** between two points.

- **Returns:** Absolute **z-axis depth** difference.

#### `set_finger_state(self)`
Determines **which fingers are open or closed** using distances between **finger tips, middle knuckles, and base knuckles**.

- Uses a **threshold ratio** to classify each finger as **open (1) or closed (0)**.

#### `get_gesture(self)`
Determines the **gesture being performed** based on finger positions.

- Reduces **false detections** by **requiring 5 consecutive frames** to confirm a gesture.
- Detects `PINCH`, `V_GEST`, `MID`, and `TWO_FINGER_CLOSED` gestures.

---

### 4. `Controller`
This class executes **system commands** (mouse control, volume, brightness, scrolling) based on detected gestures.

#### Methods:

#### `getpinchylv(hand_result)`
Calculates how much the hand **moves vertically** during a pinch gesture.

#### `getpinchxlv(hand_result)`
Calculates how much the hand **moves horizontally** during a pinch gesture.

#### `changesystembrightness()`
Adjusts **screen brightness** using the `sbcontrol` library.

- Uses the **pinch level** (`pinchlv`) to increase/decrease brightness.
- Ensures brightness stays **within 0%-100%**.

#### `changesystemvolume()`
Adjusts **system volume** using the `pycaw` library.

- Uses `pinchlv` to **increase or decrease volume**.
- Ensures volume stays **within 0%-100%**.

#### `scrollVertical()`
Scrolls the screen **up/down** based on the pinch movement.

#### `scrollHorizontal()`
Scrolls the screen **left/right** by **simulating `Shift + Scroll`**.

#### `get_position(hand_result)`
Finds **hand position** and stabilizes cursor movement using a **dampening algorithm** to avoid jittery motion.

#### `pinch_control_init(hand_result)`
Initializes pinch detection variables (starting x/y position, pinch level, etc.).

#### `pinch_control(hand_result, controlHorizontal, controlVertical)`
Determines if pinch movement is **horizontal (x-axis)** or **vertical (y-axis)** and **executes appropriate command**.

#### `handle_controls(gesture, hand_result)`
Executes different **mouse actions** based on detected gestures:
- Moves cursor (`V_GEST`)
- Left click (`MID`)
- Right click (`INDEX`)
- Drag (`FIST`)
- Double click (`TWO_FINGER_CLOSED`)

---

### 5. `GestureController`
This class handles **camera input**, captures hand landmarks using MediaPipe, classifies hands, and acts as the **main entry point** for the program.

#### Methods:

#### `__init__(self)`
Initializes **camera feed** and starts gesture detection.

#### `classify_hands(results)`
Assigns detected hands as **major (dominant)** or **minor (non-dominant)** based on user preferences.

#### `start(self)`
Main **loop** that:
1. **Captures frames** from the camera.
2. **Processes images** with MediaPipe.
3. **Classifies hands**.
4. **Executes gestures**.
5. **Draws hand landmarks**.

---

## How It Works Internally
1. **Video Capture**
   - The `GestureController` starts capturing frames using OpenCV.
   - Frames are converted from BGR → RGB (for MediaPipe processing).

2. **Hand Detection (MediaPipe)**
   - The program detects hands and assigns them as **major/minor**.

3. **Gesture Recognition**
   - `HandRecog` converts **hand landmarks** into binary **gesture encodings**.

4. **Action Execution**
   - `Controller` **maps gestures** to **system commands**.

5. **Output Display**
   - The modified frame is displayed with hand tracking.

---

## Conclusion
- `Gesture_Controller.py` is responsible for **gesture detection** and **executing system actions**.
- It processes **camera input**, **classifies hands**, and **maps gestures to system controls**.


This documentation provides everything you need to understand, modify, or extend this module.