import cv2
import os
import psutil
import customtkinter as ctk
from PIL import Image, ImageTk
import win32com.client
import threading
import time
from tkinter import messagebox
import subprocess
import shutil
import random
import numpy as np
import win32gui
import win32process
import pickle
from ultralytics import YOLO
from facenet_pytorch import InceptionResnetV1
import torch
import torchvision.transforms as transforms
from PIL import Image as PILImage

# Set the appearance mode and color theme for the GUI
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def load_facenet_model():
    try:
        return InceptionResnetV1(pretrained='vggface2').eval()
    except Exception as e:
        # Try to delete corrupted vggface2 weights from torch cache
        import glob
        cache_dirs = [
            os.path.expanduser('~/.cache/torch/hub/checkpoints'),
            os.path.expanduser('~/.torch/facenet'),
            os.path.expanduser('~/.cache/torch/checkpoints'),
        ]
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                for fname in os.listdir(cache_dir):
                    if 'vggface2' in fname and fname.endswith('.pt'):
                        try:
                            os.remove(os.path.join(cache_dir, fname))
                        except Exception:
                            pass
        # Try again to download and load the model
        return InceptionResnetV1(pretrained='vggface2').eval()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Set up the main window
        self.title("Program Lock with Face Recognition")
        self.geometry("800x600")

        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        # Add logo label to sidebar
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Main Menu", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Add buttons to sidebar
        self.lock_button = ctk.CTkButton(self.sidebar_frame, text="Lock Programs", command=self.lock_all_programs)
        self.lock_button.grid(row=1, column=0, padx=20, pady=10)

        self.unlock_button = ctk.CTkButton(self.sidebar_frame, text="Unlock Programs", command=self.unlock_all_programs)
        self.unlock_button.grid(row=2, column=0, padx=20, pady=10)

        self.create_dataset_button = ctk.CTkButton(self.sidebar_frame, text="Create Dataset", command=self.create_dataset)
        self.create_dataset_button.grid(row=3, column=0, padx=20, pady=10)

        self.train_model_button = ctk.CTkButton(self.sidebar_frame, text="Train Model", command=self.train_model)
        self.train_model_button.grid(row=4, column=0, padx=20, pady=10)

        # Add appearance mode options
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                             command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))

        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Create scrollable frame for app list
        self.scrollable_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Initialize variables
        self.app_buttons = []
        self.locked_apps = []
        self.is_locked = False
        self.program_states = {}
        self.app_paths_to_names = {}  # Map full paths to process names
        self.app_paths_to_exes = {}   # Map full paths to executable names

        # Define project paths
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.dataset_dir = os.path.join(self.base_dir, "dataset")
        self.models_dir = os.path.join(self.base_dir, "models")
        self.faces_path = os.path.join(self.models_dir, "faces.pkl")

        # Create necessary directories
        for directory in [self.dataset_dir, self.models_dir]:
            os.makedirs(directory, exist_ok=True)

        # Load YOLO model for face detection
        self.yolo_model = YOLO("yolov8n-face.pt")
        # Load FaceNet for face recognition (with robust loader)
        self.facenet = load_facenet_model()
        # Load face embeddings and labels if available
        if os.path.exists(self.faces_path):
            with open(self.faces_path, 'rb') as f:
                data = pickle.load(f)
                self.face_embeddings = data['embeddings']
                self.face_labels = data['labels']
        else:
            self.face_embeddings = np.array([])
            self.face_labels = []

        # Load desktop apps
        self.load_desktop_apps()

        # Initialize face detection model
        # try:
        #     # Load OpenCV's Haar Cascade face detector
        #     haar_cascade_path = os.path.join(self.models_dir, "haarcascade_frontalface_default.xml")
            
        #     # Check if the cascade file exists, if not download it
        #     if not os.path.exists(haar_cascade_path):
        #         messagebox.showinfo("First Run", "First-time setup: Downloading required face model...")
        #         self.download_haar_cascade(haar_cascade_path)
            
        #     self.face_detector = cv2.CascadeClassifier(haar_cascade_path)
            
        #     # Initialize LBPH Face Recognizer
        #     self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
            
        #     # Load face recognition model if it exists
        #     if os.path.exists(self.face_model_path):
        #         self.face_recognizer.read(self.face_model_path)
                
        #         # Load face labels
        #         if os.path.exists(self.faces_path):
        #             with open(self.faces_path, 'rb') as f:
        #                 self.faces_data = pickle.load(f)
        #             print(f"Loaded face recognition model with {len(self.faces_data['faces'])} faces")
        #         else:
        #             self.faces_data = {'faces': [], 'labels': []}
        #     else:
        #         self.faces_data = {'faces': [], 'labels': []}
            
        # except Exception as e:
        #     messagebox.showerror("Error", f"Failed to initialize face recognition: {str(e)}")
            
        # Start monitoring thread
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self.monitor_locked_programs, daemon=True)
        self.monitor_thread.start()
    
    def download_haar_cascade(self, output_path):
        """Download the Haar Cascade face detector"""
        try:
            import requests
            
            # URL for the pre-trained Haar Cascade
            url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
            
            # Create a progress window
            progress_window = ctk.CTkToplevel(self)
            progress_window.title("Downloading Model")
            progress_window.geometry("400x150")
            progress_window.transient(self)
            progress_window.grab_set()
            
            progress_label = ctk.CTkLabel(progress_window, text="Downloading face model...")
            progress_label.pack(pady=20)
            
            progress_bar = ctk.CTkProgressBar(progress_window)
            progress_bar.pack(pady=10, padx=20, fill="x")
            progress_bar.set(0)
            
            # Download the file
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            # Download with progress
            downloaded = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = min(1.0, downloaded / total_size)
                        progress_bar.set(progress)
                        progress_window.update()
            
            progress_window.destroy()
            messagebox.showinfo("Download Complete", "Face model downloaded successfully!")
            
        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to download model: {str(e)}")
            raise e

    def load_desktop_apps(self):
        """Load and display desktop apps in the scrollable frame"""
        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = shell.SpecialFolders("Desktop")
        
        # Clear any existing buttons
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.app_buttons = []
        
        # Get desktop shortcuts
        shortcuts = []
        for filename in os.listdir(desktop):
            if filename.endswith('.lnk'):
                shortcuts.append(os.path.join(desktop, filename))
        
        # Sort the shortcuts by name
        shortcuts.sort(key=lambda x: os.path.basename(x).lower())
        
        # Display shortcuts in the scrollable frame
        for shortcut_path in shortcuts:
            filename = os.path.basename(shortcut_path)
            shortcut = shell.CreateShortCut(shortcut_path)
            app_path = shortcut.Targetpath
            app_name = os.path.splitext(filename)[0]
            
            # Store the mapping of app path to process executable name
            exe_name = os.path.basename(app_path)
            self.app_paths_to_exes[app_path] = exe_name
            self.app_paths_to_names[app_path] = app_name
            
            try:
                icon_path = shortcut.IconLocation.split(',')[0]
                if icon_path and os.path.exists(icon_path):
                    icon = Image.open(icon_path)
                    icon = icon.resize((32, 32))
                    icon = ctk.CTkImage(light_image=icon, dark_image=icon, size=(32, 32))
                else:
                    icon = None
            except:
                icon = None

            app_frame = ctk.CTkFrame(self.scrollable_frame)
            app_frame.grid(sticky="ew", padx=5, pady=5)
            app_frame.grid_columnconfigure(1, weight=1)

            if icon:
                icon_label = ctk.CTkLabel(app_frame, image=icon, text="")
                icon_label.grid(row=0, column=0, padx=5, pady=5)

            app_button = ctk.CTkCheckBox(app_frame, text=app_name, command=lambda path=app_path: self.toggle_app_lock(path))
            app_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")
            
            # Check if this app is already in locked_apps and set the checkbox state
            if app_path in self.locked_apps:
                app_button.select()

            self.app_buttons.append((app_button, app_path))

    def toggle_app_lock(self, app_path):
        """Toggle lock status for an app"""
        if app_path in self.locked_apps:
            self.locked_apps.remove(app_path)
        else:
            self.locked_apps.append(app_path)
            # Initialize the program state as unauthorized until face recognition succeeds
            self.program_states[app_path] = False

    def lock_all_programs(self):
        """Lock all selected programs"""
        if not self.locked_apps:
            messagebox.showinfo("Notification", "No programs selected to lock.")
            return
            
        # Check if we have face recognition model before locking
        if not os.path.exists(self.faces_path) or len(self.face_embeddings) == 0:
            if messagebox.askyesno("Warning", "No authorized faces have been trained. Would you like to create a dataset and train the model first?"):
                self.create_dataset()
                return
        
        # Close any running instances of locked programs
        for app_path in self.locked_apps:
            exe_name = self.app_paths_to_exes.get(app_path)
            if exe_name and self.is_program_running(exe_name):
                self.terminate_program(exe_name)
                
        self.is_locked = True
        
        # Initialize all program states as unauthorized
        for app_path in self.locked_apps:
            self.program_states[app_path] = False
            
        messagebox.showinfo("Notification", "Selected programs have been locked.")

    def unlock_all_programs(self):
        """Attempt to unlock all programs using face recognition"""
        if not self.is_locked:
            messagebox.showinfo("Notification", "No programs are currently locked.")
            return
            
        if self.face_recognition():
            self.is_locked = False
            self.program_states.clear()
            messagebox.showinfo("Notification", "Face recognized. Programs unlocked.")
        else:
            messagebox.showwarning("Warning", "Face not recognized. Programs remain locked.")

    def is_program_running(self, exe_name):
        """Check if a program is currently running by executable name"""
        for proc in psutil.process_iter(['name', 'exe']):
            proc_name = proc.info.get('name', '')
            proc_exe = proc.info.get('exe', '')
            
            # Check if process name matches the executable name
            if proc_name.lower() == exe_name.lower():
                return True
                
            # Also check if the executable path ends with our exe name
            if proc_exe and os.path.basename(proc_exe).lower() == exe_name.lower():
                return True
                
        return False

    def get_processes_for_exe(self, exe_name):
        """Get list of process IDs for a given executable name"""
        pids = []
        for proc in psutil.process_iter(['name', 'exe', 'pid']):
            try:
                proc_name = proc.info.get('name', '')
                proc_exe = proc.info.get('exe', '')
                
                # Check both process name and executable path
                if (proc_name.lower() == exe_name.lower() or 
                   (proc_exe and os.path.basename(proc_exe).lower() == exe_name.lower())):
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return pids

    def terminate_program(self, exe_name):
        """Terminate all instances of a program by executable name"""
        pids = self.get_processes_for_exe(exe_name)
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                # Wait briefly to see if termination worked
                gone, still_alive = psutil.wait_procs([proc], timeout=1)
                if still_alive:
                    # If still alive, force kill
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def detect_faces_yolo(self, frame):
        results = self.yolo_model(frame)
        faces = []
        for box in results[0].boxes.xyxy.cpu().numpy():
            x1, y1, x2, y2 = map(int, box)
            faces.append((x1, y1, x2-x1, y2-y1))
        return faces

    def get_face_embedding(self, face_img):
        img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        img = PILImage.fromarray(img)
        transform = transforms.Compose([
            transforms.Resize((160, 160)),
            transforms.ToTensor(),
            transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
        ])
        img_tensor = transform(img).unsqueeze(0)
        with torch.no_grad():
            embedding = self.facenet(img_tensor).cpu().numpy()[0]
        return embedding

    def face_recognition(self):
        if not hasattr(self, 'face_embeddings') or len(self.face_embeddings) == 0:
            messagebox.showwarning("Warning", "No authorized faces found. Please create a dataset and train the model first.")
            return False
        vid_cam = cv2.VideoCapture(0)
        if not vid_cam.isOpened():
            messagebox.showerror("Error", "Could not open camera.")
            return False
        start_time = time.time()
        recognition_count = 0
        required_recognitions = 3
        threshold = 0.8  # Lower is stricter
        while time.time() - start_time < 10:
            ret, frame = vid_cam.read()
            if not ret:
                continue
            faces = self.detect_faces_yolo(frame)
            for (x, y, w, h) in faces:
                face_roi = frame[y:y+h, x:x+w]
                if face_roi.shape[0] < 10 or face_roi.shape[1] < 10:
                    continue
                embedding = self.get_face_embedding(face_roi)
                distances = np.linalg.norm(self.face_embeddings - embedding, axis=1)
                min_idx = np.argmin(distances)
                min_dist = distances[min_idx]
                if min_dist < threshold:
                    recognition_count += 1
                    label = self.face_labels[min_idx]
                    cv2.putText(frame, f"Authorized: {label}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "Unauthorized", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            cv2.imshow('Face Recognition', frame)
            if recognition_count >= required_recognitions:
                vid_cam.release()
                cv2.destroyAllWindows()
                return True
            if cv2.waitKey(100) & 0xFF == 27:
                break
        vid_cam.release()
        cv2.destroyAllWindows()
        return False

    def get_window_process_name(self, hwnd):
        """Get process name from window handle"""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name()
        except:
            return None

    def find_windows_for_program(self, exe_name):
        """Find all window handles for a given program executable name"""
        result = []
        
        def callback(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                proc_name = self.get_window_process_name(hwnd)
                if proc_name and proc_name.lower() == exe_name.lower():
                    result.append(hwnd)
            return True
            
        win32gui.EnumWindows(callback, None)
        return result

    def monitor_locked_programs(self):
        """Monitor locked programs with improved detection"""
        while self.monitoring_active:
            if self.is_locked:
                # Check each locked app
                for app_path in self.locked_apps:
                    exe_name = self.app_paths_to_exes.get(app_path)
                    app_name = self.app_paths_to_names.get(app_path)
                    
                    if not exe_name:
                        continue
                        
                    # Check if the program is running and not authorized
                    if self.is_program_running(exe_name) and not self.program_states.get(app_path, False):
                        # Find all windows for this program
                        windows = self.find_windows_for_program(exe_name)
                        
                        if windows:
                            # Program is running and has visible windows - needs authentication
                            self.handle_unauthorized_access(app_path, exe_name, app_name)
            
            # Check more frequently to catch applications as they start
            time.sleep(0.2)

    def handle_unauthorized_access(self, app_path, exe_name, app_name):
        """Handle unauthorized access to a locked program"""
        try:
            # Terminate all instances of the program
            self.terminate_program(exe_name)
            
            # Notify the user
            messagebox.showwarning(
                "Unauthorized Access",
                f"Access to {app_name} blocked! Face recognition required."
            )
            
            # Perform face recognition
            if self.face_recognition():
                # On successful recognition, authorize the program and launch it
                self.program_states[app_path] = True
                subprocess.Popen(app_path)
                messagebox.showinfo("Access Granted", f"Access to {app_name} granted!")
            else:
                # Keep the program unauthorized
                self.program_states[app_path] = False
                messagebox.showwarning(
                    "Access Denied", 
                    f"Access to {app_name} denied! Face not recognized."
                )
        except Exception as e:
            print(f"Error handling unauthorized access: {str(e)}")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        """Change the appearance mode of the GUI"""
        ctk.set_appearance_mode(new_appearance_mode)

    def preprocess_face(self, frame, face_rect):
        """Preprocess a detected face for better recognition"""
        (x, y, w, h) = face_rect
        face = frame[y:y+h, x:x+w]
        
        # Convert to grayscale
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        
        # Normalize for lighting conditions
        gray = cv2.equalizeHist(gray)
        
        # Resize to standard size
        resized = cv2.resize(gray, (100, 100))
        
        return resized
        
    def create_dataset(self):
        try:
            os.makedirs(self.dataset_dir, exist_ok=True)
            test_file_path = os.path.join(self.dataset_dir, "test_write.txt")
            try:
                with open(test_file_path, 'w') as f:
                    f.write("test")
                os.remove(test_file_path)
            except PermissionError:
                messagebox.showerror(
                    "Permission Error",
                    "Cannot write to dataset directory. Please run the application as administrator or change the dataset location."
                )
                return
            for file in os.listdir(self.dataset_dir):
                file_path = os.path.join(self.dataset_dir, file)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except PermissionError:
                        messagebox.showwarning("Warning", f"Could not remove old file {file}. Continuing anyway.")
            vid_cam = cv2.VideoCapture(0)
            if not vid_cam.isOpened():
                messagebox.showerror("Error", "Could not open camera.")
                return
            face_images = []
            count = 0
            total_images = 20
            progress_window = ctk.CTkToplevel(self)
            progress_window.title("Creating Dataset")
            progress_window.geometry("400x150")
            progress_window.transient(self)
            progress_window.grab_set()
            progress_label = ctk.CTkLabel(progress_window, text="Capturing face images...")
            progress_label.pack(pady=20)
            progress_bar = ctk.CTkProgressBar(progress_window)
            progress_bar.pack(pady=10, padx=20, fill="x")
            progress_bar.set(0)
            def update_progress(current_count):
                progress = current_count / total_images
                progress_bar.set(progress)
                progress_label.configure(text=f"Capturing face images: {current_count}/{total_images}")
            last_capture_time = time.time() - 0.5
            capture_interval = 0.5
            while True:
                ret, frame = vid_cam.read()
                if not ret:
                    continue
                cv2.putText(
                    frame,
                    f"Capturing: {count}/{total_images} - Move your face to different positions",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
                )
                faces = self.detect_faces_yolo(frame)
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    current_time = time.time()
                    if current_time - last_capture_time >= capture_interval and count < total_images:
                        last_capture_time = current_time
                        face_img = frame[y:y+h, x:x+w]
                        if face_img.shape[0] < 10 or face_img.shape[1] < 10:
                            continue
                        face_images.append(face_img)
                        count += 1
                        update_progress(count)
                        face_image_path = os.path.join(self.dataset_dir, f"face_{count}.jpg")
                        cv2.imwrite(face_image_path, face_img)
                cv2.imshow('Creating Dataset', frame)
                if cv2.waitKey(1) & 0xFF == 27 or count >= total_images:
                    break
            vid_cam.release()
            cv2.destroyAllWindows()
            if face_images:
                embeddings = []
                labels = []
                for face_img in face_images:
                    embedding = self.get_face_embedding(face_img)
                    embeddings.append(embedding)
                    labels.append("user")
                embeddings = np.array(embeddings)
                with open(self.faces_path, 'wb') as f:
                    pickle.dump({'embeddings': embeddings, 'labels': labels}, f)
                self.face_embeddings = embeddings
                self.face_labels = labels
                progress_window.destroy()
                messagebox.showinfo(
                    "Dataset Creation",
                    f"Dataset created successfully with {len(face_images)} face images."
                )
            else:
                progress_window.destroy()
                messagebox.showwarning(
                    "Dataset Creation",
                    "No faces were detected. Please try again with better lighting."
                )
        except Exception as e:
            messagebox.showerror("Error", f"Error creating dataset: {str(e)}")
            try:
                vid_cam.release()
                cv2.destroyAllWindows()
                progress_window.destroy()
            except:
                pass

    def train_model(self):
        # در این نسخه، train_model فقط دیتاست را دوباره بارگذاری می‌کند
        if os.path.exists(self.faces_path):
            with open(self.faces_path, 'rb') as f:
                data = pickle.load(f)
                self.face_embeddings = data['embeddings']
                self.face_labels = data['labels']
            messagebox.showinfo("Training Complete", f"Face recognition model loaded successfully with {len(self.face_embeddings)} embeddings.")
        else:
            messagebox.showinfo("Training", "No face embeddings found in dataset. Creating new dataset...")
            self.create_dataset()
            
    def on_closing(self):
        """Handle window closing event"""
        # Stop the monitoring thread
        self.monitoring_active = False
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()