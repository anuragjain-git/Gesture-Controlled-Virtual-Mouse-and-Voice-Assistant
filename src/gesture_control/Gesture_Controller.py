import cv2  # OpenCV for capturing and processing video frames
import mediapipe as mp  # MediaPipe for hand tracking and gesture recognition
import pyautogui  # Simulates mouse and keyboard actions
import math  # Used for mathematical calculations like distance computation
from enum import IntEnum  # Helps define constants for gesture labels
from ctypes import cast, POINTER  # Used for system audio control (Windows-specific)
from comtypes import CLSCTX_ALL  # Required for interfacing with Windows components
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # Controls system audio volume
from google.protobuf.json_format import MessageToDict  # Converts MediaPipe results to a Python dictionary
import screen_brightness_control as sbcontrol  # Adjusts screen brightness

# Disables PyAutoGUI's fail-safe feature that stops execution if the mouse moves to the corner of the screen
pyautogui.FAILSAFE = False

# Initialize MediaPipe utilities
mp_drawing = mp.solutions.drawing_utils  # Used for drawing hand landmarks on the screen
mp_hands = mp.solutions.hands  # Provides hand-tracking capabilities

# Gesture Encodings 
class Gest(IntEnum):
    """
    Enum for mapping all hand gestures to binary numbers.
    Each gesture is represented as a unique integer.
    """

    FIST = 0  # All fingers closed
    PINKY = 1  # Only pinky finger open
    RING = 2  # Only ring finger open
    MID = 4  # Only middle finger open
    LAST3 = 7  # Last three fingers open (middle, ring, pinky)
    INDEX = 8  # Only index finger open
    FIRST2 = 12  # First two fingers (index and middle) open
    LAST4 = 15  # Last four fingers open (excluding thumb)
    THUMB = 16  # Only thumb open  
    PALM = 31  # All fingers open (open palm)
    
    # Extra Mappings
    V_GEST = 33  # "V" sign using index and middle fingers
    TWO_FINGER_CLOSED = 34  # Two fingers closed together
    PINCH_MAJOR = 35  # Major pinch (used for volume/brightness control)
    PINCH_MINOR = 36  # Minor pinch (used for fine-tuned control)

# Multi-handedness Labels
class HLabel(IntEnum):
    """
    Enum for distinguishing between left and right hands.
    """
    MINOR = 0  # Left hand
    MAJOR = 1  # Right hand

# Convert MediaPipe Landmarks to Recognizable Gestures
class HandRecog:
    """
    Converts MediaPipe hand landmarks into recognizable gestures.
    """

    def __init__(self, hand_label):
        """
        Initializes the HandRecog class with attributes for gesture recognition.

        Parameters
        ----------
        finger : int
            Stores the computed gesture for the current frame.
        ori_gesture : Gest
            The original gesture being used.
        prev_gesture : Gest
            Gesture computed in the previous frame.
        frame_count : int
            Number of frames since 'ori_gesture' was last updated.
        hand_result : Object
            Stores the landmarks obtained from MediaPipe for the current hand.
        hand_label : int
            Identifies whether the hand is left (MINOR) or right (MAJOR).
        """

        self.finger = 0  # Stores computed gesture for the current frame
        self.ori_gesture = Gest.PALM  # The original gesture being used
        self.prev_gesture = Gest.PALM  # Gesture computed in the previous frame
        self.frame_count = 0  # Number of frames since 'ori_gesture' was updated
        self.hand_result = None  # Stores landmarks obtained from MediaPipe
        self.hand_label = hand_label  # Stores hand type (left or right)

    def update_hand_result(self, hand_result):
        """
        Updates the detected hand landmarks.
        """
        self.hand_result = hand_result

    def get_signed_dist(self, point):
        """
        Computes signed Euclidean distance between two landmark points.

        Parameters
        ----------
        point : list
            Contains two elements (indices of hand landmarks).

        Returns
        -------
        float
            Signed Euclidean distance.
        """
        sign = -1
        if self.hand_result.landmark[point[0]].y < self.hand_result.landmark[point[1]].y:
            sign = 1
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x) ** 2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y) ** 2
        dist = math.sqrt(dist)
        return dist * sign

    def get_dist(self, point):
        """
        Computes Euclidean distance between two landmark points.

        Parameters
        ----------
        point : list
            Contains two elements (indices of hand landmarks).

        Returns
        -------
        float
            Euclidean distance.
        """
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x) ** 2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y) ** 2
        return math.sqrt(dist)

    def get_dz(self, point):
        """
        Computes absolute difference in the z-axis between two landmark points.

        Parameters
        ----------
        point : list
            Contains two elements (indices of hand landmarks).

        Returns
        -------
        float
        """
        return abs(self.hand_result.landmark[point[0]].z - self.hand_result.landmark[point[1]].z)

    def set_finger_state(self):
        """
        Determines which fingers are open based on their distances from knuckles.

        Uses ratios of distances between:
        - Finger tip → Middle knuckle
        - Middle knuckle → Base knuckle

        Returns
        -------
        None
        Set Finger_state: 1 if finger is open, else 0
        """
        if self.hand_result is None:
            return

        # Points representing the tip, middle knuckle, and base knuckle for each finger
        points = [[8, 5, 0], [12, 9, 0], [16, 13, 0], [20, 17, 0]]
        self.finger = 0

        for idx, point in enumerate(points):
            dist = self.get_signed_dist(point[:2])  # Tip to middle knuckle
            dist2 = self.get_signed_dist(point[1:])  # Middle knuckle to base

            try:
                ratio = round(dist / dist2, 1)
            except:
                ratio = round(dist / 0.01, 1)  # Prevent division by zero

            self.finger = self.finger << 1  # Shift bit to left
            if ratio > 0.5:  # If finger is open
                self.finger = self.finger | 1  # Set bit to 1

    def get_gesture(self):
        """
        Determines the current gesture and handles fluctuations due to noise.

        Returns
        -------
        int
            Integer corresponding to a gesture from the Gest Enum.
        """
        if self.hand_result is None:
            return Gest.PALM

        current_gesture = Gest.PALM

        # Pinch Detection (Used for controlling brightness/volume)
        if self.finger in [Gest.LAST3, Gest.LAST4] and self.get_dist([8, 4]) < 0.05:
            if self.hand_label == HLabel.MINOR:
                current_gesture = Gest.PINCH_MINOR
            else:
                current_gesture = Gest.PINCH_MAJOR

        # Detect "V" Gesture or Two-Finger Closed Gesture
        elif Gest.FIRST2 == self.finger:
            point = [[8, 12], [5, 9]]  # Landmarks for index and middle finger
            dist1 = self.get_dist(point[0])
            dist2 = self.get_dist(point[1])
            ratio = dist1 / dist2

            if ratio > 1.7:
                current_gesture = Gest.V_GEST
            else:
                if self.get_dz([8, 12]) < 0.1:
                    current_gesture = Gest.TWO_FINGER_CLOSED
                else:
                    current_gesture = Gest.MID

        else:
            current_gesture = self.finger

        # Reduce noise by requiring 5 consistent frames before confirming gesture
        if current_gesture == self.prev_gesture:
            self.frame_count += 1
        else:
            self.frame_count = 0

        self.prev_gesture = current_gesture

        if self.frame_count > 4:
            self.ori_gesture = current_gesture

        return self.ori_gesture


# Executes commands according to detected gestures
class Controller:
    """
    Executes commands based on detected gestures.

    Attributes
    ----------
    tx_old : int
        Previous mouse x-coordinate.
    ty_old : int
        Previous mouse y-coordinate.
    flag : bool
        True if 'V' gesture is detected.
    grabflag : bool
        True if 'FIST' gesture is detected.
    pinchmajorflag : bool
        True if 'PINCH' gesture is detected with the major (dominant) hand.
        - Controls brightness on x-axis.
        - Controls volume on y-axis.
    pinchminorflag : bool
        True if 'PINCH' gesture is detected with the minor (non-dominant) hand.
        - Controls horizontal scrolling on x-axis.
        - Controls vertical scrolling on y-axis.
    pinchstartxcoord : int
        x-coordinate of the hand landmark when the pinch gesture starts.
    pinchstartycoord : int
        y-coordinate of the hand landmark when the pinch gesture starts.
    pinchdirectionflag : bool
        True if pinch movement is along the x-axis, otherwise False.
    prevpinchlv : int
        Stores quantized magnitude of previous pinch gesture displacement.
    pinchlv : int
        Stores quantized magnitude of current pinch gesture displacement.
    framecount : int
        Number of frames since 'pinchlv' was last updated.
    prev_hand : tuple
        Stores (x, y) coordinates of the hand in the previous frame.
    pinch_threshold : float
        Step size for quantization of 'pinchlv'.
    """

    # Class-level attributes (shared across all instances)
    tx_old = 0  # Old x-coordinate for cursor stabilization
    ty_old = 0  # Old y-coordinate for cursor stabilization
    trial = True  # Unused attribute (potentially for debugging)
    flag = False  # Indicates if 'V' gesture is detected
    grabflag = False  # Indicates if 'FIST' gesture is detected
    pinchmajorflag = False  # Tracks if major hand is pinching
    pinchminorflag = False  # Tracks if minor hand is pinching
    pinchstartxcoord = None  # Initial x-coordinate when pinch starts
    pinchstartycoord = None  # Initial y-coordinate when pinch starts
    pinchdirectionflag = None  # True for x-axis pinch, False for y-axis
    prevpinchlv = 0  # Previous pinch displacement value
    pinchlv = 0  # Current pinch displacement value
    framecount = 0  # Counter for frames since pinch update
    prev_hand = None  # Previous frame's hand coordinates
    pinch_threshold = 0.3  # Pinch movement step size

    def getpinchylv(hand_result):
        """Calculates how much the hand has moved vertically during a pinch."""
        dist = round((Controller.pinchstartycoord - hand_result.landmark[8].y) * 10, 1)  # Find vertical movement difference
        return dist  # Return calculated distance

    def getpinchxlv(hand_result):
        """Calculates how much the hand has moved horizontally during a pinch."""
        dist = round((hand_result.landmark[8].x - Controller.pinchstartxcoord) * 10, 1)  # Find horizontal movement difference
        return dist  # Return calculated distance
    
    def changesystembrightness():
        """Changes system brightness based on pinch movement."""
        currentBrightnessLv = sbcontrol.get_brightness(display=0) / 100.0  # Get current brightness level (0 to 1 scale)
        currentBrightnessLv += Controller.pinchlv / 50.0  # Adjust brightness based on pinch level
        
        # Ensure brightness is within valid range (0 to 1)
        if currentBrightnessLv > 1.0:
            currentBrightnessLv = 1.0
        elif currentBrightnessLv < 0.0:
            currentBrightnessLv = 0.0  
        
        sbcontrol.fade_brightness(int(100 * currentBrightnessLv), start=sbcontrol.get_brightness(display=0))  # Apply brightness change
    
    def changesystemvolume():
        """Changes system volume based on pinch movement."""
        devices = AudioUtilities.GetSpeakers()  # Get audio output device
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)  # Activate volume control interface
        volume = cast(interface, POINTER(IAudioEndpointVolume))  # Get volume control object
        currentVolumeLv = volume.GetMasterVolumeLevelScalar()  # Get current volume level (0 to 1 scale)
        currentVolumeLv += Controller.pinchlv / 50.0  # Adjust volume based on pinch level
        
        # Ensure volume is within valid range (0 to 1)
        if currentVolumeLv > 1.0:
            currentVolumeLv = 1.0
        elif currentVolumeLv < 0.0:
            currentVolumeLv = 0.0
        
        volume.SetMasterVolumeLevelScalar(currentVolumeLv, None)  # Apply volume change
    
    def scrollVertical():
        """Scrolls the screen up or down based on pinch movement."""
        pyautogui.scroll(120 if Controller.pinchlv > 0.0 else -120)  # Scroll up for positive pinch, down for negative pinch
    
    def scrollHorizontal():
        """Scrolls the screen left or right based on pinch movement."""
        pyautogui.keyDown('shift')  # Hold shift key (for horizontal scrolling in some apps)
        pyautogui.keyDown('ctrl')  # Hold control key
        pyautogui.scroll(-120 if Controller.pinchlv > 0.0 else 120)  # Scroll horizontally
        pyautogui.keyUp('ctrl')  # Release control key
        pyautogui.keyUp('shift')  # Release shift key
    
    def get_position(hand_result):
        """Finds the current position of the hand and stabilizes cursor movement."""
        point = 9  # Landmark index for hand position tracking
        position = [hand_result.landmark[point].x, hand_result.landmark[point].y]  # Get x and y position of the hand
        sx, sy = pyautogui.size()  # Get screen dimensions
        x_old, y_old = pyautogui.position()  # Get previous cursor position
        x = int(position[0] * sx)  # Convert hand x-position to screen coordinates
        y = int(position[1] * sy)  # Convert hand y-position to screen coordinates
        
        if Controller.prev_hand is None:
            Controller.prev_hand = x, y  # Store initial hand position
        
        delta_x = x - Controller.prev_hand[0]  # Change in x-position
        delta_y = y - Controller.prev_hand[1]  # Change in y-position
        
        distsq = delta_x**2 + delta_y**2  # Distance squared for movement stabilization
        ratio = 1  # Default movement ratio
        Controller.prev_hand = [x, y]  # Update previous hand position
        
        if distsq <= 25:
            ratio = 0  # Ignore small movements
        elif distsq <= 900:
            ratio = 0.07 * (distsq ** (1/2))  # Apply gradual movement adjustment
        else:
            ratio = 2.1  # Allow larger movements
        
        x, y = x_old + delta_x * ratio, y_old + delta_y * ratio  # Apply stabilized movement
        return (x, y)  # Return new cursor position
    
    def pinch_control_init(hand_result):
        """Initializes pinch control attributes when a pinch starts."""
        Controller.pinchstartxcoord = hand_result.landmark[8].x  # Store x-coordinate where pinch starts
        Controller.pinchstartycoord = hand_result.landmark[8].y  # Store y-coordinate where pinch starts
        Controller.pinchlv = 0  # Reset pinch level
        Controller.prevpinchlv = 0  # Reset previous pinch level
        Controller.framecount = 0  # Reset frame counter
    
    def handle_controls(gesture, hand_result):
        """Executes different actions based on detected hand gestures."""
        x, y = None, None
        if gesture != Gest.PALM:
            x, y = Controller.get_position(hand_result)  # Get hand position for cursor movement
        
        # Reset flags if gestures change
        if gesture != Gest.FIST and Controller.grabflag:
            Controller.grabflag = False
            pyautogui.mouseUp(button="left")
        
        if gesture == Gest.V_GEST:
            Controller.flag = True
            pyautogui.moveTo(x, y, duration=0.1)  # Move cursor smoothly
        
        elif gesture == Gest.FIST:
            if not Controller.grabflag:
                Controller.grabflag = True
                pyautogui.mouseDown(button="left")  # Start dragging
            pyautogui.moveTo(x, y, duration=0.1)  # Move cursor while dragging
        
        elif gesture == Gest.PINCH_MAJOR:
            if not Controller.pinchmajorflag:
                Controller.pinch_control_init(hand_result)
                Controller.pinchmajorflag = True
            Controller.pinch_control(hand_result, Controller.changesystembrightness, Controller.changesystemvolume)

class GestureController:
    """
    Handles camera input, obtains hand landmarks from MediaPipe, and acts as 
    the entry point for the entire program.

    Attributes
    ----------
    gc_mode : int
        Indicates whether the gesture controller is running or not.
        1 if running, otherwise 0.
    cap : Object
        OpenCV object for capturing video frames from the camera.
    CAM_HEIGHT : int
        Height (in pixels) of the obtained video frame.
    CAM_WIDTH : int
        Width (in pixels) of the obtained video frame.
    hr_major : Object of 'HandRecog'
        Represents the major (dominant) hand.
    hr_minor : Object of 'HandRecog'
        Represents the minor (non-dominant) hand.
    dom_hand : bool
        True if the right hand is the dominant hand, otherwise False.
        Defaults to True.
    """

    # Class-level attributes (shared across all instances)
    gc_mode = 0  # Gesture controller mode (1 = running, 0 = stopped)
    cap = None  # OpenCV capture object for accessing the camera
    CAM_HEIGHT = None  # Camera frame height
    CAM_WIDTH = None  # Camera frame width
    hr_major = None  # Object representing the major (dominant) hand
    hr_minor = None  # Object representing the minor (non-dominant) hand
    dom_hand = True  # Default dominant hand (True = right hand)

    def __init__(self):
        """
        Initializes attributes and starts capturing video from the default camera.
        """
        GestureController.gc_mode = 1  # Enable gesture controller
        GestureController.cap = cv2.VideoCapture(0)  # Open the default camera (ID 0)
        
        # Get the height and width of the camera frame
        GestureController.CAM_HEIGHT = GestureController.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        GestureController.CAM_WIDTH = GestureController.cap.get(cv2.CAP_PROP_FRAME_WIDTH)

    @staticmethod
    def classify_hands(results):
        """
        Classifies detected hands as major (dominant) or minor (non-dominant)
        based on MediaPipe's hand tracking.

        Parameters
        ----------
        results : MediaPipe object
            The output from the MediaPipe hand detection model, containing 
            landmark information and handedness (left or right).
        
        Sets
        ----
        hr_major : Hand landmarks for the dominant hand.
        hr_minor : Hand landmarks for the non-dominant hand.
        """
        left, right = None, None  # Initialize left and right hand variables

        # Process the first detected hand
        try:
            handedness_dict = MessageToDict(results.multi_handedness[0])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[0]  # Assign to right hand
            else:
                left = results.multi_hand_landmarks[0]  # Assign to left hand
        except:
            pass  # No first hand detected

        # Process the second detected hand (if available)
        try:
            handedness_dict = MessageToDict(results.multi_handedness[1])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[1]  # Assign to right hand
            else:
                left = results.multi_hand_landmarks[1]  # Assign to left hand
        except:
            pass  # No second hand detected

        # Assign major and minor hand based on the dominant hand setting
        if GestureController.dom_hand:
            GestureController.hr_major = right
            GestureController.hr_minor = left
        else:
            GestureController.hr_major = left
            GestureController.hr_minor = right

    def start(self):
        """
        Entry point for the entire program. Captures video frames, processes 
        them using MediaPipe, classifies hands, and performs gesture-based 
        control.

        The function continuously reads frames from the camera, detects hands, 
        classifies them, and executes corresponding gestures until the program 
        is stopped.

        Stops when the 'Enter' key (key code 13) is pressed.
        """

        # Create objects to recognize gestures for major and minor hands
        handmajor = HandRecog(HLabel.MAJOR)
        handminor = HandRecog(HLabel.MINOR)

        # Initialize MediaPipe Hands module with specific detection and tracking confidence
        with mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
            while GestureController.cap.isOpened() and GestureController.gc_mode:
                success, image = GestureController.cap.read()  # Capture frame

                if not success:
                    print("Ignoring empty camera frame.")
                    continue  # Skip processing if the frame is empty
                
                # Flip the image horizontally and convert color from BGR to RGB (required by MediaPipe)
                image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
                image.flags.writeable = False  # Optimize performance for MediaPipe
                results = hands.process(image)  # Process the image with MediaPipe Hand Tracking
                
                # Convert image back to BGR for OpenCV display
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                if results.multi_hand_landmarks:  # If hands are detected
                    GestureController.classify_hands(results)  # Classify hands as major/minor
                    
                    # Update gesture recognition objects with current hand landmarks
                    handmajor.update_hand_result(GestureController.hr_major)
                    handminor.update_hand_result(GestureController.hr_minor)

                    # Determine finger state for both hands
                    handmajor.set_finger_state()
                    handminor.set_finger_state()

                    # Detect gestures for minor hand first
                    gest_name = handminor.get_gesture()

                    # If minor hand performs a pinch, use its gesture
                    if gest_name == Gest.PINCH_MINOR:
                        Controller.handle_controls(gest_name, handminor.hand_result)
                    else:
                        # Otherwise, use the major hand gesture
                        gest_name = handmajor.get_gesture()
                        Controller.handle_controls(gest_name, handmajor.hand_result)

                    # Draw hand landmarks on the image
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                else:
                    Controller.prev_hand = None  # Reset previous hand detection if no hands are found

                # Display the image with landmarks
                # cv2.imshow('Gesture Controller', image) 
                # Modified above code to prevent console window from popping up 
                cv2.namedWindow('Gesture Controller', cv2.WINDOW_NORMAL)
                cv2.imshow('Gesture Controller', image)

                # Break the loop when 'Enter' key (ASCII 13) is pressed
                if cv2.waitKey(5) & 0xFF == 13:
                    break

        # Release the camera and close all OpenCV windows
        GestureController.cap.release()
        cv2.destroyAllWindows()

# Uncomment the lines below to run the Gesture Controller directly
# gc1 = GestureController()
# gc1.start()
