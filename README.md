# PySceneDetect GUI, to EDIUS FCP7 XML

### Overview
EDIUS video editing software does not offer any scene or shot change detection tool (2024). With the help of various coding tools, I've created two GUI Python scripts to fill this gap:

1. **PySceneDetect_GUI_JSON.py**: A graphical user interface for the PySceneDetect tool by Brandon Castellano. PySceneDetect is used to detect shot changes in videos and can automatically split videos into separate clips. PySceneDetect itself doesn't have an official GUI, so this script provides an easy-to-use interface. PySceneDetect also only creates scene-cut data in a CSV file. My Python script extracts the scene-cut data from the CSV file and extracts detailed metadata from the video file using FFMPEG. It then combines this information into a JSON structure.

2. **JSON_to_EDIUS_FCP7XML.py**: A graphical user interface (GUI) for converting JSON files into XML files with a specific structure required by EDIUS Video Editing software.

3. **NEW CMD_SceneDetect_to_EDIUS_FCP7XML.py** This Python script can be run by Command Line or BAT file. It runs PySceneDetect SceneDetect to extract scene-cut data into a CSV file. The script then extracts the scene-cut data from the CSV file and extracts detailed metadata from the video file using FFMPEG. It then combines this information into a JSON structure. Then finally it reads the JSON file and creates an XML file with a specific structure required by EDIUS Video Editing software.

### Features

#### PySceneDetect_GUI_JSON
- **Set Input Video File Path**: The script uses filedialog to open dialogs for selecting a video file. 
- **Option To Split Video into separate clips and Save Images**:  Automatically split the video into separate clips using ffmpeg and saves an image of the first and last frame of each detected scene 
- **Start Time**: Default is set to 0 second.
- **Minimum Scene Length**: Default is set to 1 second.
- **Command Visibility**: The script enables visibility of the command execution in the CMD window.
- **Extract the scene cut data from the CSV file**: The python script extracts the scene cut data from the PySceneDetect CSV file and converts data for an EDIUS project.
- **Metadata Extraction**: Uses FFMPEG to extract detailed metadata from the video file, including:
  - File path URL
  - Duration in frames
  - NTSC status
  - Timebase (framerate)
  - Drop frame (DF) or non-drop frame (NDF)
  - First frame timecode
  - Pixel dimensions
  - Anamorphic status
  - Audio bit depth
  - Sample rate
  - Channel count
- **Combines Data & Output as JSON File**: Merges extracted metadata and scene-cut data from a CSV file into a JSON structure.

#### JSON_to_EDIUS_FCP7XML
- **Set Input JSON File Path**: Opens a file dialog for selecting the input JSON file and updates the file path text box.
- **Set Output XML File Path**: Opens a file dialog for selecting the save location of the output XML file and updates the file path text box.
- **Converts**: Reads the JSON file, constructs the XML structure, and saves the output XML file. Displays an error message if any issues occur during the process.
- **Creates XML Structure**: Creates the root XML structure and adds elements based on the JSON data.
  - add_rate: Adds rate elements with sub-elements from the JSON data.
  - add_rate: Adds rate elements with sub-elements from the JSON data.
  - add_clipitem: Adds clip items with various properties from the JSON data.
  - add_file_element: Adds file elements with properties from the JSON data.
  - add_video_format: Adds video format and sample characteristics from the JSON data.
  - add_audio_format: Adds audio format and sample characteristics from the JSON data.
  - add_audio_track: Adds audio tracks with clip items from the JSON data.
  - add_link_elements: Adds link elements to ensure proper video and audio synchronization. 

### Installation

1. **Download and install Python**
   The official Python website https://www.python.org/downloads/ When installing, select the Add python.exe to PATH checkbox, which enables users to launch Python from the command line.
2. **Download and Install PySceneDetect**
   https://github.com/Breakthrough/PySceneDetect/releases Ensure that PySceneDetect is installed and accessible in your system's PATH for this script to work correctly.
3. **Download and Install FFMPEG FFPROBE**
   The simplest way to install FFMPEG on Windows is to use a package manager like Chocolaty https://www.youtube.com/watch?v=EXOtQPf4s0I or without Chocolaty watch this video https://www.youtube.com/watch?v=JR36oH35Fgg
4. **Download My Python Files**
   Download PySceneDetect_GUI.py, PySceneDetect_CSV_to_JSON.py and JSON_to_EDIUS_FCP7XML.py scripts to a folder on your system drive
   
### Usage

**Caution**
Please try to understand what the script does, and keep in mind I'm not a programmer so there could be bugs. The script works Ok for me but there could be a risk of the script corrupting your video files or folders, so always back up before trying the script.

1. **PySceneDetect_GUI_JSON**
   Run the PySceneDetect_GUI.py script by double-clicking on the file. The GUI and CMD window should open. They might appear on top of each other, you can move them side-by-side but not after running the script. Use the interface to select the video file and configure the settings. Click "Start" to begin the scene detection process. PySceneDetect will output a scene cut data in a CSV file and the script will generate the JSON file with metadata. A message box will display "FINISHED" when done, and the GUI will close.
2. **JSON_to_EDIUS_FCP7XML**
    Run the JSON_to_EDIUS_FCP7XML.py by double-clicking on the file. The GUI might appear on top of the CMD window, you can move them side-by-side but not after running the script. Use the interface to Select JSON File: Click the "Select JSON File" button and choose the JSON file you want to convert. Select Save Location: Click the "Select Save Location" button and specify the location where you want to save the output XML file. A message box will display "Conversion successful" when done, and the GUI will close.

**CMD_SceneDetect_to_EDIUS_FCP7XML.py**
This Python script can be run by Command Line or BAT file. 
```bash
python combined_script.py --video_file path/to/video.mp4 --output_dir output_directory -- user_commands_here
```
The user commands are the same as PySceneDetect SceneDetect commands
**Examples**
1. Skip the first 10 seconds of the input video: 
```bash 
time --start 10s
```
with full command line
```bash
python combined_script.py --video_file path/to/video.mp4 --output_dir output_directory time --start 10s
```
2. Minimum length of any scene. TIMECODE can be specified as number of frames, time in seconds, or timecode. I use this all the time to prevent short clip cuts.
```bash
detect-content --min-scene-len 2s
```
```bash
python combined_script.py --video_file path/to/video.mp4 --output_dir output_directory detect-content --min-scene-len 2s
```
Make sure the output directory exists and is writable. The script runs PySceneDetect SceneDetect creates scene-cut data into a CSV file. The script then extracts the scene-cut data from the CSV file and extracts detailed metadata from the video file using FFMPEG. It then combines this information into a JSON structure. Then finally it reads the JSON file and creates an XML file with a specific structure required by EDIUS Video Editing software.
   
	
### Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes. I'm not a programmer or code writer, but a trained engineer and now a video editor with little free time to work on this project.

### Acknowledgements
Brandon Castellano for creating PySceneDetect.
The developers of FFMPEG for providing a powerful multimedia framework.
xml.etree.ElementTree for XML parsing and creating.
Copilot for assisting in the development of these scripts.	


