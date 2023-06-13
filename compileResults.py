import sys
import os
import re
import pandas as pd

def AddResult(result, item):
    if item:
        result.append(item)
    else:
        result.append("")

def findResultInFile(filePath):

    with open(filePath) as fp:
        txt = fp.read()
        status = re.search("Return status: ([A-Za-z0-9]+)", txt)
        time = re.search("Total Time: ([0-9]*.[0-9]*)", txt)
        quantifierInSummary = re.search("Quantifier in summary: True", txt)
        perror = re.search("(Prover error: .*)|(Stopping: Insufficient .*)|(Stopping: Exception .*)|(Starting Server - Unhandled exception.*)|(Unhandled exception. System.ArgumentException.*)|(Unhandled exception. System.ArgumentOutOfRangeException.*)", txt)
        
        result = []
        #Add status to result
        if status:
            AddResult(result, status.group(1))
        elif perror:
            AddResult(result, "crash")
        else:
            AddResult(result, "")
        
        #Add time to result
        if time:
            AddResult(result, time.group(1))
        else:
            AddResult(result, "")

        #Add quantifierInSummary to result
        #If quantifier is present in the summary then the results of the prover
        #Cannot be trusted. 
        if quantifierInSummary:
            AddResult(result, "True")
        else:
            AddResult(result, "False")

        #Add details about error
        if perror:
            AddResult(result, perror.group(0))
        else:
            AddResult(result, "")

        return result

def getResultFromDir(directory):
    result = []
    for filename in os.listdir(directory):
        if filename.endswith(".bpl.txt"):
            inputFile = os.path.splitext(filename)[0]
            filepath = os.path.join(directory, filename)
            result.append([inputFile] + findResultInFile(filepath))

    return result

def run(directory):
    result = pd.DataFrame(getResultFromDir(directory), columns=[
        "input",
        "status",
        "time",
        "quantifierInSummary",
        "comment"])
    outfile = os.path.join(directory, "result.csv")
    result.to_csv(outfile, index=False)

if __name__ == "__main__":
    run(sys.argv[1])
