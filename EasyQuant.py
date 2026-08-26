'''
Authors: Rita Carlota, Sofia Pascoal, Carolien Zeelen, Casper van der Kerk, Romy Meier 
Main goal:
    - Split a hyperstack with up to four channels into four substacks with one channel each. 
    - Run classifiers based on channel in one image or multiple images inside a folder.
Optional: Further process each channel separately and save 
output substacks.
Requirements: *No plugin needed*
Date: September 2025
'''

import sys
import os
import datetime
import csv

from ij import IJ, WindowManager, Prefs
from ij.measure import ResultsTable
from ij.text import TextWindow

from javax.swing import JFileChooser, JFrame, JOptionPane, JDialog
from java.text import SimpleDateFormat
from java.util import Date
from java.lang import System, Runtime
from java.io import File
from java.awt.event import WindowAdapter

##############
# CONSTANTS #
#############
# Initialize a key name used to store the last opened directory between ImageJ sessions
PREF_KEY = "EasyQuant.lastDir"

##########################
#  VARIABLE DEFINITIONS  #
##########################
timestamp_formatter = SimpleDateFormat("yyyy-MM-dd'T'HH-mm-ss")
date_formatter =  SimpleDateFormat("yyyy_MM_dd")

# Extensions associated with the Bio-Formats plug-in 
bioformats_extensions = [".czi", ".nd2", ".lif"]

# This will be the base of the output directory structure. 
# It will be appended with a timestamp with format: `_DD-MM-YYYYTHH-MM-SS`
output_subdirectory_name = "EasyQuant"

##########################
#  FUNCTION DEFINITIONS  #
##########################
class DialogDisposer(WindowAdapter):
    """
    A simple class to handle the window closing event and dispose of a dialog. It is used to dispose the dialog created by the `show_info_popup()` function.
    This works reliably across all Jython versions.
    """
    def __init__(self, dialog):
        self.dialog = dialog
    
    def windowClosing(self, event):
        self.dialog.dispose()


def path_chooser_dialog(dialog_title, directory = False):
    """
    Function to generate a dialog window to select a file or directory.

    Args:
        dialog_title (string): Title that will be given to the dialog box
        directory (bool, optional): Whether a file path should be chosen (False) or only a directory (True)
    
    Returns:
        Optional[string]: Either a file path or a directory path
    """
    # Create an 'always-on-top' frame to prevent the dialog from being hidden behind ImageJ
    frame = JFrame()
    frame.setAlwaysOnTop(True)

    # Create Java File Chooser object
    file_chooser = JFileChooser()

    # Fetch last used directory from preferences
    last_dir = Prefs.get(PREF_KEY, None)
    # If returned value is a valid directory
    if last_dir and os.path.isdir(last_dir):
        # Open dialog on that directory
        file_chooser.setCurrentDirectory(File(last_dir))
    else:
        # If returned value is not a valid directory, open dialog on the current working directory
        file_chooser.setCurrentDirectory(File(os.getcwd()))

    file_chooser.setDialogTitle(dialog_title)

    if directory:
        # Set the file chooser to directory only mode
        file_chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)
    
    response = file_chooser.showOpenDialog(frame)

    if response == JFileChooser.APPROVE_OPTION:
        # Get path
        selected_file = file_chooser.getSelectedFile()
        selected_path = file_chooser.getSelectedFile().getAbsolutePath()
        
        # Save diretory back to preferences
        if selected_file.isDirectory():
            # If the selected path already is a directory, save that path
            Prefs.set(PREF_KEY, selected_path)
        else:
            # If the selected path is a file, save the directory path of that file
            Prefs.set(PREF_KEY, selected_file.getParent())
        
        frame.dispose() # Dispose of the created dialog to free up system memory
        return selected_path
    else:
        frame.dispose() # Dispose of the created dialog to free up system memory
        # Stop the script if no path was returned (i.e. the dialog was cancelled)
        sys.exit("Directory selection was cancelled.")


def close_all(close_images = True, close_other = True):
    """
    Function to close all open windows without closing ImageJ itself

    Args:
        close_images (bool, optional): If set to True closes all image windows
        close_other (bool, optional): If set to True closes all non-image windows (Does not close the macro window or ImageJ itself)
    
    Returns:
        None
    """
    # Close all images
    if close_images:
        while WindowManager.getImageCount() > 0:
            imp = WindowManager.getCurrentImage()
            if imp is not None:
                imp.close()

    # Close all non-image windows (Results, Summary, custom tables, etc.)
    if close_other:
        non_images = WindowManager.getNonImageWindows()
        if non_images is not None:
            for win in list(non_images):  # copy to avoid modification during iteration
                if win is not None:
                    win.close()


def show_info_popup(message, title ="Info"):
    """
    Shows a non-blocking info popup that stays on top of other windows.

    Args:
        message (string): The message to be displayed in the pop-up
        title (string, optional): The title of the pop-up box

    Returns:
        None
    """
    pane = JOptionPane(message, JOptionPane.INFORMATION_MESSAGE)
    dialog = pane.createDialog(None, title)
    
    dialog.setAlwaysOnTop(True)
    dialog.setModal(False)
    
    # Create and add an instance of our custom class
    closer = DialogDisposer(dialog)
    dialog.addWindowListener(closer)
    
    dialog.setVisible(True)


def Rename_Channels(selected_channels):
    """
    Function to rename the channels dynamically based on the user's selected channels

    Args:
        selected_channels (string): A comma-separated string containing which channels should be processed [E.g. "1,2,3"]

    Returns:
        None
    """
    # Get the list of selected channels as an array
    selected_channels_array = selected_channels.split(",") #e.g., ["2", "3"]
    print("Selected channels: {}".format(selected_channels))

    # Make sure we rename based on selected channels, even if they are not in order
    for i in range(len(selected_channels_array)):
        channel_num = selected_channels_array[i]
        print("Renaming channel: {}".format(channel_num))

        # Select the window for the split channel based on its original order
        imp = WindowManager.getImage("C" + str((i + 1)) + "-selection")
        print("--> Original name was C" + str((i + 1)) + "-selection")

        # Rename the image to reflect the actual channel number selected by the user
        imp.setTitle("C" + channel_num)
        print("Renamed C" + channel_num)


def Split_Channels_Hyperstack(selected_channels, selected_frames):
    """
    Function to generate Substacks from a Hyperstack, based on selected channels and frames

    Args:
        selected_channels (string): A comma-separated string containing which channels should be processed [E.g. "1,2,3"]
        selected_frames (string): A comma-separated string containing frame ranges to process [E.g. "1,2,5-10,12"]

    Returns:
        None
    """
    # Rename current hyperstack for easier reference
    imp = WindowManager.getCurrentImage()
    imp.setTitle("hyperstack")

    # Specify the user-provided channels and use the user-provided frames
    # imp.getWindow()
    IJ.run("Make Substack...", "channels=" + selected_channels + " frames=" + selected_frames)
    substack = WindowManager.getCurrentImage()
    substack.setTitle("selection")

    # Split channels into individual images: C1-selection, C2-selection, C3-selection, C4-selection
    IJ.run(substack, "Split Channels", "")
    #Dynamically rename the channel images based on the user's selected channels
    Rename_Channels(selected_channels);


def Rename_SaveTiff_Substacks(original_file_name, output_directory):
    """
    A function to rename open Substack images and save them, as Tiff images, according to their channel

    Args:
        original_file_name (string): Name of the original file in the input directory. Used to generate the base file name of the output Tiff file
        output_directory (string): Directory on the machine running the macro where the Substack Tiff will be stored

    Returns:
        None
    """
    current_date = datetime.date.today()
    current_date_string = "{}_{}_{}".format(str(current_date.year), str(current_date.month),str(current_date.day))
    print("File date: {}".format(current_date_string))

    # Get the list of image titles
    image_title_list = WindowManager.getImageTitles()

    # Remove extension from file name
    base_name = os.path.splitext(original_file_name)[0] # Take the first entry from the resulting array
    base_name = base_name.split("/")[-1] # Take the last entry from the resulting array
    # Debuggin output
    print("Base name: {}".format(base_name))

    # Loop through the list of images and rename/save them based on the channels
    for image in image_title_list:
        imp = WindowManager.getImage(image)
        if image.startswith("C1"):
            # imp.setTitle("{}_{}_C1".format(current_date_string, base_name))
            image_file_name = "{}_{}_C1".format(current_date_string, base_name)
        elif image.startswith("C2"):
            # imp.setTitle("{}_{}_C2".format(current_date_string, base_name))
            image_file_name = "{}_{}_C2".format(current_date_string, base_name)
        elif image.startswith("C3"):
            # imp.setTitle("{}_{}_C3".format(current_date_string, base_name))
            image_file_name = "{}_{}_C3".format(current_date_string, base_name)
        elif image.startswith("C4"):
            # imp.setTitle("{}_{}_C4".format(current_date_string, base_name))
            image_file_name = "{}_{}_C4".format(current_date_string, base_name)
        else:
            continue #If image title does not match with any of the above, move to the next image
        IJ.saveAsTiff(imp, os.path.join(output_directory, image_file_name))


def run_classifier(imp, image_name, classifier_path, output_folder, size_parameters):
    """
    Function to segment an image with a Labkit classifier.
    This function performs the following steps:
        1. Segment the Image using a Labkit classifier WITHOUT the use of a GPU
        2. Set the image type to 8-bit
        3. Converts to mask using the `Otsu` method, with a dark background
            - `Calculate threshold for each image` and `Black background (of binary masks)` settings are turned on
        4. Holes are filled for the entire stack
        5. Particle analysis with the `size_parameters` input variable as the size setting on the whole stack.
            - `Summarize`, `Exclude on edges`, `Overlay` and `Pixel units` settings are turned on.

    Args:
        imp (ImagePlus): The ImagePlus object of the image to be processed. Created with `IJ.openImage()`
        image_name (string): The name of the image to be processed. Used to select the correct window by title
        classifier_path (string): Absolute file path to the classifier used in processing
        output_folder (string): Absolute path to the directory where the image masks are stored
        size_parameters (string): String with the sizing parameters used for the segmentation. E.g. `0-Infinity` or `1-10`

    Returns:
        None
    """
    # Checkpoints to know what is being used by the function
    print("Classifier in use: {}".format(classifier_path))

    # Run segmentation with Labkit using the selected classifier and the active image (no explicit image selection)
    IJ.run(imp, "Segment Image With Labkit", "segmenter_file=[" + classifier_path + "] use_gpu=false")

    imp = WindowManager.getImage("segmentation of " + image_name)
    # Additional image processing steps
    Prefs.scaleConversions = True
    IJ.run(imp, "8-bit", "")

    Prefs.blackBackground = True
    IJ.run(imp, "Convert to Mask", "method=Otsu background=Dark calculate black")

    # Fill all holes within particles
    IJ.run(imp, "Fill Holes", "stack")

    # Analyze Particles with size exclusion based on minParticleSize
    print("Analyzing particles at the following size range: {}".format(size_parameters))
    IJ.run(imp, "Analyze Particles...", "size=" + size_parameters + " pixel show=[Overlay Masks] exclude summarize overlay stack")

    # Save Image with mask as Tiff to check classifier performance afterwars, and close images at the end
    
    IJ.saveAsTiff(imp, os.path.join(output_folder, "Mask_" + image_name))
    print("Confirm masks at: {}".format(os.path.join(output_folder, "Mask_" + image_name)))


def results_to_csv(csv_file_path, image_name, write_headers, channel):
    """
    Function to write the values of the `Summary` window to a CSV file. The `Summary` window is automatically created at the end of a segmentation with Labkit.
    At the time of writing the columns that are written by this function are: `Image Name, Channel, Slice,Count, Total Area, Average Size, %Area,Mean`. 
    However, this is subject to change if the output of Labkit ever changes.
    NOTE: If a CSV with the name `<yyyy_MM_dd>.csv already exists on the output directory path, this function will append to that file. It will not automatically create a new file

    Args:
        csv_file_path (string): Path where the CSV will be written
        image_name (string): Name of the image whose output is being written
        write_headers (bool): Whether to write the headers (column names) when appending to the CSV file. When set to False will not write the headers.
        channel (string): The channel number that has been processed

    Returns:
        None
    """
    # Initialize csv_file
    csv_file = None
    current_date = date_formatter.format(Date())

    # This approach is very fragile. If the name of the "Summary" text box ever changes this will break.
    # A potential improvement would be to compute summary results from the results table
    win = WindowManager.getWindow("Summary of segmentation of {}".format(image_name))
    if isinstance(win, TextWindow):
        text_panel = win.getTextPanel()

        # Get the headers of the Summary
        header_line = text_panel.getColumnHeadings()

        # Get each row of the Summary
        lines = [text_panel.getLine(i) for i in range(text_panel.getLineCount())]
    
    else:
        # If for whatever reason the Summary window is not found, print a warning and write a placeholder line in the CSV
        print("No 'Summary' window found for image: {}".format(image_name))
        header_line = ""
        lines = ["No result output found for: {}".format(image_name)]

    try: 
        # Open a file at the selected output path in 'append' mode
        csv_file = open(csv_file_path, 'ab')
        # Initialize the writer
        writer = csv.writer(csv_file)
        # Write the headers to the CSV file if enabled
        if write_headers:
            writer.writerow(["Image Name", "Channel"] + header_line.split("\t"))
        # Write the data
        for line in lines:
            writer.writerow([image_name, channel] + line.split("\t"))
        # Write an empty row at the end of the results to separate entries
        writer.writerow("")
    
    except Exception as e:
        print("An error occurred while appending to the CSV file:", e)

    finally:
        # Always try to close the file at the end
        # If the file is not explicitly closed it will remain "in use" by ImageJ
        if csv_file is not None:
            csv_file.close()

#########################
#  ASK USER FOR INPUTS  #
#########################
#@ String (choices={"Process single file", "Process current open image", "Process entire directory"}, value="Process entire directory", style="listBox", persist=false) choice_input
#@ String (label="Enter frame numbers or ranges", description="For example:1,2,5-10,12", value="1,10,20,30,40,50,60,70,80") choice_frames
#@ String (label="Select desired channels:", visibility='MESSAGE', value="") message
#@ Boolean (label="Channel 1", value=true) channel_1
#@ Boolean (label="Channel 2", value=true) channel_2
#@ Boolean (label="Channel 3", value=false) channel_3
#@ Boolean (label="Channel 4", value=false) channel_4

#@ Integer (label="Minimum particle size:", min=0, value=0) min_particle_size
#@ Integer (label="Maximum particle size (-1 is Infinity):", value=-1) max_particle_size

#@ String (label="Add Experimental ID", value="1") experimental_id

##########################
#  CLASSIFIER SELECTION  #
##########################
if channel_1:
    classifier_channel1_path = path_chooser_dialog(dialog_title="Select Classifier for Channel 1", directory = False)
if channel_2:
    classifier_channel2_path = path_chooser_dialog(dialog_title="Select Classifier for Channel 2", directory = False)
if channel_3:
    classifier_channel3_path = path_chooser_dialog(dialog_title="Select Classifier for Channel 3", directory = False)
if channel_4:
    classifier_channel4_path = path_chooser_dialog(dialog_title="Select Classifier for Channel 4", directory = False)

#########################
#  PROCESS USER INPUTS  #
#########################
# Delete extra spaces in frame selection
choice_frames = choice_frames.replace(" ", "")

# Construct the channel_string based on selected checkboxes
channel_string = ""
if (channel_1):
    channel_string += "1"
if (channel_2):
    channel_string += ",2"
if (channel_3):
    channel_string += ",3"
if (channel_4):
    channel_string += ",4"

# Replace spaces in string variables
experimental_id = experimental_id.replace(" ", "")

# Check if max is larger than min
if max_particle_size != -1 and min_particle_size > max_particle_size:
    IJ.error("Minimum particle size is larger than maximum particle size.\nPlease use a max value that is larger than the min value.")
    raise Exception("Maximum particle size must be larger than the minimum")

# Set max_particle_size to 'Infinity' if provided value is -1
if max_particle_size == -1:
    max_particle_size = "Infinity"

# Construct size parameters string from input
size_parameters = "{}-{}".format(str(min_particle_size), str(max_particle_size))

# Printing output to verify selections
print("* Checkpoints Hyperstack Processing *")
print("Chosen frames: {}".format(choice_frames))
print("Chosen channels: {}".format(channel_string))
print("Chosen input: {}".format(choice_input))

# Generating some timestamps for file names and calculating runtime
start_timestamp = Date()
start_timestamp_string = timestamp_formatter.format(start_timestamp) 
current_date = date_formatter.format(Date()) 

#############################
#  START OF MACRO PHASE 1  #
#############################
######################################
#  SELECT FILE OR FOLDER TO ANALYSE  #
######################################
if choice_input == "Process single file":
    # Show dialog to select file
    selected_single_file_path = path_chooser_dialog(dialog_title = "Select Input File", directory = False)

    # If returned path is None
    if selected_single_file_path is None:
         # Stop the script
        sys.exit("File selection was cancelled.")
    
    # Open the file
    print("Opening file at: {}".format(selected_single_file_path))
    # Bioformats
    if any(extension in selected_single_file_path for extension in bioformats_extensions):
        IJ.run("Bio-Formats Importer", "open=[" + selected_single_file_path + "] autoscale color_mode=Default view=Hyperstack stack_order=XYCZT virtualstack_order=XYCZT windowless use_virtual_stack")
    else:
        IJ.openImage(selected_single_file_path).show()
    
    # Set the 'files' variable
    files = True
       

elif choice_input == "Process current open image":
    files = True

elif choice_input == "Process entire directory":
    selected_directory_path = path_chooser_dialog(dialog_title = "Select Input Directory", directory = True)

    if selected_directory_path is None:
         # Stop the script
        sys.exit("Directory selection was cancelled.")

    print("Selected directory path: {}".format(selected_directory_path))
    files = False

##############################################
# SELECT OUTPUT FOLDER AND CREATE SUBFOLDERS #
##############################################
# Get output directory
output_directory = path_chooser_dialog(dialog_title = "Select Output Directory", directory = True)
output_directory_root = os.path.join(output_directory, output_subdirectory_name + "_" + start_timestamp_string)
substack_output_directory = os.path.join(output_directory_root, "Substacks")
mask_output_directory = os.path.join(output_directory_root, "Masks")
os.makedirs(substack_output_directory)
os.makedirs(mask_output_directory)
# Generate path and filename for the results CSV file
csv_file_path = os.path.join(output_directory_root, "results_" + start_timestamp_string + ".csv")

# Write a text file documenting the input parameters
text_file_path = os.path.join(output_directory_root, 'input_parameters.txt')
with open(text_file_path, 'w') as f:
    f.write(start_timestamp_string + '\n\n')
    f.write("Macro used: Full macro (Batch Processing + Cell Counting)\n")
    f.write("Processing mode: {}\n".format(choice_input))
    for i in channel_string.split(','):
        if len(i) == 1: # When splitting a string that starts with `,` an empty value may appear in the resulting list, causing the script to fail. This if-statement checks for that.
            f.write("Channel {} classifier: {}\n".format(i, eval("classifier_channel" + i + "_path")))
    f.write("Selected frames: {}\n".format(choice_frames))
    f.write("Minimum selected particle size: {}\n".format(min_particle_size))
    f.write("Maximum selected particle size: {}\n".format(max_particle_size))
f.close()
    
#########################
#  PROCESSS HYPERSTACK  #
#########################
if files:
    # Get current image title
    imp = WindowManager.getCurrentImage()
    image_title = imp.getTitle()
    # Split channels
    Split_Channels_Hyperstack(channel_string, choice_frames)

    # Save substacks
    Rename_SaveTiff_Substacks(image_title, substack_output_directory)
    # Close active images
    close_all()

elif not files:
    dir_list = [f for f in os.listdir(selected_directory_path) if not f.startswith('.')] # This avoids hidden files / files that start with "." (like .DS_Store on MacOS)
    print("Amount of files in chosen directory: {}".format(len(dir_list)))

    for image in dir_list:
        print("\nNow processing image: {}".format(image))
        image_path = selected_directory_path + "/" + image
        # Bioformats
        if any(extension in image for extension in bioformats_extensions):
            IJ.run("Bio-Formats Importer", "open=[" + image_path + "] autoscale color_mode=Default view=Hyperstack stack_order=XYCZT virtualstack_order=XYCZT windowless use_virtual_stack")
        else:
            imp = IJ.openImage(image_path)
        
        imp = WindowManager.getCurrentImage()
        image_title = imp.getTitle()
        
        # Split channels
        Split_Channels_Hyperstack(channel_string, choice_frames)

        # Rename if needed
        Rename_SaveTiff_Substacks(image_title, substack_output_directory)

        # Close active images
        close_all()
        System.gc()
print("\n---------------------\nAll hyperstacks processed!\n---------------------")

############################
#  START OF MACRO PHASE 2  #
############################
# Get all files in the substack output directory
# These will all get processed by the classifier
dir_list = [f for f in os.listdir(substack_output_directory) if not f.startswith('.')] # This avoids hidden files / files that start with "." (like .DS_Store on MacOS)
print("Amount of files in substack output directory: {}".format(len(dir_list)))

# Setting the write_headers flag to True so that the first iteration of the for-loop writes the headers
# but iterations after the first do not
write_headers = True

# Initializing an index to keep track of which image we are working on for the progress bar
index = 1

# Looping over the substack output directory and processing all images with its related classifier
for image_name in dir_list:
    print("\nNow processing image: {} [{}/{}]".format(image_name, index, len(dir_list)))
    image_path = os.path.join(substack_output_directory, image_name)

    imp = IJ.openImage(image_path).show()

    # Select classifier to run based on image title (C1, C2, C3, or C4)
    if image_name.endswith("_C1.tif") and channel_1:
        run_classifier(imp, image_name, classifier_channel1_path, mask_output_directory, size_parameters)
        results_to_csv(csv_file_path, image_name, write_headers, channel="1")
    elif image_name.endswith("_C2.tif") and channel_2:
        run_classifier(imp, image_name, classifier_channel2_path, mask_output_directory, size_parameters)
        results_to_csv(csv_file_path, image_name, write_headers, channel="2")
    elif image_name.endswith("_C3.tif") and channel_3:
        run_classifier(imp, image_name, classifier_channel3_path, mask_output_directory, size_parameters)
        results_to_csv(csv_file_path, image_name, write_headers, channel="3")
    elif image_name.endswith("_C4.tif") and channel_4:
        run_classifier(imp, image_name, classifier_channel4_path, mask_output_directory, size_parameters)
        results_to_csv(csv_file_path, image_name, write_headers, channel="4")
    else:
        IJ.showMessage("Nothing processed: Channel selected in the beggining does not match chosen image")

    # If you only want the column headers to appear once in your CSV file, uncomment the bottom two lines
    # if write_headers == True:
    #     write_headers = False
    close_all()
    System.gc() 
    Runtime.getRuntime().freeMemory()
    index += 1


#################
#  FINAL REPORT #
#################
# Time Calculations
end_timestamp = Date()
end_timestamp_string = timestamp_formatter.format(end_timestamp) 
delta_time_seconds = (end_timestamp.getTime() - start_timestamp.getTime()) / 1000.0
minutes_passed = int(delta_time_seconds / 60)
seconds_passed = int(delta_time_seconds % 60)
print("Started at: {}\nFinished at: {}".format(start_timestamp_string, end_timestamp_string))
print("Total runtime: {}m{}s".format(minutes_passed, seconds_passed))
show_info_popup(message="Macro Finished!\nStarted at: {}\nFinished at: {}\nTotal runtime: {}m{}s".format(start_timestamp_string, end_timestamp_string, minutes_passed, seconds_passed), title="Macro finished")