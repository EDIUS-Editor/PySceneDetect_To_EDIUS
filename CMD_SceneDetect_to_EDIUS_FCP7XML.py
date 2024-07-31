import csv
import json
import os
import subprocess
import argparse
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

def check_ffmpeg_ffprobe():
    """Check if ffmpeg and ffprobe are installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["ffprobe", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_pyscenedetect(video_file, output_dir, user_commands):
    """Run PySceneDetect with the provided commands."""
    command = ["scenedetect", "-i", video_file, "-o", output_dir] + user_commands + ["detect-content", "list-scenes"]
    print("Running command:", " ".join(command))
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running PySceneDetect: {e}")
        exit(1)

def convert_csv_to_json(video_file, output_dir):
    """Convert CSV output from PySceneDetect to JSON format."""
    base_name = os.path.splitext(os.path.basename(video_file))[0]
    csv_file = os.path.join(output_dir, f"{base_name}-Scenes.csv")
    json_file = os.path.join(output_dir, f"{base_name}-Scenes.json")

    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' does not exist.")
        exit(1)

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

    video_data = extract_video_info(video_file)
    combined_data = video_data
    combined_data["clips"] = clips

    with open(json_file, mode='w') as file:
        json.dump(combined_data, file, indent=4)

    return json_file  # Return the path of the JSON file for further processing

def extract_video_info(video_file):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "stream=index,codec_type,width,height,display_aspect_ratio,r_frame_rate,duration,sample_rate,channels,bits_per_raw_sample",
        "-of", "json", video_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    ffprobe_output = json.loads(result.stdout)

    video_stream = next((stream for stream in ffprobe_output["streams"] if stream["codec_type"] == "video"), None)
    audio_stream = next((stream for stream in ffprobe_output["streams"] if stream["codec_type"] == "audio"), None)

    if not video_stream:
        raise ValueError("Video stream not found in the file.")

    frame_rate_str = video_stream["r_frame_rate"]
    frame_rate = round(eval(frame_rate_str))
    duration_seconds = float(video_stream["duration"])
    duration_frames = int(duration_seconds * frame_rate)
    anamorphic = "TRUE" if video_stream.get("display_aspect_ratio", "16:9") != "16:9" else "FALSE"

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

    video_info = {
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
                                "ntsc": "TRUE" if frame_rate in [23.976, 23.976023976023978, 29.97, 29.976023976023978, 59.94] else "FALSE",
                                "timebase": int(frame_rate) if isinstance(frame_rate, int) else frame_rate
                            },
                            "displayformat": "DF" if frame_rate in [29.97, 59.94] else "NDF",
                            "first_timecode": timecode  # Timecode of the first frame
                        },
                        "samplecharacteristics": {
                            "width": video_stream["width"],
                            "height": video_stream["height"],
                            "anamorphic": anamorphic, 
                            "pixelaspectratio": "Square"
                        }
                    }
                }
            }
        }
    }

    if audio_stream:
        video_info["video"]["file"]["media"]["audio"] = {
            "samplecharacteristics": {
                "depth": audio_stream.get("bits_per_raw_sample", 16),
                "samplerate": audio_stream.get("sample_rate", "N/A")
            },
            "channelcount": audio_stream.get("channels", "N/A")
        }

    return video_info

def convert_json_to_xml(json_file_path, xml_file_path):
    try:
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)
            root = create_xml_structure(data)
            tree_str = ET.tostring(root, encoding='utf-8')
            pretty_xml_as_string = parseString(tree_str).toprettyxml(indent="  ")
            # Add XML declaration and doctype
            xml_content = '<?xml version="1.0" ?>\n<!DOCTYPE xmeml>\n' + pretty_xml_as_string.split('?>', 1)[1].strip()
            with open(xml_file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            print("Conversion completed successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")

def create_xml_structure(data):
    # Root element
    root = ET.Element("xmeml", version="5")
    
    # Sequence element
    sequence = ET.SubElement(root, "sequence", id="sequence-1")
    
    # Sequence name from JSON
    ET.SubElement(sequence, "name").text = data["sequence"]["name"]
    
    # Duration from JSON
    ET.SubElement(sequence, "duration").text = str(data["video"]["file"]["media"]["video"]["duration"])
    
    # Add rate element
    add_rate(sequence, data["video"]["file"]["media"]["video"]["timecode"]["rate"])

    # Timecode element
    timecode = ET.SubElement(sequence, "timecode")
    add_rate(timecode, data["video"]["file"]["media"]["video"]["timecode"]["rate"])
    
    # Default timecode settings
    ET.SubElement(timecode, "string").text = "00:00:00:00"
    ET.SubElement(timecode, "frame").text = "0"
    ET.SubElement(timecode, "source").text = "source"
    ET.SubElement(timecode, "displayformat").text = data["video"]["file"]["media"]["video"]["timecode"]["displayformat"]

    # Default sequence in and out points
    ET.SubElement(sequence, "in").text = "-1"
    ET.SubElement(sequence, "out").text = "-1"

    # Media element
    media = ET.SubElement(sequence, "media")
    
    # Video element under media
    video = ET.SubElement(media, "video")

    # Track element under video
    video_track = ET.SubElement(video, "track")
    for i, clip in enumerate(data["clips"], start=1):
        clip_id = f"Clip {i}"
        add_clipitem(video_track, clip, "video", clip_id, i == 1, data["video"]["file"], data["video"]["file"]["media"]["video"]["timecode"]["rate"], data["video"]["file"]["media"]["audio"]["channelcount"])

    # Audio elements and tracks
    audio_clip_id = 1
    audio = ET.SubElement(media, "audio")
    channel_count = data["video"]["file"]["media"]["audio"]["channelcount"]
    for channel in range(1, channel_count + 1):
        add_audio_track(audio, data["clips"], audio_clip_id, channel, data["video"]["file"], data["video"]["file"]["media"]["video"]["timecode"]["rate"], channel_count)
        audio_clip_id += len(data["clips"])

    return root

def add_rate(parent, rate_data):
    # Adding rate element with its sub-elements from JSON
    rate = ET.SubElement(parent, "rate")
    ET.SubElement(rate, "ntsc").text = rate_data.get("ntsc", "FALSE")
    ET.SubElement(rate, "timebase").text = str(rate_data.get("timebase", 30))

def add_clipitem(parent, clip, media_type, clip_id, add_file, file_data, rate_data, channel_count):
    # Adding clipitem element with various properties from JSON
    clip_item = ET.SubElement(parent, "clipitem", id=clip_id)
    ET.SubElement(clip_item, "name").text = file_data["name"]
    ET.SubElement(clip_item, "enabled").text = "TRUE"
    ET.SubElement(clip_item, "duration").text = str(clip["end"] - clip["start"])
    add_rate(clip_item, rate_data)
    ET.SubElement(clip_item, "in").text = str(clip["start"])
    ET.SubElement(clip_item, "out").text = str(clip["end"])
    ET.SubElement(clip_item, "start").text = str(clip["start"])
    ET.SubElement(clip_item, "end").text = str(clip["end"])
    ET.SubElement(clip_item, "anamorphic").text = "FALSE"
    ET.SubElement(clip_item, "pixelaspectratio").text = "Square"
    ET.SubElement(clip_item, "alphatype").text = "none"

    if add_file:
        # Add file element only for the first clipitem
        add_file_element(clip_item, file_data, rate_data)
    else:
        # Reference to the file element for other clipitems
        ET.SubElement(clip_item, "file", id="file-1")

    # Adding sourcetrack element with mediatype from JSON or defaults
    sourcetrack = ET.SubElement(clip_item, "sourcetrack")
    ET.SubElement(sourcetrack, "mediatype").text = media_type
    if media_type == "audio":
        track_index = 1 if clip_id.startswith("ClipA1") else 2
        ET.SubElement(sourcetrack, "trackindex").text = str(track_index)

    # Adding link elements for clipitem
    add_link_elements(clip_item, clip_id, media_type, channel_count)

def add_file_element(parent, file_data, rate_data):
    # Adding file element with properties from JSON
    file_element = ET.SubElement(parent, "file", id="file-1")
    ET.SubElement(file_element, "name").text = file_data["name"]
    ET.SubElement(file_element, "pathurl").text = file_data["pathurl"]
    add_rate(file_element, rate_data)
    ET.SubElement(file_element, "duration").text = str(file_data["media"]["video"]["duration"])

    # Adding timecode element with properties from JSON
    file_timecode = ET.SubElement(file_element, "timecode")
    add_rate(file_timecode, rate_data)
    ET.SubElement(file_timecode, "string").text = file_data["media"]["video"]["timecode"]["first_timecode"]
    ET.SubElement(file_timecode, "frame").text = "0"
    ET.SubElement(file_timecode, "source").text = "source"
    ET.SubElement(file_timecode, "displayformat").text = file_data["media"]["video"]["timecode"]["displayformat"]

    # Adding media element with video and audio properties from JSON
    file_media = ET.SubElement(file_element, "media")
    video = ET.SubElement(file_media, "video")
    add_video_format(video, file_data["media"]["video"]["samplecharacteristics"], rate_data)
    if "audio" in file_data["media"]:
        audio = ET.SubElement(file_media, "audio")
        add_audio_format(audio, file_data["media"]["audio"]["samplecharacteristics"], file_data["media"]["audio"]["channelcount"])

def add_video_format(video, samplecharacteristics, rate_data):
    # Adding video format and sample characteristics from JSON
    sample_characteristics = ET.SubElement(video, "samplecharacteristics")
    add_rate(sample_characteristics, rate_data)
    ET.SubElement(sample_characteristics, "width").text = str(samplecharacteristics["width"])
    ET.SubElement(sample_characteristics, "height").text = str(samplecharacteristics["height"])
    ET.SubElement(sample_characteristics, "anamorphic").text = samplecharacteristics["anamorphic"]
    ET.SubElement(sample_characteristics, "pixelaspectratio").text = samplecharacteristics["pixelaspectratio"]

def add_audio_format(audio, samplecharacteristics, channel_count):
    # Adding audio format and sample characteristics from JSON
    sample_characteristics = ET.SubElement(audio, "samplecharacteristics")
    ET.SubElement(sample_characteristics, "depth").text = str(samplecharacteristics["depth"])
    ET.SubElement(sample_characteristics, "samplerate").text = str(samplecharacteristics["samplerate"])
    ET.SubElement(audio, "channelcount").text = str(channel_count)

def add_audio_track(parent, clips, start_id, track_index, file_data, rate_data, channel_count):
    # Adding audio track with clipitems from JSON
    audio_track = ET.SubElement(parent, "track")
    for i, clip in enumerate(clips, start=1):
        clip_id = f"ClipA{track_index} {start_id + i - 1}"
        add_clipitem(audio_track, clip, "audio", clip_id, False, file_data, rate_data, channel_count)
    ET.SubElement(audio_track, "enabled").text = "TRUE"
    ET.SubElement(audio_track, "locked").text = "FALSE"
    ET.SubElement(audio_track, "outputchannelindex").text = str(track_index)

def add_link_elements(clip_item, clip_id, media_type, channel_count):
    # Adding link elements to clipitem to ensure proper video and audio synchronization
    clip_index = clip_id.split()[-1]
    video_link = (f"Clip {clip_index}", "video", 1, clip_index)
    audio_links = [(f"ClipA{channel} {clip_index}", "audio", channel, clip_index) for channel in range(1, channel_count + 1)]

    # Ensure the first link is always video, followed by audio channels
    links = [video_link] + audio_links

    for linkclipref, linkmediatype, trackindex, clipindex in links:
        link = ET.SubElement(clip_item, "link")
        ET.SubElement(link, "linkclipref").text = linkclipref
        ET.SubElement(link, "mediatype").text = linkmediatype
        ET.SubElement(link, "trackindex").text = str(trackindex)
        ET.SubElement(link, "clipindex").text = clipindex
        if linkmediatype == "audio":
            ET.SubElement(link, "groupindex").text = "1"

def main(video_file, output_dir, user_commands):
    if not check_ffmpeg_ffprobe():
        print("Error: ffmpeg and/or ffprobe are not installed or not found in PATH.")
        exit(1)

    if not os.path.exists(video_file):
        print(f"Error: Video file '{video_file}' does not exist.")
        exit(1)

    os.makedirs(output_dir, exist_ok=True)

    run_pyscenedetect(video_file, output_dir, user_commands)

    json_file = convert_csv_to_json(video_file, output_dir)
    xml_file = os.path.splitext(json_file)[0] + ".xml"
    convert_json_to_xml(json_file, xml_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect scenes in a video, convert to JSON, and output as XML.")
    parser.add_argument("--video_file", required=True, help="Path to the video file")
    parser.add_argument("--output_dir", required=True, help="Directory to store the output files")
    parser.add_argument('user_commands', nargs=argparse.REMAINDER, help="Additional PySceneDetect commands")
    args = parser.parse_args()

    main(args.video_file, args.output_dir, args.user_commands)
