import socket
from flask import Flask, Response
import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import threading
from datetime import datetime

# Function to get the local IP address
def get_local_ip():
    try:
        # Create a socket to get the IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to a public DNS server
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        return "127.0.0.1"  # Fallback to localhost if there's an error

# Initialize Flask app
app = Flask(__name__)

# Load TFLite model
interpreter = tflite.Interpreter(model_path="./tflite_model/detect.tflite")
interpreter.allocate_tensors()

# Load labels
with open("./tflite_model/labelmap.txt", "r") as f:
    labels = [line.strip() for line in f.readlines()]

# Get model input details
input_details = interpreter.get_input_details()
input_shape = input_details[0]['shape']  # Expected shape (1, 300, 300, 3)
input_dtype = input_details[0]['dtype']  # Check expected dtype (UINT8)

# Initialize Camera
cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))  # Use YUYV format
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Global variables for frame, lock, recording, and video writer
frame_lock = threading.Lock()
current_frame = None
processed_frame = None
recording = False
video_writer = None

def capture_frames():
    global current_frame
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        with frame_lock:
            current_frame = frame

def process_frames():
    global current_frame, processed_frame, recording, video_writer
    while True:
        with frame_lock:
            if current_frame is None:
                continue
            frame = current_frame.copy()

        # Preprocess frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
        input_data = cv2.resize(frame_rgb, (input_shape[1], input_shape[2]))  # Resize
        input_data = np.expand_dims(input_data, axis=0)  # Add batch dimension

        # Ensure correct dtype
        if input_dtype == np.uint8:
            input_data = input_data.astype(np.uint8)  # Convert to UINT8
        else:
            input_data = input_data.astype(np.float32) / 255.0  # Normalize for FLOAT32 models

        # Run inference
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()

        # Get detection results
        output_details = interpreter.get_output_details()
        boxes = interpreter.get_tensor(output_details[0]['index'])[0]
        classes = interpreter.get_tensor(output_details[1]['index'])[0]
        scores = interpreter.get_tensor(output_details[2]['index'])[0]

        # Draw bounding boxes
        for i in range(len(scores)):
            if scores[i] > 0.5:  # Confidence threshold
                y1, x1, y2, x2 = boxes[i]
                label = f"{labels[int(classes[i])]}: {scores[i]:.2f}"
                
                # Convert normalized coordinates to image size
                x1, y1, x2, y2 = (int(x1 * frame.shape[1]), int(y1 * frame.shape[0]),
                                  int(x2 * frame.shape[1]), int(y2 * frame.shape[0]))
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Update the processed frame
        with frame_lock:
            processed_frame = frame.copy()

        # If recording is enabled, write the processed frame to the video file
        if recording and video_writer is not None:
            video_writer.write(processed_frame)

def generate_frames():
    global processed_frame
    while True:
        with frame_lock:
            if processed_frame is None:
                continue
            frame = processed_frame.copy()

        # Encode the frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        # Yield the frame in byte format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    # Return the response generated by the generate_frames function
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_record')
def start_record():
    global recording, video_writer
    if not recording:
        # Generate a unique filename using the current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = f"recorded_video_{timestamp}.mp4"
        
        # Initialize the video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for .mp4
        fps = 30  # Frames per second
        frame_size = (640, 480)  # Frame size (width, height)
        video_writer = cv2.VideoWriter(video_filename, fourcc, fps, frame_size)
        
        recording = True
        return f"Recording started. Saving to {video_filename}"
    else:
        return "Recording is already in progress."

@app.route('/stop_record')
def stop_record():
    global recording, video_writer
    if recording:
        recording = False
        if video_writer is not None:
            video_writer.release()
            video_writer = None
        return "Recording stopped and video saved."
    else:
        return "No recording in progress."

@app.route('/')
def index():
    # HTML page to display the video stream and IP address
    ip_address = get_local_ip()
    return f"""
    <html>
      <head>
        <title>Object Detection Stream</title>
      </head>
      <body>
        <h1>Object Detection Stream</h1>
        <p>Access this stream from another device using:</p>
        <p><strong>http://{ip_address}:5000/video_feed</strong></p>
        <p><a href="/start_record">Start Recording</a></p>
        <p><a href="/stop_record">Stop Recording</a></p>
        <img src="/video_feed" />
      </body>
    </html>
    """

if __name__ == '__main__':
    # Get the local IP address
    ip_address = get_local_ip()
    print(f"Server running on http://{ip_address}:5000")
    
    # Start the frame capture and processing threads
    threading.Thread(target=capture_frames, daemon=True).start()
    threading.Thread(target=process_frames, daemon=True).start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)
