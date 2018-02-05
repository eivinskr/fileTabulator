"""
	Create LaTeX-table with persistent description of files. Even if you move, rename or change files. 
	Automatically adds new files and remove deleted files from table. 

	Assumes folder structure:
		storagefolder (folder with files)
		scripts (folder)
		 - fileTabulator.py
		sections (folder)
 		- FileTable.tex

    Dependencies:
     - md5
     (pip install md5)
"""
from tabulate import tabulate
import string
import os 
import sys
import subprocess
import threading
import time

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    GREY = '\033[30m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# DictDiffer from https://github.com/hughdbrown/dictdiffer
class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, currentDict, pastDict):
        self.currentDict, self.pastDict = currentDict, pastDict
        self.setCurrent, self.setPast = set(currentDict.keys()), set(pastDict.keys())
        self.intersect = self.setCurrent.intersection(self.setPast)
    def added(self):
        return self.setCurrent - self.intersect 
    def deleted(self):
        return self.setPast - self.intersect 
    def moved(self):
        return set(o for o in self.intersect if self.pastDict[o] != self.currentDict[o])
    def unchanged(self):
        return set(o for o in self.intersect if self.pastDict[o] == self.currentDict[o])

#CursorAnimation from https://gist.github.com/kholis/2603409 
class CursorAnimation(threading.Thread):
	def __init__(self):
		self.flag = True
		self.animation_char = "|/-\\"
		self.idx = 0
		threading.Thread.__init__(self)

	def run(self):
		while self.flag:
			print "Processing... ",
			print self.animation_char[self.idx % len(self.animation_char)] + "\r",
			self.idx += 1
			time.sleep(0.1)

	def stop(self):
		self.flag = False

spin = CursorAnimation()
outputFilename = 'FileTable.tex'
outputFilepath = '../sections/'
storageFolder = 'fileStorage'
storage_path = os.path.relpath('../'+storageFolder, os.path.dirname(__file__))

hashesFromStorage = {} # key=hash and value=path 
hashesFromLatexFile = {} #key=hash and value=path 
linesFromLatexFile = {} #key=hash and value=list[path,description]

updatedTableContent = [] #Content to be written

addedFiles = {} #Hashvalue
unchangedFiles = {} #Hashvalue
movedFiles = {} #Hashvalue
deletedFiles = {} #Hashvalue
changedFiles= {} #key = path, value = [newhash, oldhash]
duplicateFiles = set()

def listDuplicates(seq):
  seen = set()
  seen_add = seen.add
  seen_twice = set(line for line in seq if line[0] in seen or seen_add(line[0]))
  
  return list(seen_twice)

def identifyDuplicateHashes(storageDict, results):
	if (len(storageDict) != len(results)):
		print(bcolors.WARNING + "There are duplicate files!" + bcolors.ENDC)
		seen_twice = listDuplicates(results)
		for hashValue in seen_twice:
			all_matching = filter(lambda x: x[0] == hashValue[0],results)
			duplicateFiles.add(tuple(all_matching))

def generateHashesFromFilePaths(storageDict,pathSet):
	print(bcolors.OKGREEN + "Generating hashes of files in: " + storageFolder + bcolors.ENDC)
	results = []
	for path in pathSet:
		tmp = subprocess.Popen('md5 "../'+storageFolder+path+'"',shell=True,executable="/bin/bash",stdout=subprocess.PIPE)
		printVar = tmp.stdout.read()
		tmp = printVar.split("= ")
		hashValue = tmp[1].strip()

		hashOfEmptyFile = "d41d8cd98f00b204e9800998ecf8427e"
		if (hashValue == hashOfEmptyFile):
			print(bcolors.WARNING + "Ignoring empty file at: " + path + bcolors.ENDC)
		else:
			results.append((tmp[1].strip(),path)) 
	storageDict.update(results)
	identifyDuplicateHashes(storageDict, results)

def getFilePathsIn(folder):
	print(bcolors.OKGREEN + "Parsing storage folder ("+folder+") for file paths" +bcolors.ENDC)
	filePaths = set() 
	storageFolder_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', folder)
	for root, dirs, files in os.walk(storageFolder_path):
		basePath = string.split(root,folder)[1]
		for file in files:
			if (file == ".DS_Store" or file == "/.DS_Store"):
				print(bcolors.WARNING+"Ignoring .DS_store file at:" + basePath +"/" +file +bcolors.ENDC)
			else:
				filePaths.add(basePath+"/"+file)
	return filePaths

def parseStorageFolderForFileHashesAndFilePaths():
	filePaths = getFilePathsIn(storageFolder) 
	generateHashesFromFilePaths(hashesFromStorage, filePaths)

def checkForIllegalCharacter(illegalCharacter, folderPath, fileName):
	if illegalCharacter in folderPath:
		sys.exit(bcolors.FAIL + "FAILURE: folder name cannot contain character '" + illegalCharacter + "'. "+
				"It is used as separator in LaTeX table. \nInvalid folder is in path "+
				folderPath+bcolors.ENDC)
	if illegalCharacter in fileName:
		sys.exit(bcolors.FAIL + "FAILURE: file name cannot contain character '" + illegalCharacter + "'. "+
				"It is used as separator in LaTeX table. \nInvalid filename is "+
				folderPath+"/"+fileName + bcolors.ENDC)

def buildUpdatedTableContent():
	for hashValue in sorted(addedFiles):
		filePath = hashesFromStorage[hashValue]
		#print("Added: " + filePath)
		description = ""
		pathElements = filePath.rsplit("/", 1)
		folderPath = pathElements[0]
		fileName = pathElements[1]
		checkForIllegalCharacter("&", folderPath, fileName)
		updatedTableContent.append([folderPath, fileName, description, hashValue])

	for hashValue in sorted(unchangedFiles):
		line = linesFromLatexFile[hashValue]
		filePath = line[0]
		description = line[1]
		pathElements = filePath.rsplit("/", 1)
		folderPath = pathElements[0]
		fileName = pathElements[1]
		updatedTableContent.append([folderPath, fileName, description, hashValue])

	for hashValue in sorted(movedFiles):
		filePath = hashesFromStorage[hashValue]
		oldFilePath = hashesFromLatexFile[hashValue]
		print("Moved from: " + oldFilePath + "\nMoved to: " + filePath)
		pathElements = filePath.rsplit("/", 1)
		folderPath = pathElements[0]
		fileName = pathElements[1]
		checkForIllegalCharacter("&", folderPath, fileName)
		description = linesFromLatexFile[hashValue][1]
		updatedTableContent.append([folderPath, fileName, description, hashValue]) #Empty description

	for filePath, hashList in sorted(changedFiles.items()):
		description = linesFromLatexFile[hashList[0]][1]
		pathElements = filePath.rsplit("/", 1)
		folderPath = pathElements[0]
		fileName = pathElements[1]
		updatedTableContent.append([folderPath, fileName, description, hashList[1]])
		#print("Changed: " + filePath)

def writeUpdatedTableContentToFile():
	file = open(outputFilepath + outputFilename, 'w')
	file.write('%!TEX root = ../main.tex\n')
	file.write('% Generated by fileTabulator.py.\n% Please only edit descriptions\n')
	file.write('\\begin{landscape}\n\centering\n\\begin{longtabu} to \linewidth{|X[1,l]|X[2,l]|X[1,l]H|}\n\\taburowcolors[1]2{lightgrey..white} \n\\toprule\n\caption{File List}\label{tab:file_list}\\\\\n')
	file.write('\hline\n\\textbf{Path} & \\textbf{Filename}  & \\textbf{Description} & \\textbf{Hash} \\\\\n\hline\n\endfirsthead\n\multicolumn{4}{l}\n{\\tablename\ \\thetable\ -- \\textit{Continued from previous page}} \\\\')
	file.write('\n\hline\n\\textbf{Path} & \\textbf{Filename} & \\textbf{Description} & \\textbf{Hash} \\\\\n\hline\n\endhead\n\hline \multicolumn{4}{l}{\\textit{Continued on next page}} \\\\\endfoot\n\hline\n\endlastfoot\n\\taburowcolors[1]2{lightgrey..white}')
	file.write(tabulate(sorted(updatedTableContent), tablefmt="latex").split('\hline',2)[1])
	file.write('\end{longtabu}\n\end{landscape}')
	file.close()
	print(bcolors.OKGREEN + "Successfully wrote new table to file '" + outputFilename +"' in path '" + outputFilepath +"'." + bcolors.ENDC);

def parseLatexFile():
	print(bcolors.OKGREEN + "Parsing LaTeX-file ("+outputFilename + ") for file paths and file hashes" + bcolors.ENDC)
	try:
		tableFile = open(outputFilepath + outputFilename, 'r')
		for i in xrange(23):
			try:
				tableFile.next()
			except StopIteration:
				print(bcolors.WARNING + "File FileTable.tex is empty. Trying to build new file." + bcolors.ENDC)
				break
		for line in tableFile:
				values = string.split(line.replace("\_", "_"),'&')
				if (len(values)==1): 
					tableFile.close()
					break
				path = values[0].strip()
				filename = values[1].strip()
				description = values[2].strip()
				hashValue = values[3][:-3].strip()
				linesFromLatexFile[hashValue] = [path+"/"+filename, description]
				hashesFromLatexFile[hashValue] = path+"/"+filename
	except IOError:
		print(bcolors.FAIL + "Error: File FileTable.tex does not appear to exist." + bcolors.ENDC)
	

def categorizeHashes(current_dict, past_dict):
	global addedFiles
	global unchangedFiles
	global movedFiles
	global deletedFiles
	global changedFiles

	commonFilePaths = set()
	dictDiffer = DictDiffer(current_dict, past_dict)
	
	unchangedFiles = dictDiffer.unchanged()
	addedFiles = dictDiffer.added()
	movedFiles = dictDiffer.moved() 
	deletedFiles = dictDiffer.deleted()
	
	deletedFilesTmp = deletedFiles.copy()
	addedFilesTmp = addedFiles.copy()

	for hashValueAdded in addedFilesTmp:
		for hashValueDeleted in deletedFilesTmp:
			if (current_dict[hashValueAdded]==past_dict[hashValueDeleted]):
				changedFiles[current_dict[hashValueAdded]] = [hashValueDeleted, hashValueAdded]
				addedFiles.remove(hashValueAdded)
				deletedFiles.remove(hashValueDeleted)

def prettyPrintPathFromHash(hashStorage, dictionary):
	print("{:_^40}").format("_")
	for key in sorted(dictionary):
	  print("{:<40}".format(hashStorage[key]))
	print("{:_^40}").format("_")
	print("\n")

def prettyPrintPathFromNewHash(dictionary):
	prettyPrintPathFromHash(hashesFromStorage, dictionary)

def prettyPrintPathFromOldHash(dictionary):
	prettyPrintPathFromHash(hashesFromLatexFile, dictionary)

def prettyPrintPathAndDescriptionFromDictionary(dictionary):
	print("{:_^180}").format("_")
	print("{:_^100} {:_^80}".format('Path: ','Description: ')) 
	for key in sorted(dictionary):
	  print("{:<100} {:<80}".format(key, dictionary[key]))
	print("{:_^180}").format("_")
	print("\n")

def prettyPrintPathFromDict(dictionary):
	print("{:_^40}").format("_")
	for key in sorted(dictionary):
	 	print("{:<40}".format(key))
	print("{:_^40}").format("_")
	print("\n")

def prettyPrintPathAndDescriptionFromListOfLists(listOfLists):
	print("{:_^180}").format("_")
	print("{:_^100} {:_^80}".format('Path: ','Description: ')) 
	for list in listOfLists:
	  print("{:<100} {:<80}".format(list[0]+"/"+list[1], list[2]))
	print("{:_^180}").format("_")
	print("\n")

def prettyPrintText(text):
	print("{:_^40}").format("_")
	print("{:^47}").format(bcolors.BOLD + text + bcolors.ENDC)
	print("{:_^40}").format("_")

def prettyPrintWarning(text):
	print("{:_^40}").format("_")
	print("{:^47}").format(bcolors.WARNING + text + bcolors.ENDC)
	print("{:_^40}").format("_")

def prettyPrintTitle(title):
	print("{:_^40}").format("_")
	print("{:^47}").format(bcolors.BOLD + title + bcolors.ENDC)

def prettyPrintDuplicateFiles(dictionary):
	print("{:_^180}").format("_")
	print("{:_^100} {:_^80}".format('Path: ','Hash: ')) 
	for key in sorted(dictionary):
		for hashValue, path in key:
			print("{:<100} {:<80}".format(path, hashValue))
		print("\n")
	print("{:_^180}").format("_")
	print("\n")

def printResults():
	print("{:^120}").format(bcolors.BOLD + "Content of " + outputFilename +": " + bcolors.ENDC)
	prettyPrintPathAndDescriptionFromListOfLists(updatedTableContent)
	if (unchangedFiles !=  set() ):
		prettyPrintTitle("Unchanged Files: ")
		prettyPrintPathFromNewHash(unchangedFiles)
	else:
		prettyPrintText("No unchanged files(!)")
	print(bcolors.BOLD + str(len(updatedTableContent)) + " Files from folder " + storageFolder + " in " + outputFilename + bcolors.ENDC)	
	if (addedFiles !=  set() ):
		title = "Adding new files from "
		if (len(addedFiles)==1):
			title = "Adding new file from "
		prettyPrintTitle(title+storageFolder+": ")	
		prettyPrintPathFromNewHash(addedFiles)
	else:
		prettyPrintText("No files has been added")
	if (movedFiles !=  set() ):
		prettyPrintTitle("Moved Files: ")
		prettyPrintPathFromOldHash(movedFiles)
	else:
		prettyPrintText("No files has been moved")
	if (changedFiles !=  {} ):
		prettyPrintTitle("Changed Files: ")
		prettyPrintPathFromDict(changedFiles)
	else:
		prettyPrintText("No files has been changed")
	if (deletedFiles !=  set() ):
		prettyPrintTitle("Deleted Files: ")
		prettyPrintPathFromOldHash(deletedFiles)
	else:
		prettyPrintText("No files has been deleted")
	if (duplicateFiles !=  set() ):
		prettyPrintWarning("WARNING: Duplicate files, only one is stored in LaTex-file")
		prettyPrintTitle("Duplicate Files(!): ")
		prettyPrintDuplicateFiles(duplicateFiles)
	else:
		prettyPrintText("No duplicate files")

spin.start()
parseStorageFolderForFileHashesAndFilePaths()
parseLatexFile()

print(bcolors.OKGREEN + "Categorizing hashes from LaTeX-file and storage folder"+ bcolors.ENDC)
categorizeHashes(hashesFromStorage, hashesFromLatexFile)

print(bcolors.OKGREEN + "Building Table Content " + bcolors.ENDC)
buildUpdatedTableContent()
printResults()
print(bcolors.OKGREEN + "Writing table to LaTex-file " + outputFilename + bcolors.ENDC)
writeUpdatedTableContentToFile()
spin.stop()