import sys, os, yaml, glob
import subprocess
import argparse
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import shutil as sh


def main(args):
    workingDir = os.getcwd()
    assemblers = sum(args.assemblers, [])
    if not os.path.exists(args.validation_dir):
        sys.exit("Error: directory {} does not exists".format(args.validation_dir))
    if not os.path.exists(args.assemblies_dir):
        sys.exit("Error: directory {} does not exists".format(args.assemblies_dir))
   
    validation_dir    = os.path.abspath(args.validation_dir) # save valiadation directory
    assemblies_dir    = os.path.abspath(args.assemblies_dir) # save assemblies directory
    outputName        = args.output
    minContigLength   = args.minContigLength
    genomeSize        = args.genomeSize
    processed         = 0 # count how many assembler I am going to process

    if not os.path.exists("LaTeX"):
        os.makedirs("LaTeX")
    os.chdir("LaTeX")
    #produce latex document
    latex_document = _latexHeader(outputName, assemblers)
    assemblyStats = []
    for assembler in assemblers:
        #compute assembly statistics
        assemblySeq = os.path.join(assemblies_dir, assembler, "{}.scf.fasta".format(outputName))
        if os.path.exists(assemblySeq):
            assemblyStats.append(computeAssemblyStats(assembler, assemblySeq, minContigLength, genomeSize))
   
    latex_document = _insert_stat_table(latex_document, assemblyStats)
    #now copy QAstast
    if not os.path.exists("QA_pictures"):
        os.makedirs("QA_pictures")
    for assembler in assemblers:
        if not os.path.exists(os.path.join("QA_pictures", assembler)):
            os.makedirs(os.path.join("QA_pictures", assembler))
    #directory structure created
    for assembler in assemblers:
        if os.path.exists(os.path.join(validation_dir, assembler, "reference", "{}.scf.fasta".format(outputName))):
            latex_document = _new_section(latex_document, assembler)
            Original_CoverageDistribution200 = os.path.join(validation_dir, assembler, "QAstats", "Coverage_distribution_noOutliers.png")
            Original_GC_vs_Coverage          = os.path.join(validation_dir, assembler, "QAstats", "GC_vs_Coverage_noOutliers.png")
            Original_GC_vs_CtgLength         = os.path.join(validation_dir, assembler, "QAstats", "GC_vs_CtgLength.png")
            Original_MedianCov_vs_CtgLength  = os.path.join(validation_dir, assembler, "QAstats", "MedianCov_vs_CtgLength_noOutliers.png")
            Copied_CoverageDistribution200   = os.path.join("QA_pictures", assembler, "Coverage_distribution_noOutliers.png")
            Copied_GC_vs_Coverage            = os.path.join("QA_pictures", assembler, "GC_vs_Coverage_noOutliers.png")
            Copied_GC_vs_CtgLength           = os.path.join("QA_pictures", assembler, "GC_vs_CtgLength.png")
            Copied_MedianCov_vs_CtgLength    = os.path.join("QA_pictures", assembler, "MedianCov_vs_CtgLength_noOutliers.png")
            sh.copy(Original_CoverageDistribution200, Copied_CoverageDistribution200)
            sh.copy(Original_GC_vs_Coverage , Copied_GC_vs_Coverage )
            sh.copy(Original_GC_vs_CtgLength , Copied_GC_vs_CtgLength )
            sh.copy(Original_MedianCov_vs_CtgLength , Copied_MedianCov_vs_CtgLength )
        
            pictures=[[Copied_CoverageDistribution200, "Contig coverage distribtion" ],\
                  [Copied_GC_vs_Coverage, "GC-content versus contig-coverage"],\
                  [Copied_GC_vs_CtgLength, "GC-content versus contig-Length"],\
                  [Copied_MedianCov_vs_CtgLength, "Median-coverage vs Contig-Length"]]
            latex_document = _insert_QA_figure(latex_document,  pictures, "QA pictures")
    # now FRCurve
    latex_document = _new_section(latex_document, "FRCurve")

    if not os.path.exists("FRCurves"):
        os.makedirs("FRCurves")
    os.chdir("FRCurves")
    names = ["_FRC" , "COMPR_MP_FRC" , "COMPR_PE_FRC" , "HIGH_COV_PE_FRC" , "HIGH_NORM_COV_PE_FRC" ,"HIGH_OUTIE_MP_FRC" , "HIGH_OUTIE_PE_FRC" , "HIGH_SINGLE_MP_FRC" , "HIGH_SINGLE_PE_FRC" , "HIGH_SPAN_MP_FRC" , "HIGH_SPAN_PE_FRC" ,"LOW_COV_PE_FRC" , "LOW_NORM_COV_PE_FRC" , "STRECH_MP_FRC" , "STRECH_PE_FRC"]
    for name in names:
        FRCurves = []
        for assembler in assemblers:
            FRCurve_Orig_name = os.path.join(validation_dir, assembler, "FRCurve", "{}{}.txt".format(outputName, name))
            FRCurves.append([assembler, FRCurve_Orig_name])
        FRCname = _plotFRCurve("{}_{}".format(outputName, name),FRCurves)
        FRCurves = []
    #plot last FRCurve
    for assembler in assemblers:
        FRCurves.append([assembler, os.path.join(validation_dir, assembler, "FRCurve", "{}_FRC.txt".format(outputName))])
    FRCname = _plotFRCurve(outputName,FRCurves)
    print FRCname
    os.chdir("..")
    latex_document = _new_figure(latex_document, "FRCurves/{}".format(FRCname), "Feature Response Curve compute on all Features")
    latex_document = _latexFooter(latex_document)
    latex_document = _latexFooter(latex_document)

    with open("{0}.tex".format(outputName),'w') as f:
        f.write(latex_document)

    os.chdir("..")
    # now prepare delivery folder
    if not os.path.exists("{}_delivery_report".format(outputName)):
        os.makedirs("{}_delivery_report".format(outputName))
    os.chdir("{}_delivery_report".format(outputName))

    #now copy QA tables
    for assembler in assemblers:
        if os.path.exists(os.path.join(assemblies_dir, assembler,  "{}.scf.fasta".format(outputName) )):
            if not os.path.exists(assembler):
                os.makedirs(assembler)
            if not os.path.exists(os.path.join(assembler, "assembly")):
                os.makedirs(os.path.join(assembler, "assembly"))
            
            sh.copy(os.path.join(assemblies_dir, assembler, "{}.scf.fasta".format(outputName)), os.path.join(assembler, "assembly",  "{}.scf.fasta".format(outputName)))
            sh.copy(os.path.join(assemblies_dir, assembler, "{}.ctg.fasta".format(outputName)), os.path.join(assembler, "assembly",  "{}.ctg.fasta".format(outputName)))
            if not os.path.exists(os.path.join(assembler, "QA_table")):
                os.makedirs(os.path.join(assembler, "QA_table"))
            sh.copy(os.path.join(validation_dir, assembler, "QAstats", "Contigs_Cov_SeqLen_GC.csv"), os.path.join(assembler, "QA_table", "Contigs_Cov_SeqLen_GC.csv"))
            if not os.path.exists(os.path.join(assembler, "FRCurves")):
                os.makedirs(os.path.join(assembler, "FRCurves"))
            names = ["_FRC" , "COMPR_MP_FRC" , "COMPR_PE_FRC" , "HIGH_COV_PE_FRC" , "HIGH_NORM_COV_PE_FRC" ,"HIGH_OUTIE_MP_FRC" , "HIGH_OUTIE_PE_FRC" , "HIGH_SINGLE_MP_FRC" , "HIGH_SINGLE_PE_FRC" , "HIGH_SPAN_MP_FRC" , "HIGH_SPAN_PE_FRC" ,"LOW_COV_PE_FRC" , "LOW_NORM_COV_PE_FRC" , "STRECH_MP_FRC" , "STRECH_PE_FRC"]
            for name in names:
                FRCurve_Orig_name = os.path.join(validation_dir, assembler, "FRCurve", "{}{}.txt".format(outputName, name))
                FRCurve_Dest_name = os.path.join(assembler, "FRCurves", "{}{}.txt".format(outputName, name))
                sh.copy(FRCurve_Orig_name,FRCurve_Dest_name)
    # now copy FRCurve pictures
    sh.copytree("../LaTeX/FRCurves", "FRCurves")
    os.chdir("..")

    return

def _plotFRCurve(outputName, FRCurves):
    FRCurveName = "{}_FRCurve.png".format(outputName)
    maxXvalues   = []
    for FRCurveData in FRCurves:
        assembler = FRCurveData[0]
        FRCurve   = FRCurveData[1]
        FRC_data    = pd.io.parsers.read_csv(FRCurve, sep=' ', header=None)
        FRC_features= FRC_data[FRC_data.columns[0]].tolist()
        FRC_coverage= FRC_data[FRC_data.columns[1]].tolist()
        plt.plot(FRC_features, FRC_coverage, label="{}".format(assembler))
        maxXvalues.append(max(FRC_features))
    maxXvalues.sort()
    maxXvalues.reverse()
    maxXvalue = maxXvalues[0]
    for i in range(1, len(maxXvalues)-1):
        if maxXvalue > maxXvalues[i]*100:
            maxXvalue = maxXvalues[i] + int(maxXvalues[i]*0.10)

    plt.ylim((-5,140))
    plt.xlim((-1,maxXvalue))
    plt.legend(loc=4, ncol=1, borderaxespad=0.)
    plt.savefig(FRCurveName)
    plt.clf()
    return FRCurveName






def computeAssemblyStats(assembler,sequence, minlenght, genomeSize):
    contigsLength       = []
    Contigs_TotalLength = 0
    Contigs_longLength  = 0
    numContigs      = 0
    numLongContigs  = 0
    with open(sequence, "r") as ref_fd:
        fasta_header     = ref_fd.readline()
        sequence         = ""
        for line in ref_fd:
            line = line
            if line.startswith(">"):
                Contigs_TotalLength += len(sequence)
                contigsLength.append(len(sequence))
                if len(sequence) >= minlenght:
                    numLongContigs      += 1
                    Contigs_longLength  += len(sequence)
                numContigs += 1
                sequence    = ""
            else:
                sequence+=line
        Contigs_TotalLength += len(sequence)
        contigsLength.append(len(sequence))
        if len(sequence) >= minlenght:
            numLongContigs      += 1
            Contigs_longLength  += len(sequence)
        numContigs += 1

    contigsLength.sort()
    contigsLength.reverse()
    
    teoN50 = genomeSize * 0.5
    teoN80 = genomeSize * 0.8
    testSum = 0
    N50 = 0
    N80 = 0
    maxContigLength   = contigsLength[0]
    for con in contigsLength:
        testSum += con
        if teoN50 < testSum:
            if N50 == 0:
                N50 = con
        if teoN80 < testSum:
            N80 = con
            break
    return [assembler,numContigs, numLongContigs, N50, N80, maxContigLength, Contigs_TotalLength, Contigs_longLength]


def _insert_QA_figure(latex_document, pictures, caption):
    tabular  = "\n\\begin{center}\n"
    tabular += "\\begin{tabular}{|c|c|}\n"
    tabular += "\\hline \n"
    tabular +=  " & \\\\\n"
    tabular += "\\includegraphics[width=0.45\\linewidth]{" + pictures[0][0] + "} & \\includegraphics[width=0.45\\linewidth]{" + pictures[1][0] + "}\\\\\n"
    tabular += pictures[0][1] + " & " + pictures[1][1] + "\\\\\\hline\n"
    tabular +=  " & \\\\\n"
    tabular += "\\includegraphics[width=0.45\\linewidth]{" + pictures[2][0] + "} & \\includegraphics[width=0.45\\linewidth]{" + pictures[3][0] + "}\\\\\n"
    tabular += pictures[2][1] + " & " + pictures[3][1] + "\\\\\\hline\n"
    tabular += "\\end{tabular}\n"
    tabular += "\\end{center}\n"
    latex_document += tabular
    #print tabular
    return latex_document
 
 
 
 



def _new_figure(latex_document, picture, caption):
    figure  = "\n"
    figure += "\\begin{center}\n"
#    figure += "\\begin{figure}[H]\n"
#    figure += " \\centering\n"
    figure += " \\includegraphics[width=0.8\\textwidth]{" + picture + "}\n"
    figure += " \\captionof{figure}{" + caption + "}\n"
#
    figure += "\\end{center}\n"
    latex_document += figure
    return latex_document

def _new_section(latex_document, title):
    if "_" in title:
        title = "-".join(title.split("_"))
    latex_document += "\\subsection{"+ title + "}\n\n"
    return latex_document


def _insert_stat_table(latex_document, assemblersStats):
    tabular = "\n\\subsection{Standard assembly statistics}\n"
    tabular += "\\begin{center}\n"
    tabular += "\\begin{table}[h!]\n"
    tabular += "\\begin{tabular}{|c||l|l|l|l|l|l|l|}\n"
    tabular += "\\hline \n"
    tabular += " assembler & \\#scaff & \\#scaff  & N50 & N80 & max scf &  Ass     & Ass. length  \\\\ \n"
    tabular += "           &          &  $>2kbp$  &     &     &  Lgth   & length   &  Ctgs $>2Kbp$ \\\\\\hline \n"
    for assembler in assemblersStats:
        tabular += "{}\\\\\n".format(' & '.join(map(str,assembler)))
    tabular += "\\hline \n"
    tabular += "\n\\end{tabular}\n"
    tabular += "\\caption{For each assembler we report number of contigs/scaffolds, contigs/scaffold $>5Kbp$, N50 (the length of the longest contig/scaffold such that the sum of contigs longer than it is $50\%$ of the estimated genome length), N80 (the length of the longest contig/scaffold such that the sum of contigs longer than it is $80\%$ of the estimated genome length), Max scaffold length, and total assembly length }\n"
    tabular += "\\end{table}\n"
    tabular += "\\end{center}\n"
    latex_document += tabular
    #print tabular
    return latex_document


def _latexFooter(latex_document):
    latex_document += "\n\\subsection{References}\n"
    latex_document+= "\\begin{itemize} \n"
    latex_document+= "\\item ABySS http://www.bcgsc.ca/platform/bioinfo/software/abyss \n"
    latex_document+= "\\item CABOG http://sourceforge.net/apps/mediawiki/wgs-assembler/ \n"
    latex_document+= "\\item SOAPdenovo http://soap.genomics.org.cn/soapdenovo.html\n"
    latex_document+= "\\item SPADES http://bioinf.spbau.ru/spades/\n"
    latex_document+= "\\item BWA http://bio-bwa.sourceforge.net/ \n"
    latex_document+= "\\item FRCurve: https://github.com/vezzi/FRC\\_align\n"
    latex_document+= "\\item QAtootls: https://github.com/vezzi/qaTools\n"
    latex_document+= "\\item NGI-automated de novo assembly pipeline (Highly Unstable): https://github.com/vezzi/de\\_novo\\_scilife\n"
    latex_document+= "\\end{itemize} \n"
    latex_document += "\\end{document}\n"
    return latex_document

def _latexHeader(sampleName, assemblers):
    LaTeX_header  = "\\documentclass{article}\n"
    LaTeX_header += "\\usepackage{graphicx}\n"
    LaTeX_header += "\\usepackage{caption}\n"
    LaTeX_header += "\\begin{document}\n"
    sampleName = sampleName.replace("_", "-")
    
    LaTeX_header += "\\title{{Evaluation Report for Sample {0} }}\n".format(sampleName)
    LaTeX_header += "\\author{Francesco Vezzi}\n"
    LaTeX_header += "\\maketitle\n"
    LaTeX_header += "\\begin{abstract}\n"
    
    
    
    
    LaTeX_header += "De novo assembly and de novo assembly evaluation are two difficult computational exercises.\
    Currently there is no tool ($i.e.$, de novo assembler) that is guarantee to always outperform the others. Many recent publications ($e.g.$, GAGE, GAGE-B, Assemblathon 1 and 2)\
    showed how the same assembler can have totally different performances on slightly different datasets.\
    For these reasons, at NGI-Stockholm we do not limit our de novo analysis to a single tool, instead we employ several assemblers and we provide our costumers with a semi-automated evaluation in order to allow them to choose the best assembler based on their specific needs\n\
The assembly or assemblies judged to be the best can be directly employed to answer important biological questions, or they can be used as a backbone for a specific user defined assembly pipeline (i.e., use of extra data, use of non supported tools, variation of parameters)\n"
    LaTeX_header += "\\end{abstract}\n"
    LaTeX_header += "\\section{Introduction}\n"
    LaTeX_header += "\
    We assembled sample {0} with {1} different tool(s):".format(sampleName, len(assemblers))
    LaTeX_header += "\\begin{itemize} \n"
    for assembler in assemblers:
        LaTeX_header += "\\item {}\n".format(assembler)
    LaTeX_header += "\\end{itemize}\n"
    LaTeX_header += "For each assembler the latest version of the tool has been employed, using either default parameters \
    or parameters suggested by the assembler's developer. To know exactly which parameters have\
    been employed contact NGI support. \n"
    LaTeX_header += "For each assembly the following information is provided:\n \
    \\begin{itemize} \n\
    \\item Table with Standard Assembly Statistics: number of contigs/scaffolds, number of contigs/scaffold $>2Kbp$, N50 (the length of the longest contig/scaffold such that the sum of contigs/scaffolds longer than it is $50\%$ of the estimated genome length), N80 (the length of the longest contig/scaffold such that the sum of contigs/scaffolds longer than it is $80\%$ of the estimated genome length), length of the longest contig/scaffold, total assembly length, and sum of contigs/scaffolds $>2Kbp$\n\
    \\item For each individual assembler four plots are automatically generated:  \n\
    \\begin{itemize} \n\
    \\item Contig-coverage distribution: this plot shows contigs coverage distribution ($i.e.$, how many contigs have a certain coverage)\n\
    \\item GC-content versus Contig-Coverage: this plot shows for each contig/scaffold its GCs content on the $x$-axis and its coverage on the $y$-axis\n\
	\\item GC-content vs Contig-Length: this plot shows for each contig/scaffold its GCs content on the $x$-axis and its length on the $y$-axis\n\
    \\item Contig Coverage vs Contig Length: this plot shows for each contig/scaffold its coverage on the $x$-axis and its length on the $y$-axis\n\
    \\end{itemize} \n\
    \\item FRCurve plot: Inspired by the standard receiver operating characteristic (ROC) curve, the Feature-Response curve (FRCurve) characterizes the sensitivity (coverage) of the sequence assembler output (contigs) as a function of its discrimination threshold (number of features/errors). Generally speaking, FRCurve can be used to rank different assemblies: the sharpest the curve is the better the assembly is (i.e., given a certain feature threshold $w$, we prefer the assembler that reconstructs an higher portion of the genome with $w$ features). FRCurve is one of the few tools able to evaluate de novo assemblies in absence of a reference sequence. Results are not always straightforward to interpret and must be always used in conjunction with other sources (e.g., quality plots and standard assembly statistics)\n\
\\end{itemize}\n \
    Only contigs longer than 2Kbp are used in this validation. This is done in roder to avoid problems with outliers points and to partially circumvent the fact that some assemblers output small contigs while others perform automatic trimming.\
    Statiscs like N50, N80, etc. are computed on the expected genome length in order to normalise the numbers and allow a fair comparison among various tools.\n\
    Coverage information and FRCurve features are obtaind by aligning the Quality Filtered reads against the assembled sequences ($i.e.$, only contigs/scaffolds longer than $2Kbp$ are employed) using bwa mem algorithm\n\n\
    This report is delivered both via e-mail and via Uppmax. In particular on Uppmax the following files are available for further result inspection:\n\
    \\begin{itemize} \n\
    \\item the report itself\n\
    \\item for each assembly a folder named as the assemler itself. Each of this folders contains the following folders:\n\
    \\begin{itemize} \n\
    \\item assembly: multi-fasta file of the assembled contigs and scaffolds\n\
    \\item QA table: contains the QA table employed to draw quality plots. A close look to this table is always recommended.\n\
    \\item FRCurves: all the FRCurves files (the one plotted here is the one that collects at once all the features, however one might be interested in looking one feature at the time)\n\
    \\end{itemize} \n\
    \\end{itemize} \n\
    Please, note that the pipeline generates all the plots automatically. The pipeline tries to eliminate outliers in order to visualize data in a meaningful and useful way (e.g., a single contig with extremely high coverage can jeopardize the visualization of all the other contigs). However, there might be situations where interesting points are discarded. We recommend to always inspect the original tables that are delivered on Uppmax altogether with this report.\n\
    \\newpage"
    return LaTeX_header





if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--validation-dir', type=str, required=True, help="Directory where validation is stored (one assembler per folder)")
    parser.add_argument('--assemblies-dir', type=str, required=True, help="Directory where assemblies are stored (one assembler per folder)")
    parser.add_argument('--assemblers',     type=str, required=True, help="List of assemblers to be evalueted", action='append', nargs='+')
    parser.add_argument('--sample-config',  type=str, help="sample config, it is needed to extract several informations")
    parser.add_argument('--global-config',  type=str, help="global configuration file")
    parser.add_argument('--output',         type=str, required=True, help="output header used to store all results (i.e., output.scf.fasta)")
    parser.add_argument('--genomeSize',     type=int, required=True, help="expected genome size (same as specified in the validation phase)")
    parser.add_argument('--minContigLength',type=int, default=2000, help="minimum contig length (usually the same used to validate assembly). Default value set to 2000")
    args = parser.parse_args()
    
    main(args)



#python ~/DE_NOVO_PIPELINE/de_novo_scilife/utils/run_assembly_evaluation.py --assembues-dir /proj/b2013064/nobackup/vezzi/C.Wheat/03_ASSEMBLY/ --assemblers allpaths abyss soapdenovo