import os
import sys
import subprocess
import psutil
import argparse

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

def runExperiment(config):
    global tasksCount
    global tasksFinished
    global taskLock
    try:
        job = [
            "corral-traceInlining/bin/Debug/net6.0/corral",
            config["inputFile"],
            "/trackAllVars",
            "/recursionBound:" + str(input_args.recBound),
        ]

        if config["inputFile"].endswith(".bpl.bpl"):
            job.append("/si")
        
        timeout = 60 * input_args.timeout

        if len(config["cmdArgs"]) > 0:
            job += config["cmdArgs"]

        if "smtLogFile" in config:
            job.append("/proverLog:" + config["smtLogFile"])
        
        if "outputFile" in config:
            with open(config["outputFile"], "w") as outFile:
                logRunningConfig(outFile, config["inputFile"], config["smtLogFile"] if "smtLogFile" in config else None)
                outFile.flush()
                proc = subprocess.Popen(job, stdout=outFile, stderr=outFile)
                outs, errs = proc.communicate(timeout=timeout)
                if(errs):
                    print(config["inputFile"], errs)
                    print("-+" * 30)

    except subprocess.TimeoutExpired:
        print("inside timeout", config["execType"] + ":" + config["inputFile"])
        try:
            parent = psutil.Process(proc.pid)
            children = parent.children(recursive=True)
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            print('Failed to find or access process.')
            return

        for child in children:
            try:
                child.kill()
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                print('Failed to kill process child.')
        try:
            parent.kill()
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            print('Failed to kill process.')

        with open(config["outputFile"], "a") as outFile:
            outFile.write("Return status: TIMEDOUT")

    except Exception as e:
        print("Error", e)

    finally:
        taskLock.acquire()
        tasksFinished += 1
        print("Progress: " + str(tasksFinished) + "/" + str(tasksCount), end="\r")
        taskLock.release()


input_args = {}
taskLock = Lock()
tasksCount = 0
tasksFinished = 0

def logRunningConfig(stream, inputFile=None, smtFile=None):
    stream.write("-" * 40 + "\n")
    stream.write("Running Experiment(s) with following parameters:" + "\n\n")
    stream.write("  Input Directory: " + input_args.inDir + "\n")
    stream.write("  Output Directory: " + input_args.outDir + "\n")
    
    if inputFile != None:
        stream.write("  Input File: " + inputFile + "\n")
    
    stream.write("  Generate SMT Logs: " + str(input_args.genSMT) + "\n")
    
    if smtFile != None:
        stream.write("  SMT Log File: " + smtFile + "\n")
    
    stream.write("  Timeout (per benchmark): " + str(input_args.timeout) + " mins" + "\n")
    stream.write("  Recursion Bound: " + str(input_args.recBound) + "\n")
    stream.write("  Max Workers: " + str(input_args.workers) + "\n")
    stream.write("-" * 40 + "\n")

typeToCmdArg = {
    "corral" : [],
    "legion" : ["/underWidenSI"],
    "saransh" : ["/traceInlining"],
}

def main():
    global input_args
    global tasksCount
    parser = argparse.ArgumentParser()
    parser.add_argument('--inDir', '-i', help='directory containing benchmarks', required=True, type=str)
    parser.add_argument('--outDir', '-o', help='output directory', required=True, type=str)
    parser.add_argument('--timeout', help='timeout(in mins)', default=120, type=int)
    parser.add_argument('--recBound', help='Recursion Bound', default=3, type=int)
    parser.add_argument('--workers', help='Number of benchmarks to run in parallel', default=1, type=int)
    parser.add_argument('--genSMT', help='Generate SMT Logs', default=False, type=bool)
    parser.add_argument('-t','--type', nargs='+', help='What to run?', default=["saransh", "corral", "legion"])
    input_args = parser.parse_args()
    logRunningConfig(sys.stdout)

    for type in input_args.type:
        typeOutDir = os.path.join(input_args.outDir, type)
        if os.path.exists(typeOutDir):
           print("Warning: Output folder for " + type + " already exists may contains old results")
        else:
            os.makedirs(typeOutDir)

    tasks = []
    for file_name in os.listdir(input_args.inDir):
        if file_name.endswith(".bpl"):
            for type in input_args.type:
                config = {
                    "inputFile" : os.path.abspath(os.path.join(input_args.inDir, file_name)),
                    "outputFile" : os.path.abspath(os.path.join(input_args.outDir, type, file_name + ".txt")),
                    "cmdArgs" : typeToCmdArg[type]
                }
                if input_args.genSMT:
                    config["smtLogFile"] = os.path.abspath(os.path.join(input_args.outDir, type, file_name + ".smt2"))
                    
                tasks.append(config)

    tasksCount = len(tasks)
    print("-" * 40)
    print("Progress: " + str(tasksFinished) + "/" + str(tasksCount), end="\r")
    with ThreadPoolExecutor(max_workers = input_args.workers) as executor:
        executor.map(runExperiment, tasks)


if __name__ == "__main__":
    main()
    
    

