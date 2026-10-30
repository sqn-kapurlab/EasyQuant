[README.md](https://github.com/user-attachments/files/34174088/README.md)
# **EasyQuant**

EasyQuant is an ImageJ  pipeline designed to streamline the processing, segmentation, and quantification of cells/objects from microscopy data.  
The repository includes **three separate workflows**, allowing users to run the full pipeline or choose only the components they need.

---

##  **Repository Structure**

Inside the **EasyQuant** folder, you will find three different executable pipelines:

### 1. **EasyQuant**  
The complete end-to-end workflow.  
This pipeline guides the user from raw image files all the way to a finished Excel report containing quantified cell counts.

**Features include:**
- Selection of desired frames and channels directly from the raw data  
- Automated segmentation using **Labkit**  
- Export of an Excel file summarizing the number of detected cells for all selected frames and channels  

---
### 2. **EasyQuant_BatchProcessingOnly**  
A standalone preprocessing module.  

This pipeline performs only the **batch selection and extraction** of user-specified frames and channels from raw image files.  
It is intended for users who wish to prepare their images first and apply segmentation later.

---

### 3. **EasyQuant_CellCountingOnly**  
A standalone segmentation module.  

This version performs only the **cell-counting process**, using previously generated Labkit classifiers.  
It outputs a .csv file with the quantifications for each selected frame and channel—ideal for users who already have pre-processed image subsets.

---

##  **Why Modular Pipelines?**

While the full EasyQuant workflow provides a complete automated analysis solution, we recognize that many users may prefer—or require—to run only specific steps.  
By separating the pipeline into distinct modules, EasyQuant offers maximum flexibility without compromising ease of use.

---

##  **Output**

All workflows that include segmentation produce:
- A .csv file summarizing detected cells  
- Quantifications per frame and per channel  
- Reproducible results using established Labkit classifiers  
