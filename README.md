
# 🔒 FaceLock: Face Recognition-Based Application Locker

FaceLock is a Windows desktop application built with Python that enables users to **lock and unlock selected programs** using **real-time face recognition**. This powerful tool is especially useful for securing sensitive applications from unauthorized access on shared computers.

## 🚀 Features

- 🔐 **Lock any desktop application** from being launched unless authorized via face recognition.
- 👁️ **Real-time face detection** using YOLOv8 and recognition using FaceNet.
- 🎥 **Dataset collection** and **model training** through your webcam in an intuitive GUI.
- 💻 Built using `CustomTkinter` for a modern UI.
- 📂 Automatic detection of shortcut icons on the desktop.
- 👤 Supports **multi-face embedding** storage and recognition.
- 🧠 Lightweight monitoring system that prevents and terminates unauthorized app usage.

## 🧠 How it works

1. **Create Dataset**: Capture your face using your webcam. The app collects 20 images and generates embeddings.
2. **Train Model**: Face embeddings are stored and used for future verification.
3. **Select Applications**: Choose desktop shortcuts to lock via the GUI.
4. **Lock Applications**: When locked, launching the selected programs triggers face authentication.
5. **Face Recognition**: If your face is recognized, the program is allowed to launch. Otherwise, it is forcefully closed.

## 📦 Technologies Used

- Python 3
- [YOLOv8-Face](https://github.com/derronqi/yolov8-face) for face detection
- [FaceNet (facenet-pytorch)](https://github.com/timesler/facenet-pytorch) for face recognition
- `CustomTkinter` for GUI
- `OpenCV` for camera and image processing
- `psutil`, `subprocess`, `win32com.client` for system and process control

## 📸 Screenshots

![App Screenshot](screenshot.png)


## ⚙️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/amir-rs/Lock-Unlock-Laptop-PC-Face-Recongnition.git
   cd FaceLock


2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   python app.py
   ```

## 📝 Notes

* This project is designed for **Windows only** due to dependencies like `pywin32`.
* If the YOLOv8 model is not present, it will be downloaded automatically.
* Run as Administrator if you face permission issues with killing processes or accessing app paths.

## 📁 Directory Structure

```
FaceLock/
├── app.py                 # Main application file
├── dataset/               # Captured face images
├── models/
│   └── faces.pkl          # Stored face embeddings
├── yolov8n-face.pt        # YOLOv8 face detection model
└── README.md              # Project documentation
```

## 🛡️ License

This project is licensed under the MIT License.

