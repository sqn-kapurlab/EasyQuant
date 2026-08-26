'''
Authors: Rita Carlota, Sofia Pascoal, Carolien Zeelen, Casper van der Kerk, Romy Meier 
Main goal: Split a hyperstack with up to four channels into 
    four substacks with one channel each. 
Optional: Further process each channel separately and save 
output substacks.
Requirements: *No plugin needed*
Date: October 2024
'''

import sys
import os
import datetime

from ij import IJ, WindowManager, Prefs

from javax.swing import JFileChooser, JFrame
from java.util import Date
from java.text import SimpleDateFormat
from java.io import File

##############
# CONSTANTS #
#############
PREF_KEY = "EasyQuant.lastDir"

##########################
#  VARIABLE DEFINITIONS  #
##########################
bioformats_extensions = [".czi", ".nd2", ".lif", ".tif"]
timestamp_formatter = SimpleDateFormat("yyyy-MM-dd'T'HH-mm-ss")
timestamp_string = timestamp_formatter.format(Date())

output_subdirectory_name = "EasyQuant_BatchProcessingOnly"

##########################
#  FUNCTION DEFINITIONS  #
##########################
def path_chooser_dialog(dialog_title, directory=False):
    frame = JFrame()
    frame.setAlwaysOnTop(True)

    file_chooser = JFileChooser()

    last_dir = Prefs.get(PREF_KEY, None)
    if last_dir and os.path.isdir(last_dir):
        file_chooser.setCurrentDirectory(File(last_dir))
    else:
        file_chooser.setCurrentDirectory(File(os.getcwd()))

    file_chooser.setDialogTitle(dialog_title)

    if directory:
        file_chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)
    
    response = file_chooser.showOpenDialog(frame)

    if response == JFileChooser.APPROVE_OPTION:
        selected_file = file_chooser.getSelectedFile()
        selected_path = selected_file.getAbsolutePath()
        
        if selected_file.isDirectory():
            Prefs.set(PREF_KEY, selected_path)
        else:
            Prefs.set(PREF_KEY, selected_file.getParent())
        
        frame.dispose()
        return selected_path
    else:
        frame.dispose()
        sys.exit("Directory selection was cancelled.")


def Rename_Channels(selected_channels):
    selected_channels_array = selected_channels.split(",")
    print("Selected channels: {}".format(selected_channels))

    for i in range(len(selected_channels_array)):
        channel_num = selected_channels_array[i]
        print("Renaming channel: {}".format(channel_num))

        imp = WindowManager.getImage("C" + str((i + 1)) + "-selection")
        print("--> Original name was C" + str((i + 1)) + "-selection")

        imp.setTitle("C" + channel_num)
        print("Renamed C" + channel_num)


def Split_Channels_Hyperstack(selected_channels, selected_frames):
    imp = WindowManager.getCurrentImage()
    imp.setTitle("hyperstack")

    IJ.run("Make Substack...", "channels=" + selected_channels + " frames=" + selected_frames)

    substack = WindowManager.getCurrentImage()
    substack.setTitle("selection")

    # If there is only one channel, do not run Split Channels.
    # Split Channels requires a multichannel image.
    if substack.getNChannels() == 1:
        substack.setTitle("C" + selected_channels.replace(",", "") + "-selection")
        return

    IJ.run(substack, "Split Channels", "")

    Rename_Channels(selected_channels)


def Rename_SaveTiff_Substacks(original_file_name, output_directory):
    current_date = datetime.date.today()
    current_date_string = "{}_{}_{}".format(str(current_date.year), str(current_date.month), str(current_date.day))
    print("File date: {}".format(current_date_string))

    image_title_list = WindowManager.getImageTitles()

    base_name = os.path.splitext(original_file_name)[0]
    base_name = base_name.split("/")[-1]
    print("Base name: {}".format(base_name))

    for image in image_title_list:
        imp = WindowManager.getImage(image)

        if image.startswith("C1"):
            image_file_name = "{}_{}_C1".format(current_date_string, base_name)
        elif image.startswith("C2"):
            image_file_name = "{}_{}_C2".format(current_date_string, base_name)
        elif image.startswith("C3"):
            image_file_name = "{}_{}_C3".format(current_date_string, base_name)
        elif image.startswith("C4"):
            image_file_name = "{}_{}_C4".format(current_date_string, base_name)
        else:
            continue

        IJ.saveAsTiff(imp, os.path.join(output_directory, image_file_name))


#########################
#  ASK USER FOR INPUTS  #
#########################
#@ String (choices={"Process single file", "Process current open image", "Process entire directory"}, value="Process entire directory", style="listBox", persist=false) choice_input
#@ String (label="Enter frame numbers or ranges", description="For example:1,2,5-10,12", value="1,10,20,30,40,50,60,70,80") choice_frames
#@ String (label="Select desired channels:", visibility='MESSAGE', value="") message
#@ Boolean (label="Channel 1", value=true) channel_1
#@ Boolean (label="Channel 2", value=false) channel_2
#@ Boolean (label="Channel 3", value=false) channel_3
#@ Boolean (label="Channel 4", value=false) channel_4

choice_frames = choice_frames.replace(" ", "")

channel_string = ""
if channel_1:
    channel_string += "1"
if channel_2:
    channel_string += ",2"
if channel_3:
    channel_string += ",3"
if channel_4:
    channel_string += ",4"

print("* Checkpoints Hyperstack Processing *")
print("Chosen frames: {}".format(choice_frames))
print("Chosen channels: {}".format(channel_string))
print("Chosen input: {}".format(choice_input))


######################################
#  SELECT FILE OR FOLDER TO ANALYSE  #
######################################
if choice_input == "Process single file":
    selected_file_path = path_chooser_dialog(dialog_title="Select Input File", directory=False)

    if selected_file_path is None:
        sys.exit("File selection was cancelled.")
    
    print("Opening file at: {}".format(selected_file_path))

    if any(extension in selected_file_path for extension in bioformats_extensions):
        print("i have ext")
        IJ.run("Bio-Formats Importer", "open=[" + selected_file_path + "] autoscale color_mode=Default view=Hyperstack stack_order=XYCZT virtualstack_order=XYCZT windowless use_virtual_stack")
    else:
        IJ.openImage(selected_file_path).show()
        print("im open")
    
    files = True
       

elif choice_input == "Process current open image":
    files = True

elif choice_input == "Process entire directory":
    selected_directory_path = path_chooser_dialog(dialog_title="Select Input Directory", directory=True)

    if selected_directory_path is None:
        sys.exit("Directory selection was cancelled.")

    print("Selected directory path: {}".format(selected_directory_path))
    files = False

print(files)

##############################################
# SELECT OUTPUT FOLDER AND CREATE SUBFOLDERS #
##############################################
output_directory = path_chooser_dialog(dialog_title="Select Output Directory", directory=True)
output_directory_root = os.path.join(output_directory, output_subdirectory_name + "_" + timestamp_string)
substack_output_directory = os.path.join(output_directory_root, "Substacks")
os.makedirs(substack_output_directory)

text_file_path = os.path.join(output_directory_root, 'input_parameters.txt')
with open(text_file_path, 'w') as f:
    f.write(timestamp_string + '\n\n')
    f.write("Macro used: Batch Processing\n")
    f.write("Processing mode: {}\n".format(choice_input))
    f.write("Selected channels: {}\n".format(channel_string))
    f.write("Selected frames: {}\n".format(choice_frames))


######################
#  PROCESSS IMAGES   #
######################
print(files)

if files:
    imp = WindowManager.getCurrentImage()
    image_title = imp.getTitle()

    Split_Channels_Hyperstack(channel_string, choice_frames)

    Rename_SaveTiff_Substacks(image_title, substack_output_directory)

    IJ.run("Close All")

elif not files:
    dir_list = [f for f in os.listdir(selected_directory_path) if not f.startswith('.')]
    print("Amount of files in chosen directory: {}".format(len(dir_list)))

    for image in dir_list:
        print("\nNow processing image: {}".format(image))
        image_path = selected_directory_path + "/" + image

        if any(extension in image for extension in bioformats_extensions):
            IJ.run("Bio-Formats Importer", "open=[" + image_path + "] autoscale color_mode=Default view=Hyperstack stack_order=XYCZT virtualstack_order=XYCZT windowless use_virtual_stack")
        else:
            imp = IJ.openImage(image_path)
            imp.show()
        
        imp = WindowManager.getCurrentImage()
        image_title = imp.getTitle()
        
        Split_Channels_Hyperstack(channel_string, choice_frames)

        Rename_SaveTiff_Substacks(image_title, substack_output_directory)

        IJ.run("Close All")

print("\n---------------------\nAll images processed!\n---------------------")