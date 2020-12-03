import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

METHODS = ["Tax", "Taymouri", "Camargo random", "Camargo argmax", "Lin", "Di Mauro", "EDBN", "Baseline"]
DATA = ["Helpdesk.csv", "BPIC12W.csv", "BPIC12.csv", "BPIC15_1_sorted_new.csv",
        "BPIC15_3_sorted_new.csv", "BPIC15_5_sorted_new.csv"]

DATA_NAMES = {}
DATA_NAMES["Helpdesk.csv"] = "Helpdesk"
DATA_NAMES["BPIC12W.csv"] = "BPIC12W"
DATA_NAMES["BPIC12.csv"] = "BPIC12"
DATA_NAMES["BPIC15_1_sorted_new.csv"] = "BPIC15\_1"
DATA_NAMES["BPIC15_2_sorted_new.csv"] = "BPIC15\_2"
DATA_NAMES["BPIC15_3_sorted_new.csv"] = "BPIC15\_3"
DATA_NAMES["BPIC15_4_sorted_new.csv"] = "BPIC15\_4"
DATA_NAMES["BPIC15_5_sorted_new.csv"] = "BPIC15\_5"

X_AXIS = {}
X_AXIS["prefix_size"] = "Size of prefix"
X_AXIS["end_event"] = "Add end event"
X_AXIS["split_method"] = "Split method"
X_AXIS["split_cases"] = "Split cases"
X_AXIS["train_percentage"] = "Percentage train data"

result_file = "Split Method/split_method.txt"

MARKERS = ["o", "v", "^", "s", "+", "D", "<", ">", "p"]

tableau20 = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),
             (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),
             (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),
             (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),
             (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]

for i in range(len(tableau20)):
    r, g, b = tableau20[i]
    tableau20[i] = (r / 255., g / 255., b / 255.)

def read_result_file(result_file):
    with open(result_file, "r") as finn:
        result_string = finn.read()

    single_results = result_string.split("====================================")[:-1]

    records = []
    for result in single_results:
        splitted_result = result.split("\n")
        if splitted_result[0] == "":
            splitted_result = splitted_result[2:]
        record = dict(data=splitted_result[0].split(" ")[-1].split("/")[-1],
                      prefix_size=splitted_result[1].split(" ")[-1],
                      end_event=splitted_result[2].split(" ")[-1],
                      split_method=splitted_result[3].split(" ")[-1],
                      split_cases=splitted_result[4].split(" ")[-1],
                      train_percentage=splitted_result[5].split(" ")[-1])
        for acc_string in splitted_result[8:-1]:
            method, acc = acc_string.split(": ")
            if method == "Camargo":
                acc_list = eval(acc)
                record["Camargo random"] = float(acc_list[0])
                record["Camargo argmax"] = float(acc_list[1])
            else:
                record[method] = float(acc)
        records.append(record)

    result_data = pd.DataFrame()
    result_data = result_data.from_records(records)
    print(result_data.dtypes)
    return result_data

def plot_acc_values(dataframe, method, x_axis, divide=None, title=""):
    if divide is not None:
        for group_id, group in dataframe.groupby(divide):
            plt.scatter(group[x_axis], group[method], label=group_id)
    else:
        plt.scatter(dataframe[x_axis], dataframe[method])
    plt.title(title)
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=3)
    plt.show()


def plot_all_acc_values(dataframe, x_axis, title=""):
    for m in METHODS:
        plt.plot(dataframe[x_axis], dataframe[m], "-o", label=m)
    plt.title(title)
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=3)
    plt.show()


def get_max_per_x(dataframe, x_axis):
    # dataframe = dataframe[dataframe["end_event"] == "False"]
    result = {}
    for prefix, group in dataframe.groupby(x_axis):
        for m in METHODS:
            if m not in result:
                result[m] = []
            result[m].append((prefix, max(group[m])))
    return result


def plot_max_acc_values(max_vals, title=""):
    for method in max_vals:
        x = [i[0] for i in max_vals[method]]
        y = [i[1] for i in max_vals[method]]
        plt.plot(x, y, "-o", label=method)
    plt.ylim([0.7, 1])
    plt.title(title)
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=3)
    plt.show()


def create_latex(output_folder, dataframe, x_axis, use_methods=None):
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)
        os.mkdir(os.path.join(output_folder, "figures"))

    output = ""

    if use_methods is None:
        use_methods = METHODS

    # Create graphs
    for d in DATA:
        d_dataframe = dataframe[dataframe["data"] == d]
        d_name = d.split("/")[-1].split(".")[0]
        accs = []
        for m in use_methods:
            plt.plot(d_dataframe[x_axis], d_dataframe[m], "o")
            accs.append((m, d_dataframe[m].values))
        plt.title(d_name)
        # plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=3)
        fig_location = os.path.join(output_folder, "figures", d_name)
        plt.savefig(fig_location)
        plt.close()

        num_x_vals = len(d_dataframe[x_axis])

        print(accs)

        output += "\subsection{%s}" % d_name.replace("_", "\_")

        for i in range(len(d_dataframe[x_axis])):
            output += "\\begin{table}[h!]"
            output += "\centering"
            output += "\caption{Results for value \\textbf{%s} of axis %s}" % (d_dataframe[x_axis].values[i], x_axis.replace("_", " "))
            output += "\\begin{tabular}{l | l}"
            output += "Method & Accuracy\\\\"
            output += "\hline "
            tmp = sorted([(m[0], m[1][i]) for m in accs], key=lambda l:l[1], reverse=True)
            for result_tuple in tmp:
                output += "%s & %f \\\\" % result_tuple
            output += "\end{tabular}"
            output += "\end{table}"

        # output += "\\begin{figure}[h!]"
        # output += "\centering"
        output += "\includegraphics{figures/" + d_name + ".png}"
        # output += "\end{figure}"
        output += "\\newpage"
        output += "\n"

    with open(output_folder + "/main.tex", "w") as fout:
        fout.write("\\documentclass{article}\n\\usepackage{graphicx}\n\\begin{document}")
        fout.write(output)
        fout.write("\\end{document}")

def create_latex_average(output_folder, dataframe, x_axises, use_methods=None):
    if use_methods is None:
        use_methods = METHODS

    plt.rcParams["text.usetex"] = True
    plt.rcParams["text.latex.preamble"] = [r"\usepackage{lmodern}"]

    figure = plt.figure(figsize=(20, 10))
    figure.subplots_adjust(wspace=1, hspace=1)

    fig_num = 231
    # Create graphs
    for x_axis in x_axises:
        col_num = 0
        for d in DATA:
            d_dataframe = dataframe[dataframe["data"] == d]
            d_name = d.split("/")[-1].split(".")[0]
            accs = []

            d_groups = d_dataframe.groupby(x_axis)
            for m in use_methods:
                x = []
                y = []
                for x_val, group in d_groups:
                    x.append(x_val)
                    y.append(np.mean(group[m]))
                    print(fig_num)
                if x_axis == "prefix_size":
                    yx = list(zip(y,x))
                    yx.sort(key=lambda l: int(l[1]))
                    x = [x for y,x in yx]
                    y = [y for y,x in yx]
                    ax = figure.add_subplot(fig_num)
                    ax.set_ylim([-0.05, 0.9])
                    ax.spines["right"].set_visible(False)
                    ax.spines["top"].set_visible(False)
                    ax.plot(x, y, marker=MARKERS[col_num], label=DATA_NAMES[d], color=tableau20[col_num])
                    ax.set_title(X_AXIS[x_axis])
                else:
                    ax = figure.add_subplot(fig_num)
                    ax.set_ylim([-0.05, 0.9])
                    ax.spines["right"].set_visible(False)
                    ax.spines["top"].set_visible(False)
                    ax.plot(x, y, marker=MARKERS[col_num], label=DATA_NAMES[d], color=tableau20[col_num])
                    ax.set_title(X_AXIS[x_axis])
            col_num += 1
        fig_num += 1

    figure.tight_layout()
    ax = figure.add_subplot(fig_num)
    ax.axis("off")
    figure.legend(labels=["Helpdesk","BPIC12W", "BPIC12", "BPIC15\_1", "BPIC15\_2", "BPIC15\_3",
                          "BPIC15\_4", "BPIC15\_5"], loc="lower right", ncol=1, fontsize="xx-large",
                  frameon=False, bbox_to_anchor=(0.38, -0.025), bbox_transform=ax.transAxes, labelspacing=1.3,
                  markerscale=2)

    plt.savefig("Overview.eps", format="eps")
    plt.show()



DATA = ["Camargo_Helpdesk.csv", "Camargo_BPIC12W.csv", "Camargo_BPIC2012.csv", "BPIC15_1_sorted_new.csv",
        "BPIC15_2_sorted_new.csv", "BPIC15_3_sorted_new.csv",
        "BPIC15_4_sorted_new.csv", "BPIC15_5_sorted_new.csv"]

DATA_NAMES["Camargo_Helpdesk.csv"] = "Helpdesk"
DATA_NAMES["Camargo_BPIC12W.csv"] = "BPIC12\_W"
DATA_NAMES["Camargo_BPIC2012.csv"] = "BPIC12"

base_results = read_result_file("test_baseline.txt")
# base_results2 = read_result_file("test_baseline_2.txt")
# base_results3 = read_result_file("test_baseline_3.txt")

# base_results = base_results.append(base_results2)
# base_results = base_results.append(base_results3)

TESTS = {}
TESTS["train_percentage"] = "Train Percentage"
TESTS["split_method"] = "Split Method"
TESTS["split_cases"] = "Split Cases"
TESTS["prefix_size"] = "Prefix Size"
TESTS["end_event"] = "End Event"

create_latex_average("Baseline", base_results, TESTS.keys(), use_methods=["Baseline"])