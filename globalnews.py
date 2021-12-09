""" globalnews.py
Global NEWS 2 model, GNE implementation.
This module is the master model execution controller; it imports
gncfg, gncore, and the actual "model" code (dissolved.py, etc).

AVAILABILITY, USE RESTRICTIONS, AND CONTACT INFORMATION
-------------------------------------------------------
The Global NEWS 2 model ("NEWS 2") and the Global NEWS modeling Environment (GNE)
were developed by the Global NEWS group and are available at our web site:
http://www.marine.rutgers.edu/globalnews/
We encourage its use for research and educational (non-commercial) purposes, but 
we request that active users contact us to inform about how it is being applied. 
Such feedback and reporting will improve our continued development of the model code. 
Global NEWS is a work group of UNESCO's Intergovernmental Oceanographic Commission (IOC).

Use of NEWS 2 should be ackwnowledged by citing Mayorga et al (in review); 
Beusen et al. (2009) and Billen and Garnier (2007) should also be cited if 
the DSi model and the ICEP index, respectively, are also used.

For questions and additional information, please contact:
Emilio Mayorga, Ph.D.          mayorga@apl.washington.edu
Applied Physics Laboratory, University of Washington
Seattle, WA  USA
---------------------------------------
RECENT MODIFICATION HISTORY

1/18/2010: Improved documentation and some run-time messages.
10/16-24/2008: Added functionality to allow an optional 'All-Forms' model
 after the Global NEWS nutrient form models are completed. This new model
 or calculation can use results from any nutrient form output. It is coded
 in the python code file allformmodel.py. It's enabled through the new
 optional argument -a (or --afm).
1/28/2008: Added actual usage text to usage(); cleaned up run-time messages a bit 
 and added date-time statements at every major code block in main() and runmodel().
9/17-18/2007
"""


import sys
import os.path
import getopt
from operator import itemgetter
import time

# Import Global NEWS Environment ("gne") modules
# Generic gne code files ideally should be placed in the "gnecode"
# subfolder, but they may also be placed at the same base folder
__gne = os.path.join('.', 'gnecode')
if os.path.exists(__gne): sys.path.insert(0, __gne)
from gnecode.gncfg import *
import gnecode.gncore as gncore
import gnecode.gngis2tbls as gngis2tbls

__version__ = '$Revision: 2010-01-18$'


def localtimestrf(frmtopt="datetime"):
    ''' Return the local date-time as a formatted string. 
        frmtopt="datetime" (default)   Return a complete date-time string.
        frmtopt="timeonly"             Return Hour:Minute:Seconds only.
    '''
    if frmtopt == "datetime":
        return time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    elif frmtopt == "timeonly":
        return "Time: " + time.strftime("%H:%M:%S", time.localtime())

def usage():
    ''' Print out string describing model usage and optional arguments.
    '''
    print("\nRun-time arguments/options:")
    print("-h OR --help        Show this help text.")
    print("-v                  Run in verbose mode (print out all internal messages).")
    print("<none>              Run Global NEWS model using vars.cfg config file.")
    print("-a OR --afm         Run Global NEWS 'All-Forms' model *after* all individual")
    print("                    nutrient forms have been calculated (with allformmodel.py).")
    print("-g OR --gis         Run GIS pre-processor using gis2tbls.cfg config file.")
    print("-g OR --gis         Run GIS pre-processor using gis2tbls.cfg config file.")
    print("-p OR --postproc    Run post-processing: create new loads variables")
    print("                    for selected inputs and outputs, all basins.")


def main():
    global FLAGS
    
    print("\n***** Global NEWS modeling Environment (GNE) *****")
    print("            " + __version__)
    print("            " + localtimestrf())
    print("      ==========================================")

    # Passing arguments at command-line
    # opts, args = getopt.getopt(sys.argv[1:], "ho:v", ["help", "output="])

    try:
        # hmm, not sure what's fed to args if opts already gets the arg value
        opts, args = getopt.getopt(sys.argv[1:], "agphv", ["afm", "gis", "postproc", "help"])
        # extract list of just the "options" (arguments), without arg. values
        opt = list(map(itemgetter(0), opts))
    except getopt.GetoptError:
        # print help information, then exit:
        usage()
        sys.exit(2)
        
    if "-h" in opt or "--help" in opt:
        usage()
        sys.exit()

    FLAGS['verbose'] = False
    if "-v" in opt:
        FLAGS['verbose'] = True
    
    if "-g" in opt or "--gis" in opt:
        rungis2tbls()
    elif "-p" in opt or "--postproc" in opt:
        runpostproc()
    else:
        if "-a" in opt or "--afm" in opt:
            FLAGS['AllFormModel'] = True
        else:
            FLAGS['AllFormModel'] = False
        runmodel()
    #elif "-s" in opt or "--smry" in opt:
    #    runsummary() # does not exist yet!

    print("      ==========================================")
    print("***** GNE Run completed *****")
    print("            %s\n" % localtimestrf())


def runmodel():
    ''' Execute a Global NEWS run using pre-processed basin inputs
    as configured in vars.cfg.
    '''
    global IN, OUT, FLAGS

    print("*** Running Global NEWS Model\n")

    gncore.cfg_simple_sections("MODEL")
    print("*** Done reading general model run configurations (cfg_simple_sections()) ***")
    print("        %s" % localtimestrf("timeonly"))

    gncore.PopulateCfgVars(fname_cfg_var, "MODEL")
    print("*** Done reading variable configurations (PopulateCfgVars()) ***")
    print("        %s" % localtimestrf("timeonly"))

    gncore.load_var_arrays(INDOC_TBL, INDOC, IN, OUT)
    print("*** Done loading input data into memory (load_var_arrays()) ***")
    print("        %s" % localtimestrf("timeonly"))

    print("\n*** Ready to run models ... ***")
    # run only nutrient-form (parameter) subsets specified in vars.cfg, as appropriate
    params_dissolved = [p for p in RUN['p'] if p in PGRP['dissolved']]
    params_particulate = [p for p in RUN['p'] if p in PGRP['particulate']]
    print("    Nutrient forms (parameters) requested:")
    print("    " + ",".join(params_dissolved) + "  " + ",".join(params_particulate))
    
    if len(params_dissolved):
        import dissolved
        dissolved.model(params_dissolved)
        print("*** Done with dissolved sub-models ***")
    else:
        print("*** No dissolved forms (parameters) requested")
    print("        %s" % localtimestrf("timeonly"))

    if len(params_particulate):
        import particulate
        particulate.model(params_particulate)
        print("*** Done with particulate sub-models ***")
    else:
        print("*** No particulate forms (parameters) requested")
    print("        %s" % localtimestrf("timeonly"))

    if FLAGS['AllFormModel']:
        import allformmodel
        allformmodel.model()
        print("*** Done with 'All-Form' model ***")
    else:
        print("*** No 'All-Form' model requested")
    print("        %s" % localtimestrf("timeonly"))


    gncore.write_var_arrays(OUTDOC_TBL, OUTDOC, OUT)
    print("*** Done writing output to files (write_var_arrays()) ***")


def rungis2tbls():
    global IN, OUT

    print("\n***Running Global NEWS Pre-Processor (GIS > Tables)\n")
    # print the time, too?

    gncore.cfg_simple_sections("GIS2TBLS")
    print("*** Done with cfg_simple_sections ***\n")

    gncore.PopulateCfgVars(fname_cfg_gis, "GIS2TBLS")
    print("*** Done with PopulateCfgVars ***\n")

    gngis2tbls.LoadBasinIDArea(INDOC_TBL, IN, OUT)
    print("*** Done with LoadBasinIDArea ***\n")
    
    # loop through gis input grids for all items in INDOC
    #print "INDOC keys:", INDOC.keys(), "  INDOC_TBL keys:", INDOC_TBL.keys()
    gngis2tbls.CalcBasinStats(INDOC_TBL, INDOC)
    print("*** Done with CalcBasinStats ***\n")
    gngis2tbls.BasinStatsToOUTvarArrays(OUTDOC_TBL, OUTDOC, OUT, IN)
    print("*** Done with BasinStatsToOUTvarArrays ***\n")
    
    # INSERT HERE A NEW FUNCTION (SEPARATE FILE) TO FREELY DEFINE GENERATED
    # OUT VARS THAT ARE NOT ZONALSTATS. WILL NEED TO MODIFY
    # BasinStatsToOUTvarArrays TO NOT TRIP OVER THOSE NEW OUT VARS
    # Maybe this new function should be called *only* if there are any
    # "qualifying" OUT vars?? Do that test here, in the new function, or
    # in BasinStatsToOUTvarArrays() and have it return a value?
    excldvarset = set(list(INDOC.keys()) + ['BasinID', 'BasinArea'])
    genoutset   = set(OUTDOC.keys()).difference(excldvarset)
    if len(genoutset):
        import gis2tbls
        gis2tbls.newoutvars()
        print("*** Done with gis2tbls ***\n")
    else:
        print("*** No gis2tbls variables requested\n")
    
    gncore.write_var_arrays(OUTDOC_TBL, OUTDOC, OUT)
    print("*** Done with write_var_arrays ***\n")


def runpostproc():
    global IN, OUT

    print("\n***Running Post-processing \n")
    # print the time, too?

    gncore.cfg_simple_sections("MODEL")
    print("*** Done with cfg_simple_sections ***\n")

    gncore.PopulateCfgVars(fname_cfg_var, "MODEL")
    print("*** Done with PopulateCfgVars ***\n")

    gncore.load_var_arrays(INDOC_TBL, INDOC, IN, OUT)
    print("*** Done with load_var_arrays ***\n")

    # run only parameter subsets specified in vars.cfg (? is this applicable?)
    print("  Parameters requested: ", RUN['p'])

    if len(RUN['p']):
        import postprocess
        postprocess.processvars(RUN['p'])
        print("*** Done with postprocess ***\n")
    else:
        print("*** No postprocess parameters requested\n")

    gncore.write_var_arrays(OUTDOC_TBL, OUTDOC, OUT)
    print("*** Done with write_var_arrays ***\n")
    
    # NOW WRITE OUT A SEPARATE SUMMARY FILE (*_smry.csv) WITH
    # GLOBAL AND MAYBE REGIONAL (CONTINENTAL, ETC) TOTALS???



if __name__ == '__main__':
    main()
