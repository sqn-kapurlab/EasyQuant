'''
Authors: Rita Carlota, Sofia Pascoal, Carolien Zeelen, Casper van der Kerk, Romy Meier 
Main goal: Run classifiers based on channel in one image or multiple images inside a folder
Requirements: No ImageJ plugins needed
Date: July 2025
'''

import os
import csv
import sys

from ij import IJ, WindowManager, Prefs
from ij.measure import ResultsTable
from ij.text import TextWindow

from java.text import SimpleDateFormat
from java.util import Date
from javax.swing import JFileChooser, JFrame, JOptionPane, JDialog
from java.lang import System, Runtime
from java.io import File
from java.awt.event import WindowAdapter

##############
# CONSTANTS #
#############
PREF_KEY = "EasyQuant.lastDir"

##########################
#  VARIABLE DEFINITIONS  #
##########################
timestamp_formatter = SimpleDateFormat("yyyy-MM-dd'T'HH-mm-ss")
date_formatter =  SimpleDateFormat("yyyy_MM_dd") 

# This will be the base of the output directory structure. 
# It will be appended with a timestamp with format: `_DD-MM-YYYYTHH-MM-SS`
output_subdirectory_name = "EasyQuant_CellCountingOnly"

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
#@ String (label="Select desired channels:", visibility='MESSAGE', value="") message
#@ Boolean (label="Channel 1", value=true) channel_1
#@ Boolean (label="Channel 2", value=true) channel_2
#@ Boolean (label="Channel 3", value=false) channel_3
#@ Boolean (label="Channel 4", value=false) channel_4

#@ Integer (label="Minimum particle size:", min=0, value=0) min_particle_size
#@ Integer (label="Maximum particle size (-1 is Infinity):", value=-1) max_particle_size

#@ String (label="Add Experimental ID", value="1") experimental_id

# HANDLE ERRORS FROM USER INPUT
# Replace spaces in string variables
experimental_id = experimental_id.replace(" ", "")

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

# Check if max is larger than min
if max_particle_size != -1 and min_particle_size > max_particle_size:
    IJ.error("Minimum particle size is larger than maximum particle size.\nPlease use a max value that is larger than the min value.")
    raise Exception("Maximum particle size must be larger than the minimum")

# Set max_particle_size to 'Infinity' if provided value is -1
if max_particle_size == -1:
    max_particle_size = "Infinity"

size_parameters = "{}-{}".format(str(min_particle_size), str(max_particle_size))
start_timestamp = Date()
start_timestamp_string = timestamp_formatter.format(start_timestamp) 
current_date = date_formatter.format(Date()) 

# Setting the write_headers flag to True so that the first iteration of the for-loop writes the headers
# in your CSV file but iterations after the first do not
write_headers = True

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

######################################
#  SELECT FILE OR FOLDER TO ANALYSE  #
######################################
if choice_input == "Process single file":
    IJ.run("Close All")
    # Select one image to process
    file_path = path_chooser_dialog(dialog_title="Select a file to process", directory = False)
    # Get output directory
    output_directory = path_chooser_dialog(dialog_title = "Select Output Directory", directory = True)
    output_directory_root = os.path.join(output_directory, output_subdirectory_name + "_" + start_timestamp_string)
    mask_output_directory = os.path.join(output_directory_root, "Masks")
    os.makedirs(mask_output_directory)
    # Generate path and filename for the results CSV file
    csv_file_path = os.path.join(output_directory_root, "results_" + start_timestamp_string + ".csv")
    
    # Write a text file documenting the input parameters
    text_file_path = os.path.join(output_directory_root, 'input_parameters.txt')
    with open(text_file_path, 'w') as f:
        f.write(start_timestamp_string + '\n\n')
        f.write("Macro used: Cell Counting\n")
        f.write("Processing mode: {}\n".format(choice_input))
        for i in channel_string.split(','):
            if len(i) == 1: # When splitting a string that starts with `,` an empty value may appear in the resulting list, causing the script to fail. This if-statement checks for that.
                f.write("Channel {} classifier: {}\n".format(i, eval("classifier_channel" + i + "_path")))
        f.write("Minimum selected particle size: {}\n".format(min_particle_size))
        f.write("Maximum selected particle size: {}\n".format(max_particle_size))
    f.close()

    IJ.openImage(file_path).show() # Open selected file
    imp = WindowManager.getCurrentImage()
    image_name = imp.getTitle()

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
    
    # Close all windows and free up memory when we're done
    close_all()
    System.gc() 
    Runtime.getRuntime().freeMemory()

elif choice_input == "Process current open image":
    imp = WindowManager.getCurrentImage()
    image_name = imp.getTitle()
    # Get output directory
    output_directory = path_chooser_dialog(dialog_title = "Select Output Directory", directory = True)
    output_directory_root = os.path.join(output_directory, output_subdirectory_name + "_" + start_timestamp_string)
    mask_output_directory = os.path.join(output_directory_root, "Masks")
    os.makedirs(mask_output_directory)
    # Generate path and filename for the results CSV file
    csv_file_path = os.path.join(output_directory_root, "results_" + start_timestamp_string + ".csv")
    
    # Write a text file documenting the input parameters
    text_file_path = os.path.join(output_directory_root, 'input_parameters.txt')
    with open(text_file_path, 'w') as f:
        f.write(start_timestamp_string + '\n\n')
        f.write("Macro used: Cell Counting\n")
        f.write("Processing mode: {}\n".format(choice_input))
        for i in channel_string.split(','):
            if len(i) == 1: # When splitting a string that starts with `,` an empty value may appear in the resulting list, causing the script to fail. This if-statement checks for that.
                f.write("Channel {} classifier: {}\n".format(i, eval("classifier_channel" + i + "_path")))
        f.write("Minimum selected particle size: {}\n".format(min_particle_size))
        f.write("Maximum selected particle size: {}\n".format(max_particle_size))
    f.close()

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
    
    # Close all windows and free up memory when we're done
    close_all()
    System.gc() 
    Runtime.getRuntime().freeMemory()

# Process all images in the folder, based on channel termination
elif choice_input == "Process entire directory":
    # Closing all open windows
    # close_all()
    IJ.run("Close All")
    dir_path_input = path_chooser_dialog(dialog_title="Select input folder to batch process all images", directory = True)
    # Get output directory
    output_directory = path_chooser_dialog(dialog_title = "Select Output Directory", directory = True)
    output_directory_root = os.path.join(output_directory, output_subdirectory_name + "_" + start_timestamp_string)
    mask_output_directory = os.path.join(output_directory_root, "Masks")
    os.makedirs(mask_output_directory)
    # Generate path and filename for the results CSV file
    csv_file_path = os.path.join(output_directory_root, "results_" + start_timestamp_string + ".csv")

    # Write a text file documenting the input parameters
    text_file_path = os.path.join(output_directory_root, 'input_parameters.txt')
    with open(text_file_path, 'w') as f:
        f.write(start_timestamp_string + '\n\n')
        f.write("Macro used: Cell Counting\n")
        f.write("Processing mode: {}\n".format(choice_input))
        for i in channel_string.split(','):
            if len(i) == 1: # When splitting a string that starts with `,` an empty value may appear in the resulting list, causing the script to fail. This if-statement checks for that.
                f.write("Channel {} classifier: {}\n".format(i, eval("classifier_channel" + i + "_path")))
        f.write("Minimum selected particle size: {}\n".format(min_particle_size))
        f.write("Maximum selected particle size: {}\n".format(max_particle_size))
    f.close()

    # Get all file names in the chosen input directory
    dir_list = [f for f in os.listdir(dir_path_input) if not f.startswith('.')] # This avoids hidden files / files that start with "." (like .DS_Store on MacOS)
    print("Amount of files in chosen directory: {}".format(len(dir_list)))

    # Initializing an index to keep track of which image we are working on for the progress bar
    index = 1

    for image_name in dir_list:
        print("\nNow processing image: {} [{}/{}]".format(image_name, index, len(dir_list)))
        image_path = os.path.join(dir_path_input, image_name)
        
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

# Time Calculations
end_timestamp = Date()
end_timestamp_string = timestamp_formatter.format(end_timestamp) 
delta_time_seconds = (end_timestamp.getTime() - start_timestamp.getTime()) / 1000.0
minutes_passed = int(delta_time_seconds / 60)
seconds_passed = int(delta_time_seconds % 60)
print("Started at: {}\nFinished at: {}".format(start_timestamp_string, end_timestamp_string))
print("Total runtime: {}m{}s".format(minutes_passed, seconds_passed))
show_info_popup(message="Macro Finished!\nStarted at: {}\nFinished at: {}\nTotal runtime: {}m{}s".format(start_timestamp_string, end_timestamp_string, minutes_passed, seconds_passed), title="Macro finished")