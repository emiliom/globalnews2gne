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
import numpy as ny
from numpy import log, exp, log10

# Import Global NEWS Environment ("gne") modules
# Generic gne code files ideally should be placed in the "gnecode"
# subfolder, but they may also be placed at the same base folder
__gne = os.path.join('.', 'gnecode')
if os.path.exists(__gne): sys.path.insert(0, __gne)
from gnecode.gncfg import *
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

    cfg_simple_sections("MODEL")
    print("*** Done reading general model run configurations (cfg_simple_sections()) ***")
    print("        %s" % localtimestrf("timeonly"))

    PopulateCfgVars(fname_cfg_var, "MODEL")
    print("*** Done reading variable configurations (PopulateCfgVars()) ***")
    print("        %s" % localtimestrf("timeonly"))

    load_var_arrays(INDOC_TBL, INDOC, IN, OUT)
    print("*** Done loading input data into memory (load_var_arrays()) ***")
    print("        %s" % localtimestrf("timeonly"))

    print("\n*** Ready to run models ... ***")
    # run only nutrient-form (parameter) subsets specified in vars.cfg, as appropriate
    params_dissolved = [p for p in RUN['p'] if p in PGRP['dissolved']]
    params_particulate = [p for p in RUN['p'] if p in PGRP['particulate']]
    print("    Nutrient forms (parameters) requested:")
    print("    " + ",".join(params_dissolved) + "  " + ",".join(params_particulate))
    
    if len(params_dissolved):        
        model_dissolved(params_dissolved)
        print("*** Done with dissolved sub-models ***")
    else:
        print("*** No dissolved forms (parameters) requested")
    print("        %s" % localtimestrf("timeonly"))

    if len(params_particulate):        
        model_particulate(params_particulate)
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


    write_var_arrays(OUTDOC_TBL, OUTDOC, OUT)
    print("*** Done writing output to files (write_var_arrays()) ***")


def rungis2tbls():
    global IN, OUT

    print("\n***Running Global NEWS Pre-Processor (GIS > Tables)\n")
    # print the time, too?

    cfg_simple_sections("GIS2TBLS")
    print("*** Done with cfg_simple_sections ***\n")

    PopulateCfgVars(fname_cfg_gis, "GIS2TBLS")
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
    
    write_var_arrays(OUTDOC_TBL, OUTDOC, OUT)
    print("*** Done with write_var_arrays ***\n")


def runpostproc():
    global IN, OUT

    print("\n***Running Post-processing \n")
    # print the time, too?

    cfg_simple_sections("MODEL")
    print("*** Done with cfg_simple_sections ***\n")

    PopulateCfgVars(fname_cfg_var, "MODEL")
    print("*** Done with PopulateCfgVars ***\n")

    load_var_arrays(INDOC_TBL, INDOC, IN, OUT)
    print("*** Done with load_var_arrays ***\n")

    # run only parameter subsets specified in vars.cfg (? is this applicable?)
    print("  Parameters requested: ", RUN['p'])

    if len(RUN['p']):
        import postprocess
        postprocess.processvars(RUN['p'])
        print("*** Done with postprocess ***\n")
    else:
        print("*** No postprocess parameters requested\n")

    write_var_arrays(OUTDOC_TBL, OUTDOC, OUT)
    print("*** Done with write_var_arrays ***\n")
    
    # NOW WRITE OUT A SEPARATE SUMMARY FILE (*_smry.csv) WITH
    # GLOBAL AND MAYBE REGIONAL (CONTINENTAL, ETC) TOTALS???

def ParseStrBlock(delims, str_in, strblock_d):
    if delims[0] in str_in:
        bl0, blf = (str_in.index(delims[0]), str_in.index(delims[1]))
        # 0 = enclosed block, b = beginning block, f = final block
        # strblock_d['b']<strblock_d['0']>strblock_d['f']
        # where < and > represent the chosen delimeters, "delims"
        strblock_d['0'] = str_in[:bl0]
        strblock_d['b'] = str_in[bl0+1:blf]
        strblock_d['f'] = str_in[blf+1:]

        return True
    else:
        return False


def read_cfgfile(fname_cfg, sect_prefix):
    """ Read and parse configuration files
    Return dictionary of parsed section/options
    For section names [prefix.suffix]: cfg_dict[sect_suffix][option] = optionvalue
    For section names [prefix]: cfg_dict[option] = optionvalue
    """
    import os, os.path
    import configparser

    cfg = configparser.SafeConfigParser()
    # Prevent default behavior of returning options in all-lowercase
    cfg.optionxform = str

    fpath_cfg = os.path.join(fpath_dev, fname_cfg)
    cfg.read(fpath_cfg)

    # is any error checking needed??
    cfg_dict = {}
    for section in cfg.sections():
        if "." in section:
            spre,ssuf = section.split(".")
            if spre == sect_prefix:
                cfg_dict[ssuf] = {}
                for opt,val in cfg.items(section):
                    cfg_dict[ssuf][opt] = val
                    if FLAGS['verbose']: print(" %s[%s][%s] = %s" %(sect_prefix, ssuf, opt, cfg_dict[ssuf][opt]))
        elif section == sect_prefix:
            for opt,val in cfg.items(section):
                cfg_dict[opt] = val
                if FLAGS['verbose']: print(" %s[%s] = %s" %(section, opt, cfg_dict[opt]))

    
    return cfg_dict


def parse_cfg_ccal(ccal_cfg_d, ccal_d):
    """ Populate global CCAL dictionary
    """

    for k1 in list(ccal_cfg_d.keys()):
        ccal_d[k1] = {}
        for k2,val in list(ccal_cfg_d[k1].items()):
            ccal_d[k1][k2] = float(val)


def parse_cfg_modelrun(mrun_cfg_d, run_d):
    """ Populate global RUN dictionary
    """

    # Parse variable p
    vallst = mrun_cfg_d['p'].split(',')
    # note: run_d['p'] must be stored as list, not single value
    # perform variable test & expansion based on PGRP
    if len(vallst) == 1:
        # entry could be a single parameter or a parameter group
        if vallst[0] in PGRP['all']:
            run_d['p'] = vallst
        elif vallst[0] in list(PGRP.keys()):
            run_d['p'] = list(PGRP[vallst[0]]) # convert tuple to list
        else:
            if FLAGS['verbose']: print("Generic var name: parameter sepecifier %s not valid" % (vallst[0]))
    else:
        run_d['p'] = vallst

    # Parse variable param_ord
    run_d['param_ord'] = []
    vallst = mrun_cfg_d['param_ord'].split(',')
    for idx, v in enumerate(vallst):
        if PGRP['all'][idx] in run_d['p']:
            # assign order index, converting from base 1 to base 0
            run_d['param_ord'].append(int(v) - 1)

    
    if FLAGS['verbose']: print(run_d)


def parse_cfg_basrea(basarea_cfg_d, basarea_d):
    """ Populate global BASAREA dictionary
    """

    # Parse variable BasinAreas, populate global dictionary
    if basarea_cfg_d['BasinAreas'] == "NO":
        basarea_d['BasinAreas'] = \
            {'FLAG':False, 'outtable':None, 'varname':None}
    else:
        vallst = basarea_cfg_d['BasinAreas'].split('|')
        basarea_d['BasinAreas'] = \
            {'FLAG':True, 'outtable':vallst[0], 'varname':vallst[1]}

    if FLAGS['verbose']: print("BASAREA:  ", basarea_cfg_d['BasinAreas'])


def parse_cfg_tbls(tbls, strsubs, doctbl_d, doctype):
    """ parse tables
    This generic function can populate either INDOC_TBL or OUTDOC_TBL
    INDOC_TBL and OUTDOC_TBL must be already initialized/declared (in gncfg.py)
    doctbl_d: INDOC_TBL or OUTDOC_TBL
    doctype: "IN" or "OUT"
    """
    import os.path
    
    vlist_len = {"INGIS":2, "IN":2, "OUT":2}

    # what's the difference between .items() and .iteritems()?
    for tblname,val in list(tbls.items()):
        vlist = val.split("|")
    
        # later, the basis for doctype == "OUT" might be made optional?
        if len(vlist) != vlist_len[doctype]:
            if FLAGS['verbose']: print("%s: Tables must have exactly %d arguments.\n" %(tblname, vlist_len[doctype]))
            # Now exit.
    
        # add empty tblname key to dictionary
        doctbl_d[tblname] = {}

        # Add filepath item
        # one optional string substitution is allowed for now; parse it if present
        # allowing multiple string substitutions later will be very useful
        # first test for the existence of strblock in strsubs?
        strblock = {}
        if ParseStrBlock("()", vlist[0], strblock):
            doctbl_d[tblname]['filepath'] = strsubs[strblock['b']] + strblock['f']
            if FLAGS['verbose']: print(tblname,doctbl_d[tblname]['filepath'])
        else:
            doctbl_d[tblname]['filepath'] = vlist[0]
        
        if doctype == "IN":
            # test to see if the file exists
            if not os.path.exists(doctbl_d[tblname]['filepath']):
                if FLAGS['verbose']: print("Table does not exist: %s\n" %(doctbl_d[tblname]['filepath']))
                # Now exit.

            # Add basis item (check for valid values)
            basis_valid = ('basin', 'nation', 'table', 'grid')
            if vlist[1] in basis_valid:
                doctbl_d[tblname]['basis'] = vlist[1]
            else:
                if FLAGS['verbose']: print("Table %s: basis '%s' is not recognized; must be (%s).\n" \
                      %(tblname, vlist[1], ','.join(basis_valid)))
                # Now exit.
        # OUT tables can only have a 'basin' basis; for now, just ignore entry in cfg
        elif doctype == "OUT":
            doctbl_d[tblname]['basis'] = 'basin'

        # initialize list of variables to be used
        # and their left-right field output order (for OUT)
        doctbl_d[tblname]['varlst'] = []
        doctbl_d[tblname]['fieldorder'] = []


def parse_cfg_vars(vars, doctbl_d, doc_d, doctype):
    """ Parse variables, mapping them to columns (fields) in csv tables.
    """

    vlist_len = {"IN":3, "OUT":4, "INGIS":3}
    dattype   = {'IN':'tbl', 'OUT':'tbl', 'INGIS':'gis'}

    for varname,val in list(vars.items()):
        vlist = val.split("|")

        if len(vlist) != vlist_len[doctype]:
            # for doctype "OUT", flgwrite 'Y' is assumed if it's ommitted
            if doctype == "OUT" and len(vlist) == vlist_len[doctype] - 1:
                vlist.append('Y')
            else:
                if FLAGS['verbose']: print("%s: Variable must have exactly %d arguments.\n" \
                                 %(varname, vlist_len[doctype]))
            # Now exit.

        strblock = {}
        if doctype == "OUT":
            # if doctype == "OUT", try to parse generic variables
            if ParseStrBlock("<>", varname, strblock):
                vargen = strblock['b'].split('|')
                # "p": variable name used for "parameter" in .cfg file
                if vargen[0] == 'p':
                    varname0, varnamef = (strblock['0'], strblock['f'])
                    params_in = vargen[1].split(',')
                    # perform variable test & expansion based on PGRP
                    if len(params_in) == 1:
                        # entry could be a single paramer or a parameter group
                        # ignore case mismatch?? (eg, DOC vs doc)
                        if params_in[0] in PGRP['all']:
                            # it's already a simple parameter name, so use as-is
                            params = params_in
                        elif params_in[0] in list(PGRP.keys()):
                            # extract parameters from param group, convert to list
                            params = list(PGRP[params_in[0]])
                        else:
                            print("Generic var name: parameter sepecifier %s not valid" % (params_in[0]))
                    else:
                        # should do error check, to ensure parameters are valid
                        params = params_in
                else:
                    print("Error with generic var name!")
                if FLAGS['verbose']: print(strblock['b'],params, "\n")

                # Parse and expand fieldname, if it, too, is generic
                # A generic varname doesn't require a corresponding generic fieldname
                ParseStrBlock("<>", vlist[1], strblock)
                if strblock['b'] == 'p':
                    IsGenericFldName = True
                    fldname0, fldnamef = (strblock['0'], strblock['f'])
                else:
                    IsGenericFldName = False
                    if FLAGS['verbose']:
                      print(">WARNING: For generic var name, field name is not generic")

                # limit params list by actual model run parameters in RUN['p']
                params = [p for p in PGRP['all'] if p in params and p in RUN['p']]

                # add expanded variables to doc_d based on the vargen block
                for p in params:
                    # if doctype == "OUT", more than one srctable is allowed.
                    varname_p = varname0 + p + varnamef
                    if IsGenericFldName:
                        fldname_p = fldname0 + p + fldnamef
                    else:
                        fldname_p = vlist[1]
                    doctbld_docd_assign(dattype[doctype], doctbl_d, doc_d, \
                                        varname_p, vlist[0], fldname_p, \
                                        vlist[2], vlist[3], varname, p)

            else:
                doctbld_docd_assign(dattype[doctype], doctbl_d, doc_d, varname, \
                                    vlist[0], vlist[1], vlist[2], vlist[3])

        else:
            # if doctype == "IN", parse specific vars only; just one srctable is allowed.
            doctbld_docd_assign(dattype[doctype], doctbl_d, doc_d, varname, \
                                vlist[0], vlist[1], vlist[2])

    # if doctype == "OUT", create dummy, 0-value, varlst-length list for fieldorder key
    if doctype == "OUT":
        for tblname in doctbl_d:
            varlst0 = [0 for i in range(len(doctbl_d[tblname]['varlst']))]
            doctbl_d[tblname]['fieldorder'] = varlst0

    if FLAGS['verbose']:
        for tblname in sorted(doctbl_d):
            print(tblname, doctbl_d[tblname]['varlst'])


def doctbld_docd_assign(dattype, doctbld, docd, varname, srctable, fldname, \
                        fldtype, flgwrite='N', genvar=None, genvarparam=None):
    docd[varname] = {}
    docd[varname]['genvarname'] = genvar
    docd[varname]['genvar_p']   = genvarparam
    # split works fine even if there's just one srctable
    docd[varname]['srctable']   = srctable.split(',')
    docd[varname]['fieldname']  = fldname
    docd[varname]['flgwrite']   = {'Y':True, 'N':False}[flgwrite]

    if dattype == "tbl":
        if fldtype in ('double', 'int'):
            docd[varname]['fieldtype'] = fldtype
        else:
            print("Variable %s: fieldtype '%s' is not recognized; must be 'double' or 'int'.\n" %(varname, fldtype))
            # Now exit.
    elif dattype == "gis": # here, fldtype is really the cell fraction grid, if any
        if fldtype == 'all' or fldtype.startswith('clfr'):
            docd[varname]['fieldtype'] = fldtype
        else:
            print("Variable %s: fieldtype '%s' is not recognized; must be 'all' or 'clfr*'.\n" %(varname, fldtype))
            # Now exit.

    # add variable to corresponding variable list for table(s)
    for tblname in docd[varname]['srctable']: 
        doctbld[tblname]['varlst'].append(varname)

    if FLAGS['verbose']: print("docd assignments: ",varname,docd[varname]['genvarname'], \
        docd[varname]['srctable'],docd[varname]['fieldname'],docd[varname]['fieldtype'])


def load_var_arrays(doctbl_d, doc_d, data_d, out_data_d):
    """ Data array will be populated into data_d[varname]
    Open each table, load each requested fields and map them to variables.
    Variables will be numpy arrays.
    """
    import csv
    
    # =====================================================
    # LOAD AND HANDLE BasinID VARIABLE
    # Basin sub-setting functionality is included.
    id_var = 'BasinID'
    id_fldname, id_tblname = doc_d[id_var]['fieldname'], doc_d[id_var]['srctable'][0]
    
    # read csv table and load BasinID variable        
    fp = open(doctbl_d[id_tblname]['filepath'], "r")
    basinid_lst = [int(row[id_fldname]) for row in csv.DictReader(fp)]    
    fp.close()

    # Convert to int32 numpy array and load into IN
    data_d[id_var] = ny.array(basinid_lst, dtype="int32")

    # Create set out of global BasinID's array
    # For use in basin sub-setting as input variables/tables are read in (below)
    setBasinID = set(data_d[id_var])

    # Copy to OUT[id_var] numpy array
    out_data_d[id_var] = data_d[id_var]
    
    if FLAGS['verbose']: print("  Number of basins to be processed: %d" % data_d[id_var].size)

    # =====================================================
    # LOAD ALL OTHER INPUT VARIABLES, STEPPING THROUGH INDIVIDUAL INPUT TABLES
    for tbl in list(doctbl_d.keys()):
        if len(doctbl_d[tbl]['varlst']) > 0:
            # Initialize data_d dict with all its keys (variables), as numpy arrays
            # (maybe this data_d initialization should be done in parse_cfg_vars()?
            for var in doctbl_d[tbl]['varlst']:
                if var != id_var: 
                    if doc_d[var]['fieldtype'] == "double":
                        data_d[var] = ny.array([], dtype="float64")
                        #data_d[var] = ny.array([], dtype="float32")
                    elif doc_d[var]['fieldtype'] == "int":
                        data_d[var] = ny.array([], dtype="int32")

            # create temporary dict {fieldname:varname} for current table (tbl),
            # based on doctbl_d[tbl]['varlst'] and doc_d[varname]['fieldname']
            # Then map fieldname to varname, and use in the block below
            tbl_fld_var = {}
            for var in doctbl_d[tbl]['varlst']:
                if var != id_var: 
                    tbl_fld_var[doc_d[var]['fieldname']] = var
            if FLAGS['verbose']: print("tbl_fld_var: ", tbl_fld_var)

            # Read the first row (field names)
            fp = open(doctbl_d[tbl]['filepath'], "r")
            fld_names_reader = csv.reader(fp)
            fld_names = next(fld_names_reader)
            fp.close()

            # Set basinid_fld using the header (field names) reader list
            # id_fldnames_lst is a list of expected basin id field names
            id_fldnames_lst = ['basinid', 'BASINID']
            if id_fldnames_lst[0] in fld_names:
                basinid_fld = id_fldnames_lst[0]
            elif id_fldnames_lst[1] in fld_names:
                basinid_fld = id_fldnames_lst[1]
            else:
                print("  !!! Input table does not have a valid basin ID column name !!!\n")

            # read csv table and load requested fields
            fp = open(doctbl_d[tbl]['filepath'], "r")
            csvreader = csv.DictReader(fp)
            # SHOULD THERE BE A TEST TO ENSURE THAT ALL REQUESTED FIELDS
            # ARE PRESENT IN THE FILE? OTHERWISE, ABORT WITH ERROR MESSAGE
            for row in csvreader:
                for fld,v in list(row.items()):
                    if int(row[basinid_fld]) in setBasinID and fld in list(tbl_fld_var.keys()):
                        # load requested fields into the data_d dict by
                        # concatenating each row value to the numpy arrays
                        # This test is done for every single row! It may be more
                        # efficient to extract indices for the requested fields, then
                        # just use those indices directly into the row dictionary.
                        # And maybe use simple reader and not DictRead, for efficiency.
                        var = tbl_fld_var[fld]
                        if var != id_var:
                            if doc_d[var]['fieldtype'] == "double":
                                data_d[var] = ny.r_[data_d[var], float(v)]
                            elif doc_d[var]['fieldtype'] == "int":
                                data_d[var] = ny.r_[data_d[var], int(v)]
            fp.close()

            if FLAGS['verbose']: 
                for var in doctbl_d[tbl]['varlst']: 
                    print("   ", var, "(", data_d[var].size, "):", data_d[var])


def write_var_arrays(doctbl_d, doc_d, data_d):
    """ 
    To write out variables to csv tables, use the compact
    writerows() csv writer method. One way to prepare the output numpy arrays
    for writing is to use zip(). eg, for 3 numpy arrays:
    a = ny.array([1,2])
    b = ny.array([10,20])
    c = ny.array([5,7])
    zip(a,b,c)
    [(1, 10, 5), (2, 20, 7)]
    
    fp = open("myfile.csv", "wb") # without the 'b', blank lines may be inserted
    writer = csv.writer(fp)
    writer.writerow(["fld1","fld2","fld3"])
    writer.writerows(zip(a,b,c))
    
    Getting the field order just right is a big deal.
    """
    import csv


    for tbl in doctbl_d:
        if len(doctbl_d[tbl]['varlst']) > 0:
            fldnameseq = []
            writeseq = []
            # remove vars that were never written out to the OUT dict
            # either by choice or by oversight. Alternatively, write out None?
            orderedflds = dict(list(zip(doctbl_d[tbl]['fieldorder'], doctbl_d[tbl]['varlst'])))
            for ord,var in sorted(orderedflds.items()): 
                if var in data_d and \
                var in doc_d and doc_d[var]['flgwrite']:
                    fldnameseq.append(doc_d[var]['fieldname'])
                    writeseq.append("data_d['" + var + "']")

            # write requested fields to csv table
            fp = open(doctbl_d[tbl]['filepath'], "w", newline='')
            csvwriter = csv.writer(fp)
            csvwriter.writerow(fldnameseq)
            csvwriter.writerows(eval("zip(" + ",".join(writeseq) + ")"))

            fp.close()


def cfg_outvars_order(fname_cfg_var, doctbl_d, doc_d):
    """
    Re-read vars.cfg\[OUT.VARS] using raw file access to extract the order of 
    each variable (ConfigParser doesn't return the order).
    1. Open cfg file and go to [OUT.VARS] line
    2. Read through all lines in that section (until EOF or start of next [] section)
    3. Throw away comment and blank lines (lines with nothing but white space)
    4. Step through var lines.
    5. For explicit vars, increment field order index
    6. For generic vars, expand into multiple vars, assign field order index based
       on previous var field order and parameter relative indices
       (build generic-var handling functionality latere, after developing the
        simpler field order extraction tools for explicit vars)
    7. Match each var name to a key in OUTDOC dict
    8. Update OUTDOC_TBL and OUTDOC dicts with the field order
    """

    # create a dictionary of genvarname vs. var names list from doc_d
    genvars_d = {}
    for var in doc_d:
        gv = doc_d[var]['genvarname']
        if gv:
            gvpar = doc_d[var]['genvar_p']
            if gv in genvars_d:
                genvars_d[gv]['p'].append(gvpar)
                genvars_d[gv]['var'].append(var)
            else:
                genvars_d[gv] = {}
                genvars_d[gv]['p'] = [gvpar]
                genvars_d[gv]['var'] = [var]

    # sort lists in the correct relative order using RUN['p'] & RUN['param_ord']
    for gv in genvars_d:
        if FLAGS['verbose']: print("genvars: ", gv, genvars_d[gv]['p'], genvars_d[gv]['var'])
        genvars_d[gv]['p'].sort(key=lambda p: RUN['param_ord'][RUN['p'].index(p)])
        genvars_d[gv]['var'].sort(key=lambda v: \
                RUN['param_ord'][RUN['p'].index(doc_d[v]['genvar_p'])])
        if FLAGS['verbose']: print("genvars sorted: ", gv, genvars_d[gv]['p'], genvars_d[gv]['var'])

    # open file, suck in all lines, close file
    f = open(fname_cfg_var, "r")
    cfg_lines = f.readlines()
    f.close()

    # remove leading/trailing whitespace and \n, remove blank and comment lines
    # Then go to sect_name line and extract only lines below it
    cfg_lines = [line.strip() for line in cfg_lines]
    cfg_lines = [ln for ln in cfg_lines if ln != '' and not ln.startswith("#")]
    sect_name = "[OUT.VARS]"
    sect_idx  = cfg_lines.index(sect_name)
    sect_lines = cfg_lines[sect_idx+1:]
    # maybe it's best to first search for EOF or the next section header?
    # though *initially*, I can safely assume this section is the last one!
    
    # assign field order for each var/tbl
    # use enumerate to extract var index (order) concurrently
    # extract varname from each var line (stripping leading/trailing whitespace)
    # THIS SCHEME PROBABLY BREAKS DOWN WITH MORE COMPLEX SETS OF TABLES & VARS!
    # ord_offset WILL PROBABLY GET OUT OF WHACK. EVALUATE AND FIX IT.
    # or maybe it's ok, just that the assigned fieldorder values are non-consecutive?
    ord_offset = 0
    for ordidx,line in enumerate(sect_lines):
        var = line.split("=")[0].strip()
        if var in genvars_d:
            # expand generic var names
            for varexp in genvars_d[var]['var']:
                for tblname in doc_d[varexp]['srctable']: 
                    varidx = doctbl_d[tblname]['varlst'].index(varexp)
                    doctbl_d[tblname]['fieldorder'][varidx] = ordidx + ord_offset
                    ord_offset += 1
        elif var in doc_d:
            for tblname in doc_d[var]['srctable']: 
                varidx = doctbl_d[tblname]['varlst'].index(var)
                doctbl_d[tblname]['fieldorder'][varidx] = ordidx + ord_offset
        else:
            # Generic variable name was not expanded because it's not being used.
            # The RUN parameters requested don't match the var parameter block.
            # Decrease order offset to maintain a proper sequental order index
            ord_offset -= 1


def ExportVar(varsave, varname, param=None):
    ''' Export variable (array) to the gloabl OUT dictionary, to make it
    available for writing out to files. If variable is actually a literal
    (single value) and not a full-length numpy array, expand it to full-length
    float32 numpy array using IN['BasinID'] to extract the length.
    If param is not None, the variable has a generic name and must be
    expanded.
    '''
    global OUT
    
    # expand to full-length array if variable is a literal or has length == 1
    # Better to use numpy tools? fill() after ny.empty(), or repeat()
    # [BUT ONLY IF IN['BasinID'].size > 1 AND dtype IS NOT A STRING (IE, NOT srcMax
    # ARRAYS)!!! IF IN['BasinID'].size == 1, VARIABLE STILL NEEDS TO BE CONVERTED 
    # TO NUMPY ARRAY IF IT'S A SCALAR!]
    ExpandToArrayFlg = False
    if ny.isscalar(varsave) or len(varsave) == 1:
        # Expand only if scalar or array is not a numpy string-type
        # (There are no foreseeable cases of string scalars that would be exported)
        # But must first test if variable is a numpy array!
        if isinstance(varsave, ny.ndarray):
            if 'string' not in varsave.dtype.name:
                ExpandToArrayFlg = True
        else:
            ExpandToArrayFlg = True
    
    if ExpandToArrayFlg:
        varsave = ny.array(varsave, dtype='float64') \
                  * ny.ones(IN['BasinID'].size)
        #varsave = ny.array(varsave, dtype='float32') \
    
    if param == None:
        OUT[varname] = varsave
    else:
        # generic var name
        OUT[param + varname] = varsave

    # The handling of generic var names will only work if the parameter
    # is the first element of the var name!! That's very limiting and
    # will need to be generalized


def cfg_simple_sections(steptype):
    global CCAL, RUN, BASAREA

    if steptype == "MODEL":
        sect_dict = read_cfgfile(fname_cfg_cal, "CAL")
        parse_cfg_ccal(sect_dict, CCAL)

        sect_dict = read_cfgfile(fname_cfg_var, "MODELRUN")
        parse_cfg_modelrun(sect_dict, RUN)
    elif steptype == "GIS2TBLS":
        sect_dict = read_cfgfile(fname_cfg_gis, "CREATEBASAREAS")
        parse_cfg_basrea(sect_dict, BASAREA)


def PopulateCfgVars(fname_cfg, steptype):
    """ Parse config file(s), load data into vars
    steptype: "GIS2TBLS" or "MODEL"
    """
    global INDOC_TBL, INDOC, IN, OUTDOC_TBL, OUTDOC, OUT

    strsubs = read_cfgfile(fname_cfg_gen, "STRSUBS")

    # IN sections and dictionaries
    sel = {'MODEL':    ('IN','TBLS','VARS'), \
           'GIS2TBLS': ('INGIS','FILES','GISVARS')}
    in_dict = read_cfgfile(fname_cfg, "IN")
    parse_cfg_tbls(in_dict[sel[steptype][1]], strsubs, INDOC_TBL, sel[steptype][0])
    parse_cfg_vars(in_dict[sel[steptype][2]], INDOC_TBL, INDOC, sel[steptype][0])

    # OUT sections and dictionaries
    out_dict = read_cfgfile(fname_cfg, "OUT")
    parse_cfg_tbls(out_dict['TBLS'], strsubs, OUTDOC_TBL, "OUT")
    parse_cfg_vars(out_dict['VARS'], OUTDOC_TBL, OUTDOC, "OUT")
    cfg_outvars_order(fname_cfg, OUTDOC_TBL, OUTDOC)

# ---- copied from dissolved.py -----

R_MIN = 0.003  # 3 mm/yr


def model_dissolved(run_forms):
    """ Dissolved nutrient form sub-models.
    """
    
    # nutrient form list is limited to dissolved and actual 
    # model run forms ('parameters') in RUN['F']
    for F in run_forms:
        # DSi is implemented as a separate, isolated function.
        if F == 'DIC':
            Yld_F = DICModel()   # Currently an empty function.
        elif F == 'DSi':
            Yld_F = DSiModel()
        else:
            # POINT (SEWAGE) SOURCES
            RSpnt_E, FEpnt_F = Calc_PointSources(F)
            RSpnt_F = FEpnt_F * RSpnt_E

            # DIFFUSE (NON-POINT) SOURCES
            # Calculate FEws_F, FEws_nat,F, f_F(Rnat)
            FEws_F, FEws_nat_F, f_F = Calc_WSExportFunc(F)
            
            # Diffuse River Sources: explicit
            WSdif_ant_E, WSdif_nat_E = Calc_WSdifExplicit(F)
            RSdif_expl_ant_F =     FEws_F * WSdif_ant_E
            RSdif_expl_nat_F = FEws_nat_F * WSdif_nat_E
            
            # Diffuse River Sources: export coefficient
            RSdif_ec_F = Calc_RSdifExportCoeff(f_F, F)
            if F == 'DOC':
                RSdif_ec_ant_F = 0.0
                RSdif_ec_nat_F = RSdif_ec_F
            else:
                Agfr = IN['agric'] / 100.0
                RSdif_ec_ant_F =      Agfr  * RSdif_ec_F
                RSdif_ec_nat_F = (1 - Agfr) * RSdif_ec_F
            
            # Total diffuse River Sources: anthropogenic vs. natural
            RSdif_ant_F = RSdif_expl_ant_F + RSdif_ec_ant_F
            RSdif_nat_F = RSdif_expl_nat_F + RSdif_ec_nat_F

            # DISSOLVED YIELD (kg/km2/yr)
            FEriv_F = Calc_FEriv(F)

            #RS_ant_F = RSpnt_F + RSdif_ant_F
            #RSdif_F  = RSdif_ant_F + RSdif_nat_F
            Yld_F = FEriv_F * (RSpnt_F + (RSdif_ant_F + RSdif_nat_F))


            # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
            # Some are saved into global OUT dictionary mainly for reuse in SourceContrib()
            ExportVar(RSdif_ec_ant_F, 'RSdif_ec_ant', F)
            ExportVar(RSdif_ec_nat_F, 'RSdif_ec_nat', F)
            ExportVar(RSdif_ant_F, 'RSdif_ant', F)
            ExportVar(RSdif_nat_F, 'RSdif_nat', F)
            ExportVar(RSpnt_F, 'RSpnt', F)


            # CALCULATE SOURCE CONTRIBUTIONS
            SourceContrib(F)

        # DISSOLVED LOAD (ton/yr, or Mg/yr)
        Ld_F = Yld_F * IN['A'] / 1000.0
        
        # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
        ExportVar(Yld_F, 'Yld', F)
        ExportVar(Ld_F, 'Ld', F)


def DSiModel():
    """ DSi model. A multiple linear regression model, from Beusen et al. (2009)
    """

    # Runoff must be in meters/yr, but current input is in mm/yr
    Rnat = IN['Rnat'] / 1000.0

    # Truncate (clip) input (independent) variables to the acceptable range 
    # before using in T_DSiyldNAT equation
    IndepVarsTruncate = lambda var,minval,maxval: IN[var].clip(min=minval,max=maxval)
    Precip     = IndepVarsTruncate('precip',0.519952,10.9972)
    GaezSlope  = IndepVarsTruncate('gslope',1.95543000000000,41.9841000000000)
    BulkDens   = IndepVarsTruncate('bulkdens',0.93677500000000,1.6459700000000)
    VolcLithFr = IndepVarsTruncate('frvolclith',0.00000000000000,0.7621180000000)

    # CALCULATE BOX-COX TRANSFORMED ("T_") YIELD (ton SiO2/km2/yr), pre-dam
    T_Yld_DSi_pred = 1.60765821573*log(Precip) + 0.03099949128*GaezSlope + \
                     -2.59587868714*BulkDens + 1.69157777610*VolcLithFr + 2.56118766111
    
    # CALCULATE UN-TRANSFORMED YIELD (ton SiO2/km2/yr)
    boxcox_lambda = 0.068623051867468
    Yld_DSi_pred = (boxcox_lambda*T_Yld_DSi_pred + 1) ** (1/boxcox_lambda)

    # Set Yld_DSi_pred to 0 in arid basins (Rnat < R_MIN)
    Yld_DSi_pred[Rnat < R_MIN] = 0.0
    
    # Set yield to 0 if bulk density is ~ 0
    Yld_DSi_pred[IN['bulkdens'] < 0.01] = 0.0

    # Unit conversion of yield, to kg Si/km2/yr
    Yld_DSi_pred *= 1000*(28.09/60.09)

    # Apply reservoir retention term (currently from TSS only)
    D_TSS = IN['D_TSS']
    Yld_DSi = (1 - D_TSS) * Yld_DSi_pred

    return Yld_DSi


def DICModel():
    """ DIC model. Function currently empty; DIC model development is being
    done elsewhere.
    """
    print("Blank DIC model function. DIC model development is being done elsewhere.")
    return 0


def Calc_PointSources(F):
    """ Calculate point source/sewage variables.
    """

    ccalf = CCAL[F]
    
    # element (N, P, C)
    E = F[-1]

    # FEpnt_F
    if F == 'DIN':
        # IN['hwfrem_N_aspct'] is in %, not 0-1
        hwfrem_E = IN['hwfrem_N_aspct'] / 100.0
        hwfrem_E_max = 0.8
        FEpnt_F = 0.485 + 0.255*(hwfrem_E/hwfrem_E_max)
    else:
        FEpnt_F = ccalf['c']

    # RSpntExc_E
    if E in ('N', 'P'):
        RSpntExc_E = IN['RSpntExc_'+E]
    else:
        RSpntExc_E = 0.0

    # RSpntDet_E
    if E == 'P':
        RSpntDet_E = IN['RSpntDet_P']
    else:
        RSpntDet_E = 0.0


    # RSpnt_E (total)
    RSpnt_E = RSpntExc_E + RSpntDet_E
    
    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    # Some are saved into global OUT dictionary mainly for reuse in SourceContrib()
    ExportVar(RSpntExc_E, 'RSpntExc_'+E, F)
    ExportVar(RSpntDet_E, 'RSpntDet_'+E, F)
    ExportVar(RSpnt_E, 'RSpnt_'+E, F)
    ExportVar(FEpnt_F, 'FEpnt', F)

    return RSpnt_E, FEpnt_F


def Calc_WSExportFunc(F):
    """ Calculate Watershed Export Fraction (land -> rivers)
    FEws_F is a function of 'natural' mean annual water runoff from land to streams (Rnat):
    FEws_F = e_F * f_F(Rnat)
    """

    ccalf = CCAL[F]
    Rnat = IN['Rnat'] / 1000.0 # Runoff must be in meters/yr, but input is in mm/yr

    # Calculate f_F runoff function
    if F in ('DIN', 'DON', 'DOP', 'DOC'):
        f_F = Rnat ** ccalf['a']
    else:  # DIP
        # Zero values will cause rattn to blow up (error) for DIP formulation,
        # where exponent is negative. More generally: f_F -> 0 as Rnat -> 0.
        # Net effect of setting near-zero Rnat values to a very low min value
        # is to set f_F ~ 0 as Rnat -> 0
        Rgt0 = Rnat
        Rgt0[Rnat < 0.00001] = 0.0000001
        f_F = 1/(1 + (Rgt0/ccalf['a']) ** -ccalf['b'])
    
    # Set f_F (and therefore FEws_F and FEws_nat_F) to 0 for arid basins, 
    # using the runoff threshold R_MIN (Rnat < R_MIN)
    # Point sources in N & P models can produce yield > 0 when Rnat = 0 (more 
    # generally, Rnat < R_MIN). But DOC model has no point sources, so yield = 0
    # when Rnat = 0 (Rnat < R_MIN). This creates an inconsistency for DOM yields.
    f_F[Rnat < R_MIN] = 0.0

    FEws_F = ccalf['e'] * f_F

    # Initialize FEws_nat_F to be identical to FEws_F.
    # Differentiation for DIN will be applied in the DIN block below.
    # copy() is needed to preserve FEws_F (numpy's default is copy-by-reference)
    FEws_nat_F = FEws_F.copy()

    # Enforcing a maximum value
    # This constraint was set for DIN only, but if this parameter is going to be
    # interpreted as a "Fraction Exported", logically it should be <= 1.
    # However, that's not how the other models where originally defined and calibrated.
    # In general, all models exhibit FEws_F < 1

    # For DIN, enforce max value for FEws_F and calculate final FEws_nat_F
    if F == 'DIN':
        FEws_F[FEws_F > 1.0] = 1.0

        # FEws_nat. Currently only applies
        # in basins predominantly in the Humid Tropics
        HumidTropicsMask = (IN['KoppenGrpAperc'] > 50)
        FEws_nat_F[HumidTropicsMask] = ccalf['enat'] * f_F[HumidTropicsMask]
        # This constraint is probably implicit, but enforcing
        # it explicitly is a good, safe practice
        FEws_nat_F[FEws_nat_F > 1.0] = 1.0
    
    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    ExportVar(FEws_F, 'FEws', F)
    ExportVar(FEws_nat_F, 'FEws_nat', F)

    return FEws_F, FEws_nat_F, f_F


def Calc_FEriv(F):
    """ Calculate River Export fraction (loss along the river network)
    from individual retention (loss) terms
    """

    # L_F, river retention
    if F == 'DIN':
        A = IN['A']
        L_F = 0.0605 * log(A) - 0.0443
        # Enforce max value
        L_F[L_F > 0.65] = 0.65
    else:
        L_F = 0

    # D_F, reservoir retention
    # Basin D_F values are pre-processed before use in GNE.
    # Calculated from each reservoir i, then aggregated to basin as:
    # D_F = (1/Q)Sum(i=1-n)[D_i_F * Q_i]
    if F == 'DIN':
        D_F = IN['D_DIN']
        # Enforce max value
        D_F[D_F > 0.965] = 0.965
    elif F == 'DIP':
        D_F = IN['D_DIP']
        # Enforce max value
        D_F[D_F > 0.85] = 0.85
    else:  # DON, DOP, DOC
        D_F = 0

    # FQrem, consumptive water use
    FQrem = IN['FQrem']
    
    # FEriv_F
    FEriv_F = (1 - L_F)*(1 - D_F)*(1 - FQrem)

    # Enforce FEriv_F max value
    # This constraint was originally set for DIN only, but if this parameter will
    # be interpreted as a "Fraction Exported", logically it should be <= 1.
    # However, that's not how the other models where defined and calibrated.
    if F == 'DIN':
        FEriv_F[FEriv_F > 1.0] = 1.0

    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    ExportVar(FEriv_F, 'FEriv', F)

    return FEriv_F


def Calc_RSdifExportCoeff(f_F, F):
    """ Diffuse River Sources: export coefficient
    """
    
    ccalf = CCAL[F]
    
    if F in ('DIP', 'DON', 'DOP'):
        EC_F = ccalf['EC']
        RSdif_ec_F = f_F * EC_F
    elif F == 'DIN':
        RSdif_ec_F = 0.0
    else:  # DOC
        Wfr = IN['W_pct'] / 100.0  # Wfr is expected to be a fraction (0-1)
        EC_wet_F, EC_dry_F = ccalf['EC_wet'], ccalf['EC_dry']
        RSdif_ec_wet_F = f_F * (     Wfr  * EC_wet_F)
        RSdif_ec_dry_F = f_F * ((1 - Wfr) * EC_dry_F)
        RSdif_ec_F = RSdif_ec_wet_F + RSdif_ec_dry_F

        # Save into global OUT dictionary for reuse in SourceContrib()
        ExportVar(RSdif_ec_wet_F, 'RSdif_ec_wet', F)
        ExportVar(RSdif_ec_dry_F, 'RSdif_ec_dry', F)

    return RSdif_ec_F


def Calc_WSdifExplicit(F):
    """ Diffuse River Sources: explicit
    """

    ccalf = CCAL[F]

    # element (N, P, C)
    E = F[-1]
    
    if E in ('N', 'P'): # DIN, DIP, DON, DOP
        WSdif_fe_E = IN['WSdif_fe_'+E]
        WSdif_ma_E = IN['WSdif_ma_'+E]
        WSdif_ex_E = IN['WSdif_ex_'+E]
        
        WSdif_ant_E = WSdif_fe_E + WSdif_ma_E - WSdif_ex_E
        WSdif_nat_E = 0.0
        if F == 'DIN':
            # WSdif_fix_E and WSdif_dep_E are each provided as two separate input files,
            # nat & agr (ant)
            WSdif_fix_ant_E = IN['WSdif_fix_ant_N']
            WSdif_dep_ant_E = IN['WSdif_dep_ant_N']
            WSdif_ant_E += WSdif_fix_ant_E + WSdif_dep_ant_E
            
            WSdif_fix_nat_E = IN['WSdif_fix_nat_N']
            WSdif_dep_nat_E = IN['WSdif_dep_nat_N']
            WSdif_nat_E = WSdif_fix_nat_E + WSdif_dep_nat_E

        # Enforce WSdif_ant_E min value for net inputs balance.
        # WSdif_nat_E is always >= 0
        WSdif_ant_E[WSdif_ant_E < 0.0] = 0  # 0.0
    else:  # DOC
        WSdif_ant_E = 0.0
        WSdif_nat_E = 0.0


    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    ExportVar(WSdif_ant_E, 'WSdif_ant_'+E, F)
    ExportVar(WSdif_nat_E, 'WSdif_nat_'+E, F)

    return WSdif_ant_E, WSdif_nat_E


# =====================================================================

def SourceContrib(F):
    """ Determine Source Distribution (apportionment) and dominant (max) source.
    """
    
    ccalf = CCAL[F]

    # element (N, P, C)
    E = F[-1]

    # Differentiate between retention from agricultural vs. natural sources
    # (though currently this is relevant only for DIN, and only 
    # in basins predominantly in the Humid Tropics
    FEriv      = OUT[F + 'FEriv']
    FErivws    = FEriv * OUT[F + 'FEws']
    FErivwsnat = FEriv * OUT[F + 'FEws_nat']

    RSdif_ant_F = OUT[F + 'RSdif_ant']
    RSdif_nat_F = OUT[F + 'RSdif_nat']

    YS1dif_ant_F = FEriv * RSdif_ant_F
    YS1dif_nat_F = FEriv * RSdif_nat_F
    YS1pnt_F     = FEriv * OUT[F + 'FEpnt'] * OUT[F + 'RSpnt_'+E]
    
    # coarse-level source attribution
    YS1MaxDict_F = {0:'YS1pnt', 1:'YS1dif_ant', 2:'YS1dif_nat'}
    YS1all = ny.vstack((YS1pnt_F, YS1dif_ant_F, YS1dif_nat_F))

    if E in ('N', 'P'):  # DIN, DIP, DON, DOP
        # Load variables that are used by all/most N & P models
        WSdif_fe_E = IN['WSdif_fe_'+E]
        WSdif_ma_E = IN['WSdif_ma_'+E]
        WSdif_ex_E = IN['WSdif_ex_'+E]

        # Calculate gross diffuse anthropogenic land inputs, WSdif_gross_ant_E
        # Account for cases where WSdif_gross_ant_E (expfr denominator) is 0
        if F == 'DIN':
            WSdif_gross_ant_E = OUT[F + 'WSdif_ant_'+E] + WSdif_ex_E
        else:
            WSdif_gross_ant_E = WSdif_fe_E + WSdif_ma_E
        
        expfr = ny.where(WSdif_gross_ant_E > 0.0, WSdif_ex_E/WSdif_gross_ant_E, 1.0)
        G = 1. - expfr
        # Impose "mass-balance" constraint on G
        # (equivalent to WSdif_ant_E[WSdif_ant_E < 0.0] = 0.0)
        G[G < 0.0] = 0.0

        YS2difMa_ant_F = (FErivws * WSdif_ma_E) * G
        YS2difFe_ant_F = (FErivws * WSdif_fe_E) * G

        YS2pntExc_F = FEriv * OUT[F + 'FEpnt'] * OUT[F + 'RSpntExc_'+E]

        if F == 'DIN':
            WSdif_fix_ant_E = IN['WSdif_fix_ant_N']
            WSdif_dep_ant_E = IN['WSdif_dep_ant_N']
            WSdif_fix_nat_E = IN['WSdif_fix_nat_N']
            WSdif_dep_nat_E = IN['WSdif_dep_nat_N']

            YS2difFix_ant_F = (FErivws * WSdif_fix_ant_E) * G
            YS2difDep_ant_F = (FErivws * WSdif_dep_ant_E) * G
            
            # "Natural" sources (no crop export to account for)
            YS2difFix_nat_F = FErivwsnat * WSdif_fix_nat_E
            YS2difDep_nat_F = FErivwsnat * WSdif_dep_nat_E
            
            # fine-level source attribution
            YS2MaxDict_F = {0:'YS2pntExc', 1:'YS2difFe_ant', 2:'YS2difMa_ant', 
                            3:'YS2difFix_ant', 4:'YS2difDep_ant',
                            5:'YS2difFix_nat', 6:'YS2difDep_nat'}
            YS2all = ny.vstack((YS2pntExc_F, YS2difFe_ant_F, YS2difMa_ant_F, 
                                YS2difFix_ant_F, YS2difDep_ant_F, 
                                YS2difFix_nat_F, YS2difDep_nat_F))
        else:  # DIP, DON, DOP
            # Weathering/"Leaching" from agricultural areas
            # at same rate as in natural systems
            YS2dif_ec_ant_F = FEriv * OUT[F + 'RSdif_ec_ant']

            # Weathering/"Leaching" from "natural" areas (no crop export)
            # For these nutrient forms, all diffuse inputs in natural areas 
            # is from YS1dif_nat_F
            YS2dif_ec_nat_F = YS1dif_nat_F

            # fine-level source attribution
            # Use different names for weathering and leaching
            if F == 'DIP':
                LchWth = 'Wth'
            else:
                LchWth = 'Lch'
            
            if F == 'DON':
                YS2MaxDict_F = {0:'YS2pntExc', 1:'YS2difFe_ant', 2:'YS2difMa_ant', 
                                3:'YS2dif'+LchWth+'_ant', 4:'YS2dif'+LchWth+'_nat'}
                YS2all = ny.vstack((YS2pntExc_F, YS2difFe_ant_F, YS2difMa_ant_F, 
                                    YS2dif_ec_ant_F, YS2dif_ec_nat_F))
            else:
                # YS2pntDet_F is 0 for N
                YS2pntDet_F = FEriv * OUT[F + 'FEpnt'] * OUT[F + 'RSpntDet_'+E]

                YS2MaxDict_F = {0:'YS2pntExc', 1:'YS2pntDet', 
                                2:'YS2difFe_ant', 3:'YS2difMa_ant', 
                                4:'YS2dif'+LchWth+'_ant', 5:'YS2dif'+LchWth+'_nat'}
                YS2all = ny.vstack((YS2pntExc_F, YS2pntDet_F, YS2difFe_ant_F, YS2difMa_ant_F,
                                    YS2dif_ec_ant_F, YS2dif_ec_nat_F))
    else: # DOC
        # just wetlands vs. non-wetlands (dry)
        YS2difWet_F = FEriv * OUT[F + 'RSdif_ec_wet']
        YS2difDry_F = FEriv * OUT[F + 'RSdif_ec_dry']

        YS2MaxDict_F = {0:'YS2difWet', 1:'YS2difDry'}
        YS2all = ny.vstack((YS2difWet_F, YS2difDry_F))


    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE

    # SELECT AND EXPORT MAX SOURCE
    # When all src* arrays are zero, srcMax is assigned the value "undef"
    YS2MaxIdx_F = YS2all.argmax(0)
    YS2Max_F = ny.array([YS2MaxDict_F[src] for src in YS2MaxIdx_F], dtype='|S15')
    YS2Max_F[YS2all.max(0) == 0] = 'undef'
    ExportVar(YS2Max_F, 'YS2Max', F)

    if E in ('N', 'P'):  # DIN, DIP, DON, DOP
        YS1MaxIdx_F = YS1all.argmax(0)
        YS1Max_F = ny.array([YS1MaxDict_F[src] for src in YS1MaxIdx_F], dtype='|S12')
        YS1Max_F[YS1all.max(0) == 0] = 'undef'
        ExportVar(YS1Max_F, 'YS1Max', F)

        ExportVar(YS1pnt_F, 'YS1pnt', F)
        ExportVar(YS1dif_ant_F, 'YS1dif_ant', F)
        ExportVar(YS1dif_nat_F, 'YS1dif_nat', F)

        ExportVar(YS2pntExc_F, 'YS2pntExc', F)
        if E == 'P':  # DIP, DOP
            ExportVar(YS2pntDet_F, 'YS2pntDet', F)

        ExportVar(YS2difMa_ant_F, 'YS2difMa_ant', F)
        ExportVar(YS2difFe_ant_F, 'YS2difFe_ant', F)
        if F == 'DIN':
            ExportVar(YS2difFix_ant_F, 'YS2difFix_ant', F)
            ExportVar(YS2difDep_ant_F, 'YS2difDep_ant', F)
            ExportVar(YS2difFix_nat_F, 'YS2difFix_nat', F)
            ExportVar(YS2difDep_nat_F, 'YS2difDep_nat', F)
        else:  # DIP, DON, DOP
            ExportVar(YS2dif_ec_ant_F, 'YS2dif'+LchWth+'_ant', F)
            ExportVar(YS2dif_ec_nat_F, 'YS2dif'+LchWth+'_nat', F)
    else: # DOC
        ExportVar(YS2difWet_F, 'YS2difWet', F)
        ExportVar(YS2difDry_F, 'YS2difDry', F)

# ---- copied from dissolved.py -----

# Minimum acceptable runoff (meters/yr), for erosion sources from arid basins
R_MIN = 0.003  # 3 mm/yr

# Maximum acceptable Yld_TSS_pred, approx. 2x the maximum observed TSS yield
# in the basins used to develop the regression model (Table A1 in Beusen et al 2005)
Yld_TSS_pred_MAX = 5000  # ton/km2/yr

def model_particulate(run_forms):
    """ Main body of particulates sub-models.
    """
    
    # Runoff must be in meters/yr, but current input is in mm/yr
    Rnat = IN['Rnat'] / 1000.0

    # Calculate Yld_TSS_pred and Yld_TSS, set to 0 in arid basins (Rnat < R_MIN),
    # and to Yld_TSS_pred_MAX if Yld_TSS_pred > Yld_TSS_pred_MAX
    D_TSS = IN['D_TSS']
    Yld_TSS_pred = Calc_Yld_TSS_pred()
    Yld_TSS_pred[Rnat < R_MIN] = 0.0
    Yld_TSS_pred[Yld_TSS_pred > Yld_TSS_pred_MAX] = Yld_TSS_pred_MAX

    Yld_TSS = (1 - D_TSS) * Yld_TSS_pred

    # No-data flag set when Yld_TSS = 0 or Rnat < R_MIN. Because Yld_TSS = 0 when
    # either Yld_TSS_pred = 0 or D_TSS = 1, both situations are accounted for.
    NoFluxFlg = ((Yld_TSS == 0) | (Rnat < R_MIN))
    
    # Yld_TSS is already in ton/km2/yr ...
    Ld_TSS = Yld_TSS * IN['A']

    # TSSc_pred is in mg/L: yield (Mg/km2/yr) / runoff (m/yr)  (1 L = 0.001 m3)
    # Unit conversions sort out great: (Mg/km2/yr)/(m/yr) = mg/L
    # TSSc_pred blows up when Rnat = 0, logTSSc_pred when Rnat = 0 or Yld_TSS_pred = 0.
    TSSc_pred = Yld_TSS_pred / Rnat
    logTSSc_pred = log10(TSSc_pred)

    # Correct for invalid cases (NoFluxFlg), which yield TSSpc_POC_pred errors
    TSSc_pred[NoFluxFlg] = 0
    Ld_TSS[NoFluxFlg] = 0

    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    ExportVar(Yld_TSS, 'Yld_TSS')
    ExportVar(Ld_TSS, 'Ld_TSS')
    ExportVar(TSSc_pred, 'TSSc_pred')


    # CALCULATE %POC FOR USE IN THE PN AND PP MODELS
    # At very low TSSc_pred values (~ < 0.025 mg/L), TSSpc_POC_pred goes above 50%.
    # But such low TSSc_pred never occur in global dataset.
    TSSpc_POC_pred = -0.160*logTSSc_pred**3 + 2.83*logTSSc_pred**2 - 13.6*logTSSc_pred + 20.3
    # The TSSpc_POC_pred vs logTSSc_pred relationship from Ludwig et al is a concave-up curve,
    # with a local min. at TSSc_pred = 2250 mg/L; TSSpc_POC_pred increases at higher TSSc_pred!
    # But that makes no physical sense, and Ludwig et al actually appear to have
    # drawn a horizontal line beyond that point in their Fig. 3. This bottoming
    # out of TSSpc_POC_pred at high TSS conc. is generally supported by the literature.
    # It could be implemented like this:   TSSpc_POC_pred[TSSc_pred > 2250] = 0.5
    # However, the Yld_TSS_pred_MAX implementations makes that unnecessary.
    TSSpc_POC_pred[NoFluxFlg] = 0

    # nutrient form list is limited to particulate and actual 
    # model run forms ('parameters') in RUN['F']
    for F in run_forms:

        # Calculate POC, PN, PP
        if F in ('POC', 'PN'):
            if F == 'POC':
                TSSpc_F_pred = TSSpc_POC_pred
            elif F == 'PN':
                TSSpc_F_pred  = 0.116*TSSpc_POC_pred - 0.019

            # Correct for invalid cases (NoFluxFlg), which give TSSpc_POC_pred errors.
            # Then calculate POC & PN yields (kg/km2/yr) and loads (ton/yr)
            TSSpc_F_pred[NoFluxFlg] = 0

            # PARTICULATE YIELD (kg/km2/yr) & LOAD (T/yr, or Mg/yr)
            # The Yld_F equation below is derived from these 3 equations:
            # Yld_TSS = (1 - D_TSS) * Yld_TSS_pred
            # Yld_F_pred = (TSSpc_F_pred/100)*(1000*Yld_TSS_pred)
            # Yld_F = (1 - D_TSS)*Yld_F_pred
            Yld_F = (TSSpc_F_pred/100)*(1000*Yld_TSS)
            Ld_F  = Yld_F * IN['A'] / 1000.0
        elif F == 'PP':
            # Pre-calculate POCload for use in the PP model equation (eq. 4).
            # In original PP equation (eq 4), POC and PP loads are in kg/yr,
            # not the usual ton/yr used in GNE for nutrient loads. Here,
            # a conversion factor is applied so Ld_F is in ton/yr.
            # POCload is calculated for "natural" conditions (pre-dam; no trapping).
            Ld_POC_pred_kgyr = 1000*(TSSpc_POC_pred/100)*Ld_TSS/(1 - D_TSS)  # in kg/yr
            Ld_F_pred = exp(-3.09614 + 1.001769*log(Ld_POC_pred_kgyr)) / 1000.0
            
            # PARTICULATE YIELD (kg/km2/yr) & LOAD (T/yr, or Mg/yr)
            # Now calculate Ld_F with sediment trapping
            Ld_F = (1 - D_TSS) * Ld_F_pred

            # Correct for invalid cases (NoFluxFlg), which give TSSpc_POC_pred and therefore
            # Ld_F & Yld_F errors. Then calculate PP yield (kg/km2/yr) & percent (%)
            Ld_F[NoFluxFlg] = 0

            Yld_F = 1000.0 * Ld_F / IN['A']
            TSSpc_F_pred = 100 * Yld_F / (1000*Yld_TSS)
            TSSpc_F_pred[NoFluxFlg] = 0


        # CN = (TSSpc_POC_pred/12)/(PNpct/14) # Molar C:N ratio; calculate C:P and N:P ratios?

        # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
        ExportVar(TSSpc_F_pred, 'TSSpc_pred', F)
        ExportVar(Yld_F, 'Yld', F)
        ExportVar(Ld_F, 'Ld', F)


def Calc_Yld_TSS_pred():
    """ Calculate pre-dam TSS yield, Yld_TSS_pred.
    """

    # Truncate (clip) input (independent) variables to the acceptable range 
    # before using in Yld_TSS_pred equation
    IndepVarsTruncate = lambda var,minval,maxval: IN[var].clip(min=minval,max=maxval)
    MargGrassPrc = IndepVarsTruncate('marggrass',0,84.6865)
    WetlnRicePrc = IndepVarsTruncate('wetlndrice',0,24.7206)
    FrnrPrecp    = IndepVarsTruncate('frnrprecp',0.854985,11.1682)
    FrnrSlope    = IndepVarsTruncate('frnrslope',1.1301,38.4531)

    # The input lithology variable corresponds to the class number of the
    # *dominant* lithology class in the basin (from Amiotte-Suchet et al, 2003)
    # 2=carbonate rocks, 3=shales, 4=plutonic/metamorphic (shield), 
    # 6=acid volcanic rock, 7=basalt
    # not used (?): 1=sand/sanstone, 5=gabbros, 8=ice
    # If the basin did not overlay on the lithology map, a "dummy" lithology
    # class number 8 (ice) was assigned. See LithologySlope.xls.
    LithoChemCoef = {1:0.0, 2:1.0379,  3:0.9037, 4:0.3125, \
                     5:0.0, 6:-2.0678, 7:0.6694, 8:0.0}
    # Map dominant lithology class number to corresponding coefficient
    LiClass = IN['LiClass']
    LithoChem = [LithoChemCoef[i] for i in LiClass]


    # YIELD (ton/km2/yr) & LOAD (ton/yr), where 1 ton = 1 Mg
    Yld_TSS_pred = exp(0.0301*MargGrassPrc + 0.1234*WetlnRicePrc + \
                   0.2933*FrnrPrecp + 0.1027*FrnrSlope + LithoChem + 0.5522)
    # Set yield to 0 if lithology class is 8 (see comments above)
    Yld_TSS_pred[LiClass == 8] = 0.0
    
    return Yld_TSS_pred

if __name__ == '__main__':
    main()
