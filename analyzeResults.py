import pandas as pd
import matplotlib.pyplot as plt
import argparse
import sys
import os

plt.rcParams['figure.dpi'] = 300

def virtualPar2(row, expNames):
    times = []
    for expName in expNames:
        times.append(row[expName + "_par2"])
    return min(times)

def sanity(row, expnames):
    statuses = set()
    for expName in expnames:
        if row[expName + "_solved"]:
            statuses.add(row[expName + "_status"] if row[expName + "_status"] != "ReachedBound" else "OK")

    return len(statuses) <= 1

def virtualSolved(row, expNames):
    virtual_solved = False
    for expName in expNames:
        virtual_solved |= row[expName + "_solved"]
    return virtual_solved

def virtualStatus(row, expNames):
    virtual_status = "Timeout"
    for expName in expNames:
        if row[expName + "_solved"]:
            virtual_status = row[expName + "_status"]
    return virtual_status

def virtualTime(row, expNames):
    times = []
    for expName in expNames:
        times.append(row[expName + "_time"])
    return min(times)

def virtualSolveTime(row, expNames):
    times = []
    for expName in expNames:
        if (row[expName + "_solved"]):
            times.append(row[expName + "_solve_time"])
    if times:
        return min(times)
    else:
        return 0

def add_identity(axes, *line_args, **line_kwargs):
    identity, = axes.plot([], [], *line_args, **line_kwargs)
    def callback(axes):
        low_x, high_x = axes.get_xlim()
        low_y, high_y = axes.get_ylim()
        low = max(low_x, low_y)
        high = min(high_x, high_y)
        identity.set_data([low, high], [low, high])
    callback(axes)
    axes.callbacks.connect('xlim_changed', callback)
    axes.callbacks.connect('ylim_changed', callback)
    return axes

def plotScatter(joined, exp1, exp2, column, plotName="time", xlabel=None, ylabel=None):
    plt.scatter(joined[exp1+"_"+column], joined[exp2+"_"+column], s=20)
    limit = input_args.timeout / 3600
    plt.xlim((-0.05*limit, 1.05*limit))
    plt.ylim((-0.05*limit, 1.05*limit))

    if xlabel == None:
        xlabel = "Time taken by " + exp1 + " (in hours)" 
    if ylabel == None:
        ylabel = "Time taken by " + exp2 + " (in hours)" 
    
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    ax = plt.gca()
    add_identity(ax, color='r', ls='--')
    plt.grid(linestyle = '--', linewidth = 0.5, axis="y")
    plt.grid(linestyle = '--', linewidth = 0.5, axis="x")
    ax.set_aspect('equal')
    plt.gca().set_xticks([0, 0.5, 1, 1.5, 2])
    plt.gca().set_yticks([0, 0.5, 1, 1.5, 2])
    
    plt.savefig(os.path.join(input_args.outDir, "scatter_{2}_{0}_vs_{1}.jpeg".format(exp1, exp2, plotName)))
    plt.clf()

def plotCactus(joined, names, saveAs):
    x_range = 0
    for name in names:
        times = []
        counts = []
        for time in range(0, input_args.timeout+100, 100):
            times.append(time/3600.0)
            counts.append((joined[name + "_time"] < time).sum())

        x_range = max(x_range, counts[-1])

        plt.plot(counts, times, linewidth=1.5, label=name)

    plt.axhline(y=input_args.timeout/(3600 * 1), color = 'grey', linestyle = '--')
    #plt.axhline(y=input_args.timeout/(3600 * 2), color = 'grey', linestyle = '--')

    # ayrange=input_args.timeout/3600
    # plt.xlim((x_range*-0.05, 700))
    # plt.ylim((ayrange*-0.05, ayrange * 1.1))
    plt.legend()
    plt.xlabel("Number of instances solved")
    plt.ylabel("Time taken (in hours)")
    plt.grid(linestyle = '--', linewidth = 0.5, axis="y")
    plt.grid(linestyle = '--', linewidth = 0.5, axis="x")
    plt.savefig(os.path.join(input_args.outDir, saveAs))
    plt.clf()

def plotAndSavePie(col, title, outfile, explode=None):
    if explode == None:
        ax = col.groupby(col).count().plot.pie(ylabel="", title=title, startangle=90, autopct='~%1.0f%%')
    else:
        print(col.groupby(col).count())
        ax = col.groupby(col).count().plot.pie(normalize=True, ylabel="", title=title, startangle=90, autopct='%1.0f%%', explode=explode)
        
    fig = ax.get_figure()
    fig.savefig(os.path.join(input_args.outDir, outfile))
    fig.clear()

def combinedStatus(solvedBys):
    combinedStatus = []
    for i in range(0, len(solvedBys)):
        if (solvedBys[i]):
            combinedStatus.append(input_args.name[i])

    if len(combinedStatus) == 0:
        return "None"
    elif len(combinedStatus) == len(solvedBys):
        return "All"
    else:
        return " & ".join(combinedStatus)

def readAndFixCSV(filepath, name):
    data = pd.read_csv(filepath)
    data = data.drop_duplicates(subset='input', keep="first")
    data = data.set_index('input')
    data = data.add_prefix(name + "_")
    
    data[name + "_status"].fillna("crash", inplace=True)
    data[name + "_time"].fillna(input_args.timeout, inplace=True)
    data[name + "_time_hrs"] = data.apply(lambda row: row[name + "_time"] / 3600, axis=1)
    data[name + "_solved"] = data.apply(lambda row: row[name + "_status"] in ("OK", "NOK", "ReachedBound"), axis=1)
    data[name + "_par2"] = data.apply(lambda row: row[name + "_time"] if row[name + "_solved"] else 2 * input_args.timeout, axis=1)
    data[name + "_solve_time"] = data.apply(lambda row: row[name + "_time"] if row[name + "_solved"] else 0, axis=1)

    return data

def joinResults():
    results = []

    for i in range(0, len(input_args.name)):
        inputFile = input_args.inputFile[i]
        name = input_args.name[i]
        results.append(readAndFixCSV(inputFile, name))

    joined = results[0]

    for i in range(1, len(input_args.name)):
        joined = joined.join(results[i], how="inner", validate="one_to_one")
    
    return joined

if __name__ == "__main__":
    global input_args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputFile', action='append', help='Result file', required=True)
    parser.add_argument('-n', '--name', action='append', help='Experiment name', required=True)
    parser.add_argument('-o', '--outDir', help='outDir', required=True)
    parser.add_argument('-v', '--virtuals', action='append', help='Virtual Combination (use + as delimiter)')
    parser.add_argument('-f', '--force', help='force full', action='store_true')
    parser.add_argument('-t', '--timeout', help='timeout', type=int, default=7200)

    input_args = parser.parse_args()

    if len(input_args.inputFile) != len(input_args.name):
        print("Count of result files and experiment names is not matching")
        sys.exit(1)

    if not input_args.virtuals:
        input_args.virtuals = []

    #Stop if out directory already exists
    if os.path.exists(input_args.outDir):
        if not input_args.force:
            print(input_args.outDir, "already exists may rewrite already present results (use --force to force rewrite)", file=sys.stderr)
            sys.exit(1)
    else:
        os.makedirs(input_args.outDir)
        
    #Join all results into a single csv
    joined = joinResults()
    totalBenchmarks = len(joined)
    
    #Combined Status
    joined["solved_by"] = joined.apply(lambda row: combinedStatus([row[x + "_solved"] for x in input_args.name]), axis=1)
    plotAndSavePie(joined["solved_by"], "", "solved-joined.jpeg")

    #Scatter Plots
    for i in range(0, len(input_args.name)):
        for j in range(i+1, len(input_args.name)):
            plotScatter(joined, input_args.name[i], input_args.name[j], "time_hrs")

    #Generating Virtual Columns
    for virtual in input_args.virtuals:
        items = virtual.split("+")
        joined[virtual + "_status"] = joined.apply(lambda row : virtualStatus(row, items), axis=1)
        joined[virtual + "_solved"] = joined.apply(lambda row : virtualSolved(row, items), axis=1)
        joined[virtual + "_time"] = joined.apply(lambda row : virtualTime(row, items), axis=1)
        joined[virtual + "_solve_time"] = joined.apply(lambda row : virtualSolveTime(row, items), axis=1)
        joined[virtual + "_par2"] = joined.apply(lambda row : virtualPar2(row, items), axis=1)
        #joined[virtual + "_sanity"] = joined.apply(lambda row : sanity(row, virtual.split("+")), axis=1)
        #print("Sanity check: %s for %s" % ("Failed!" if False in joined[virtual + "_sanity"].values else "Passed!", virtual))

    # Plot standalone cactus
    plotCactus(joined, input_args.name, "time-cactus.jpeg")

    # Plot virtuals cactus
    plotCactus(joined, input_args.name + input_args.virtuals, "v-time-cactus.jpeg")

    #cumulative time for benchmarks that were solved by all
    names = []
    times = []
    for name in input_args.name + input_args.virtuals:
        names.append(name)
        times.append(joined[joined["solved_by"] == "All"][name + "_solve_time"].sum() / 3600)

    plt.bar(names, times,  width = 0.8)
    plt.xticks(rotation=12)
    for index, value in enumerate(times):
        plt.text(index, value + max(times) * 0.01, str(round(value, 2)), ha ='center', fontweight = 'bold')
    
    plt.axvline(x=2.5, color = 'grey', linestyle = '--')

    plt.xlabel("Verifier")
    plt.ylabel("Cumulative time taken to verify (in hours)")
    #fig.subplots_adjust(bottom=0.2)
    #fig.savefig(os.path.join(input_args.outDir, "totaltime.jpeg"))
    plt.savefig(os.path.join(input_args.outDir, "totaltime.jpeg"))
    plt.clf()
    plt.cla()

    #Compute Summary
    rows = []
    for name in input_args.name + input_args.virtuals:
        rows.append([
            name,
            joined[name + "_solved"].values.sum(),
            round(joined[name + "_solve_time"].sum() / 3600, 2),
            round(joined[name + "_par2"].sum() / 3600, 2)
        ])
    summary = pd.DataFrame(rows, columns=["Tool", "Total Solved Instances", "Total Solve Time (hrs)", "PAR2 Score (hrs)"])
    print("\n", "-" * 40, "SUMMARY", "-" * 40)
    print(summary.to_string(index=False))
    print("-" * 40, "SUMMARY", "-" * 40, "\n")

    joined.to_csv(os.path.join(input_args.outDir, "combinedResults.csv"))