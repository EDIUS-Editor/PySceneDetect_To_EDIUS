import tkinter as tk
from tkinter import filedialog, messagebox
import json
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
import os

class JSONtoXMLConverter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JSON to FCP7 XML Converter for EDIUS")
        self.geometry("600x300")

        self.json_file_path = ""
        self.xml_file_path = ""

        self.create_widgets()

    def create_widgets(self):
        # Button to select JSON file
        self.select_json_button = tk.Button(self, text="Select JSON File", command=self.select_json_file)
        self.select_json_button.pack(pady=10)

        # Text box to display the selected JSON file path
        self.json_file_path_entry = tk.Entry(self, width=80)
        self.json_file_path_entry.pack(pady=10)

        # Button to select save location for XML file
        self.select_xml_button = tk.Button(self, text="Select Save Location", command=self.select_xml_file)
        self.select_xml_button.pack(pady=10)

        # Text box to display the save location for XML file
        self.xml_file_path_entry = tk.Entry(self, width=80)
        self.xml_file_path_entry.pack(pady=10)

        # Button to start conversion
        self.convert_button = tk.Button(self, text="Convert", command=self.convert)
        self.convert_button.pack(pady=10)

    def select_json_file(self):
        self.json_file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        self.json_file_path_entry.delete(0, tk.END)
        self.json_file_path_entry.insert(0, self.json_file_path)
        
        # Set default XML file path based on JSON file path
        if self.json_file_path:
            self.xml_file_path = os.path.splitext(self.json_file_path)[0] + ".xml"
            self.xml_file_path_entry.delete(0, tk.END)
            self.xml_file_path_entry.insert(0, self.xml_file_path)

    def select_xml_file(self):
        self.xml_file_path = filedialog.asksaveasfilename(defaultextension=".xml", filetypes=[("XML Files", "*.xml")])
        self.xml_file_path_entry.delete(0, tk.END)
        self.xml_file_path_entry.insert(0, self.xml_file_path)

    def convert(self):
        # Check if both JSON file path and XML file path text boxes are empty
        if not self.json_file_path_entry.get() or not self.xml_file_path_entry.get():
            messagebox.showerror("Error", "Please select both JSON file and save location for XML file.")
            return

        try:
            with open(self.json_file_path, 'r') as json_file:
                data = json.load(json_file)
                root = self.create_xml_structure(data)
                tree_str = ET.tostring(root, encoding='utf-8')
                pretty_xml_as_string = parseString(tree_str).toprettyxml(indent="  ")
                # Add XML declaration and doctype
                xml_content = '<?xml version="1.0" ?>\n<!DOCTYPE xmeml>\n' + pretty_xml_as_string.split('?>', 1)[1].strip()
                with open(self.xml_file_path, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                messagebox.showinfo("Success", "Conversion completed successfully!")
                self.quit()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def create_xml_structure(self, data):
        # Root element
        root = ET.Element("xmeml", version="5")
        
        # Sequence element
        sequence = ET.SubElement(root, "sequence", id="sequence-1")
        
        # Sequence name from JSON
        ET.SubElement(sequence, "name").text = data["sequence"]["name"]
        
        # Duration from JSON
        ET.SubElement(sequence, "duration").text = str(data["video"]["file"]["media"]["video"]["duration"])
        
        # Add rate element
        self.add_rate(sequence, data["video"]["file"]["media"]["video"]["timecode"]["rate"])

        # Timecode element
        timecode = ET.SubElement(sequence, "timecode")
        self.add_rate(timecode, data["video"]["file"]["media"]["video"]["timecode"]["rate"])
        
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
            self.add_clipitem(video_track, clip, "video", clip_id, i == 1, data["video"]["file"], data["video"]["file"]["media"]["video"]["timecode"]["rate"], data["video"]["file"]["media"]["audio"]["channelcount"])

        # Audio elements and tracks
        audio_clip_id = 1
        audio = ET.SubElement(media, "audio")
        channel_count = data["video"]["file"]["media"]["audio"]["channelcount"]
        for channel in range(1, channel_count + 1):
            self.add_audio_track(audio, data["clips"], audio_clip_id, channel, data["video"]["file"], data["video"]["file"]["media"]["video"]["timecode"]["rate"], channel_count)
            audio_clip_id += len(data["clips"])

        return root

    def add_rate(self, parent, rate_data):
        # Adding rate element with its sub-elements from JSON
        rate = ET.SubElement(parent, "rate")
        ET.SubElement(rate, "ntsc").text = rate_data.get("ntsc", "FALSE")
        ET.SubElement(rate, "timebase").text = str(rate_data.get("timebase", 30))

    def add_clipitem(self, parent, clip, media_type, clip_id, add_file, file_data, rate_data, channel_count):
        # Adding clipitem element with various properties from JSON
        clip_item = ET.SubElement(parent, "clipitem", id=clip_id)
        ET.SubElement(clip_item, "name").text = file_data["name"]
        ET.SubElement(clip_item, "enabled").text = "TRUE"
        ET.SubElement(clip_item, "duration").text = str(clip["end"] - clip["start"])
        self.add_rate(clip_item, rate_data)
        ET.SubElement(clip_item, "in").text = str(clip["start"])
        ET.SubElement(clip_item, "out").text = str(clip["end"])
        ET.SubElement(clip_item, "start").text = str(clip["start"])
        ET.SubElement(clip_item, "end").text = str(clip["end"])
        ET.SubElement(clip_item, "anamorphic").text = "FALSE"
        ET.SubElement(clip_item, "pixelaspectratio").text = "Square"
        ET.SubElement(clip_item, "alphatype").text = "none"

        if add_file:
            # Add file element only for the first clipitem
            self.add_file_element(clip_item, file_data, rate_data)
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
        self.add_link_elements(clip_item, clip_id, media_type, channel_count)

    def add_file_element(self, parent, file_data, rate_data):
        # Adding file element with properties from JSON
        file_element = ET.SubElement(parent, "file", id="file-1")
        ET.SubElement(file_element, "name").text = file_data["name"]
        ET.SubElement(file_element, "pathurl").text = file_data["pathurl"]
        self.add_rate(file_element, rate_data)
        ET.SubElement(file_element, "duration").text = str(file_data["media"]["video"]["duration"])

        # Adding timecode element with properties from JSON
        file_timecode = ET.SubElement(file_element, "timecode")
        self.add_rate(file_timecode, rate_data)
        ET.SubElement(file_timecode, "string").text = file_data["media"]["video"]["timecode"]["first_timecode"]
        ET.SubElement(file_timecode, "frame").text = "0"
        ET.SubElement(file_timecode, "source").text = "source"
        ET.SubElement(file_timecode, "displayformat").text = file_data["media"]["video"]["timecode"]["displayformat"]

        # Adding media element with video and audio properties from JSON
        file_media = ET.SubElement(file_element, "media")
        video = ET.SubElement(file_media, "video")
        self.add_video_format(video, file_data["media"]["video"]["samplecharacteristics"], rate_data)
        if "audio" in file_data["media"]:
            audio = ET.SubElement(file_media, "audio")
            self.add_audio_format(audio, file_data["media"]["audio"]["samplecharacteristics"], file_data["media"]["audio"]["channelcount"])

    def add_video_format(self, video, samplecharacteristics, rate_data):
        # Adding video format and sample characteristics from JSON
        sample_characteristics = ET.SubElement(video, "samplecharacteristics")
        self.add_rate(sample_characteristics, rate_data)
        ET.SubElement(sample_characteristics, "width").text = str(samplecharacteristics["width"])
        ET.SubElement(sample_characteristics, "height").text = str(samplecharacteristics["height"])
        ET.SubElement(sample_characteristics, "anamorphic").text = samplecharacteristics["anamorphic"]
        ET.SubElement(sample_characteristics, "pixelaspectratio").text = samplecharacteristics["pixelaspectratio"]

    def add_audio_format(self, audio, samplecharacteristics, channel_count):
        # Adding audio format and sample characteristics from JSON
        sample_characteristics = ET.SubElement(audio, "samplecharacteristics")
        ET.SubElement(sample_characteristics, "depth").text = str(samplecharacteristics["depth"])
        ET.SubElement(sample_characteristics, "samplerate").text = str(samplecharacteristics["samplerate"])
        ET.SubElement(audio, "channelcount").text = str(channel_count)

    def add_audio_track(self, parent, clips, start_id, track_index, file_data, rate_data, channel_count):
        # Adding audio track with clipitems from JSON
        audio_track = ET.SubElement(parent, "track")
        for i, clip in enumerate(clips, start=1):
            clip_id = f"ClipA{track_index} {start_id + i - 1}"
            self.add_clipitem(audio_track, clip, "audio", clip_id, False, file_data, rate_data, channel_count)
        ET.SubElement(audio_track, "enabled").text = "TRUE"
        ET.SubElement(audio_track, "locked").text = "FALSE"
        ET.SubElement(audio_track, "outputchannelindex").text = str(track_index)

    def add_link_elements(self, clip_item, clip_id, media_type, channel_count):
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

if __name__ == "__main__":
    app = JSONtoXMLConverter()
    app.mainloop()
