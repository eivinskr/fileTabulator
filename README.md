# fileTabulator
Create a LaTeX-table with persistent description of files. Even if files are moved, renamed or changed. Automatically add new files and remove deleted files from table. 

## How does it work?
The script: 
1. Parses a folder of choise recursively, storing the filepath and MD5-hash of each file. It ignores empty files, ".DS-store"-files and gives a warning of duplicate files (same hash).  
2. Parses the existing output-file (if any) for previous filepaths and MD5-hashes. 
3. Categorizes hashes in sets of added, unchanged, moved, deleted or changed files. 
4. Creates a table with relative path from folder of choice, filename, description and hashvalue. 
5. Writes the table to LaTeX, hiding the row with hashvalues. 

## Screenshots
fileTabulator.py: 
![alt text](https://github.com/eivinskr/fileTabulator/blob/master/images/Screenshot%20fileTabulator.png?raw=true "Screenshot of fileTabulator.py")


FileTable.tex: 
![alt text](https://github.com/eivinskr/fileTabulator/blob/master/images/Screenshot%20FileTable.png?raw=true "Screenshot of FileTable.tex")

## Dependencies
 - md5 (pip install md5)
