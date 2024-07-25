import tkinter as tk
from tkinter import filedialog, messagebox
import csv
import json
import os
import subprocess

class CSVtoJSON(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("PySceneDetect GUI and CSV to JSON file with metadata")
        self.geometry("600x400")

        # Video file selection
        self.video_file = tk.StringVar()
        tk.Label(self, text="Select Video File:").pack(pady=5)
        tk.Entry(self, textvariable=self.video_file, width=50).pack(pady=5)
        tk.Button(self, text="Browse Video", command=self.select_video_file).pack(pady=5)

        # Options
        self.split_video = tk.BooleanVar()
        self.save_images = tk.BooleanVar()
        self.start_seconds = tk.IntVar(value=0)
        self.min_scene_length = tk.IntVar(value=1)

        tk.Checkbutton(self, text="Split Video", variable=self.split_video).pack(pady=5)
        tk.Checkbutton(self, text="Save Images", variable=self.save_images).pack(pady=5)

        tk.Label(self, text="Skip first N seconds (time --start):").pack(pady=5)
        tk.Entry(self, textvariable=self.start_seconds).pack(pady=5)

        tk.Label(self, text="Minimum length of any scene (--min-scene-len):").pack(pady=5)
        tk.Entry(self, textvariable=self.min_scene_length).pack(pady=5)

        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Process", command=self.process).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Cancel", command=self.quit).pack(side=tk.LEFT, padx=10)

    def select_video_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov")])
        if file_path:
            self.video_file.set(file_path)

    def process(self):
        video_file = self.video_file.get()
        if not video_file:
            messagebox.showerror("Error", "Please select a video file.")
            return

        # Check ffmpeg and ffprobe availability
        if not self.check_ffmpeg_ffprobe():
            messagebox.showerror("Error", "ffmpeg or ffprobe is unavailable. Please check if their path has been added to the Environment Variables.")
            self.quit()
            return

        try:
            # Check write permissions for the output directory
            output_dir = os.path.dirname(video_file)
            if not os.access(output_dir, os.W_OK):
                raise PermissionError(f"No write permission to the directory: {output_dir}")

            # Run PySceneDetect
            self.run_pyscenedetect(video_file, output_dir)

            # Convert CSV to JSON with metadata
            self.convert_csv_to_json(video_file, output_dir)

            messagebox.showinfo("Finished", f"Processing successful. JSON saved in the same directory as the video file.")
            self.quit()
        except PermissionError as e:
            messagebox.showerror("Permission Error", str(e))
            self.quit()
        except Exception as e:
            messagebox.showerror("Error", f"Error occurred: {str(e)}")

    def check_ffmpeg_ffprobe(self):
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

    def run_pyscenedetect(self, video_file, output_dir):
        output_csv = os.path.join(output_dir, os.path.splitext(os.path.basename(video_file))[0] + "-Scenes.csv")

        # Construct the command for PySceneDetect
        cmd = f'scenedetect --input "{video_file}" --output "{output_dir}" --min-scene-len {self.min_scene_length.get()}s detect-content list-scenes'

        if self.start_seconds.get() > 0:
            cmd += f' time --start {self.start_seconds.get()}s'

        if self.split_video.get():
            cmd += ' split-video'

        if self.save_images.get():
            cmd += ' save-images'

        # Print the command for debugging purposes
        print(f"Running command: {cmd}")

        # Execute the command
        subprocess.run(cmd, shell=True, check=True)

    def convert_csv_to_json(self, video_file, output_dir):
        csv_file = os.path.join(output_dir, os.path.splitext(os.path.basename(video_file))[0] + "-Scenes.csv")
        json_file = os.path.join(output_dir, os.path.splitext(os.path.basename(video_file))[0] + "-Scenes.json")

        clips = []
        with open(csv_file, mode='r', newline='') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the first line
            headers = next(reader)  # Read the second line as headers
            for row in reader:
                row_dict = dict(zip(headers, row))
                clip = {
                    "id": row_dict["Scene Number"],
                    "start": int(row_dict["Start Frame"]) - 1,
                    "end": int(row_dict["End Frame"])
                }
                clips.append(clip)

        video_data = self.extract_video_info(video_file)
        combined_data = video_data
        combined_data["clips"] = clips

        with open(json_file, mode='w') as file:
            json.dump(combined_data, file, indent=4)

    def extract_video_info(self, video_file):
        cmd = [
            "ffprobe", "-v", "error", "-show_streams", "-show_format",
            "-of", "json", video_file
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        ffprobe_output = json.loads(result.stdout)

        video_stream = next((stream for stream in ffprobe_output["streams"] if stream["codec_type"] == "video"), None)
        audio_stream = next((stream for stream in ffprobe_output["streams"] if stream["codec_type"] == "audio"), None)

        if not video_stream:
            raise ValueError("Video stream not found in the file.")

        frame_rate_str = video_stream["r_frame_rate"]
        frame_rate = eval(frame_rate_str)
        duration_seconds = float(video_stream["duration"])
        duration_frames = int(duration_seconds * frame_rate)

        # Extract the start timecode using ffprobe
        timecode = "00:00:00:00"  # Default value
        try:
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                "format_tags=timecode", "-of", "default=noprint_wrappers=1:nokey=1", video_file
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if result.stdout.strip():
                timecode = result.stdout.strip()
        except Exception as e:
            print(f"Could not extract timecode: {e}")

        video_metadata = {
            "sequence": {
                "name": os.path.splitext(os.path.basename(video_file))[0]
            },
            "video": {
                "file": {
                    "name": os.path.basename(video_file),
                    "pathurl": os.path.abspath(video_file).replace("\\", "/"),
                    "media": {
                        "video": {
                            "duration": duration_frames,
                            "timecode": {
                                "rate": {
                                    "ntsc": "TRUE" if frame_rate in [23.976, 29.97, 59.94] else "FALSE",
                                    "timebase": int(frame_rate) if isinstance(frame_rate, int) else frame_rate
                                },
                                "displayformat": "DF" if frame_rate in [29.97, 59.94] else "NDF",
                                "first_timecode": timecode  # Timecode of the first frame
                            },
                            "samplecharacteristics": {
                                "width": video_stream["width"],
                                "height": video_stream["height"],
                                "anamorphic": "TRUE" if video_stream["display_aspect_ratio"] != "16:9" and video_stream["width"] <= 768 else "FALSE",
                                "pixelaspectratio": "Square"
                            }
                        }
                    }
                }
            }
        }

        if audio_stream:
            video_metadata["video"]["file"]["media"]["audio"] = {
                "samplecharacteristics": {
                    "depth": audio_stream.get("bits_per_raw_sample", 16),
                    "samplerate": audio_stream["sample_rate"]
                },
                "channelcount": audio_stream["channels"]
            }

        return video_metadata

if __name__ == "__main__":
    app = CSVtoJSON()
    app.mainloop()
