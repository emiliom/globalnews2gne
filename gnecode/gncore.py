""" gncore.py
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

1/18/2010: Added the standard module documentation text above.
10/16/2008
Changed floating-point I/O numpy array dtype from float32 to NumPy's default float64,
to avoid round-off errors. Changes applied to load_var_arrays() and ExportVar().
7/9/2008
Modified test for scalars or single-element lists/arrays in ExportVar(), to account
for model run cases where a single basin was requested, and the srcMax arrays 
(srcMax1 & srcMax2) are being exported. Previously, these were converted to numpy
arrays of float32 data type.
1/25-28/2008
Overhauled load_var_arrays() to allow basin sub-setting, based on the basin ID's
in the core input table that corresponds to the BasinID variable in vars.cfg.
First reads the list of basins ids, then as all other input variables are being read
(one basin row at a time), only variable values from table rows with Basin ID's in 
the BasinID set are loaded.
6/15/2007
"""



import numpy as ny
from gncfg import *

__version__ = '$Revision: 2010-01-18$'


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
    import ConfigParser

    cfg = ConfigParser.SafeConfigParser()
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
                    if FLAGS['verbose']: print " %s[%s][%s] = %s" %(sect_prefix, ssuf, opt, cfg_dict[ssuf][opt])
        elif section == sect_prefix:
            for opt,val in cfg.items(section):
                cfg_dict[opt] = val
                if FLAGS['verbose']: print " %s[%s] = %s" %(section, opt, cfg_dict[opt])

    
    return cfg_dict


def parse_cfg_ccal(ccal_cfg_d, ccal_d):
    """ Populate global CCAL dictionary
    """

    for k1 in ccal_cfg_d.keys():
        ccal_d[k1] = {}
        for k2,val in ccal_cfg_d[k1].items():
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
        elif vallst[0] in PGRP.keys():
            run_d['p'] = list(PGRP[vallst[0]]) # convert tuple to list
        else:
            if FLAGS['verbose']: print "Generic var name: parameter sepecifier %s not valid" % (vallst[0])
    else:
        run_d['p'] = vallst

    # Parse variable param_ord
    run_d['param_ord'] = []
    vallst = mrun_cfg_d['param_ord'].split(',')
    for idx, v in enumerate(vallst):
        if PGRP['all'][idx] in run_d['p']:
            # assign order index, converting from base 1 to base 0
            run_d['param_ord'].append(int(v) - 1)

    
    if FLAGS['verbose']: print run_d


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

    if FLAGS['verbose']: print "BASAREA:  ", basarea_cfg_d['BasinAreas']


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
    for tblname,val in tbls.items():
        vlist = val.split("|")
    
        # later, the basis for doctype == "OUT" might be made optional?
        if len(vlist) != vlist_len[doctype]:
            if FLAGS['verbose']: print "%s: Tables must have exactly %d arguments.\n" %(tblname, vlist_len[doctype])
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
            if FLAGS['verbose']: print tblname,doctbl_d[tblname]['filepath']
        else:
            doctbl_d[tblname]['filepath'] = vlist[0]
        
        if doctype == "IN":
            # test to see if the file exists
            if not os.path.exists(doctbl_d[tblname]['filepath']):
                if FLAGS['verbose']: print "Table does not exist: %s\n" %(doctbl_d[tblname]['filepath'])
                # Now exit.

            # Add basis item (check for valid values)
            basis_valid = ('basin', 'nation', 'table', 'grid')
            if vlist[1] in basis_valid:
                doctbl_d[tblname]['basis'] = vlist[1]
            else:
                if FLAGS['verbose']: print "Table %s: basis '%s' is not recognized; must be (%s).\n" \
                      %(tblname, vlist[1], ','.join(basis_valid))
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

    for varname,val in vars.items():
        vlist = val.split("|")

        if len(vlist) != vlist_len[doctype]:
            # for doctype "OUT", flgwrite 'Y' is assumed if it's ommitted
            if doctype == "OUT" and len(vlist) == vlist_len[doctype] - 1:
                vlist.append('Y')
            else:
                if FLAGS['verbose']: print "%s: Variable must have exactly %d arguments.\n" \
                                 %(varname, vlist_len[doctype])
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
                        elif params_in[0] in PGRP.keys():
                            # extract parameters from param group, convert to list
                            params = list(PGRP[params_in[0]])
                        else:
                            print "Generic var name: parameter sepecifier %s not valid" % (params_in[0])
                    else:
                        # should do error check, to ensure parameters are valid
                        params = params_in
                else:
                    print "Error with generic var name!"
                if FLAGS['verbose']: print strblock['b'],params, "\n"

                # Parse and expand fieldname, if it, too, is generic
                # A generic varname doesn't require a corresponding generic fieldname
                ParseStrBlock("<>", vlist[1], strblock)
                if strblock['b'] == 'p':
                    IsGenericFldName = True
                    fldname0, fldnamef = (strblock['0'], strblock['f'])
                else:
                    IsGenericFldName = False
                    if FLAGS['verbose']:
                      print ">WARNING: For generic var name, field name is not generic"

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
            print tblname, doctbl_d[tblname]['varlst']


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
            print "Variable %s: fieldtype '%s' is not recognized; must be 'double' or 'int'.\n" %(varname, fldtype)
            # Now exit.
    elif dattype == "gis": # here, fldtype is really the cell fraction grid, if any
        if fldtype == 'all' or fldtype.startswith('clfr'):
            docd[varname]['fieldtype'] = fldtype
        else:
            print "Variable %s: fieldtype '%s' is not recognized; must be 'all' or 'clfr*'.\n" %(varname, fldtype)
            # Now exit.

    # add variable to corresponding variable list for table(s)
    for tblname in docd[varname]['srctable']: 
        doctbld[tblname]['varlst'].append(varname)

    if FLAGS['verbose']: print "docd assignments: ",varname,docd[varname]['genvarname'], \
        docd[varname]['srctable'],docd[varname]['fieldname'],docd[varname]['fieldtype']


def load_var_arrays(doctbl_d, doc_d, data_d, out_data_d):
    """ Data array will be populated into data_d[varname]
    Open each table, load each requested fields and map them to variables.
    Variables will be numpy arrays.
    """
    import csv
    from sets import Set as set

    # =====================================================
    # LOAD AND HANDLE BasinID VARIABLE
    # Basin sub-setting functionality is included.
    id_var = 'BasinID'
    id_fldname, id_tblname = doc_d[id_var]['fieldname'], doc_d[id_var]['srctable'][0]
    
    # read csv table and load BasinID variable
    fp = open(doctbl_d[id_tblname]['filepath'], "rb")
    basinid_lst = [int(row[id_fldname]) for row in csv.DictReader(fp)]
    fp.close()

    # Convert to int32 numpy array and load into IN
    data_d[id_var] = ny.array(basinid_lst, dtype="int32")

    # Create set out of global BasinID's array
    # For use in basin sub-setting as input variables/tables are read in (below)
    setBasinID = set(data_d[id_var])

    # Copy to OUT[id_var] numpy array
    out_data_d[id_var] = data_d[id_var]
    
    if FLAGS['verbose']: print "  Number of basins to be processed: %d" % data_d[id_var].size

    # =====================================================
    # LOAD ALL OTHER INPUT VARIABLES, STEPPING THROUGH INDIVIDUAL INPUT TABLES
    for tbl in doctbl_d.keys():
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
            if FLAGS['verbose']: print "tbl_fld_var: ", tbl_fld_var

            # Read the first row (field names)
            fp = open(doctbl_d[tbl]['filepath'], "rb")
            fld_names_reader = csv.reader(fp)
            fld_names = fld_names_reader.next()
            fp.close()

            # Set basinid_fld using the header (field names) reader list
            # id_fldnames_lst is a list of expected basin id field names
            id_fldnames_lst = ['basinid', 'BASINID']
            if id_fldnames_lst[0] in fld_names:
                basinid_fld = id_fldnames_lst[0]
            elif id_fldnames_lst[1] in fld_names:
                basinid_fld = id_fldnames_lst[1]
            else:
                print "  !!! Input table does not have a valid basin ID column name !!!\n"

            # read csv table and load requested fields
            fp = open(doctbl_d[tbl]['filepath'], "rb")
            csvreader = csv.DictReader(fp)
            # SHOULD THERE BE A TEST TO ENSURE THAT ALL REQUESTED FIELDS
            # ARE PRESENT IN THE FILE? OTHERWISE, ABORT WITH ERROR MESSAGE
            for row in csvreader:
                for fld,v in row.items():
                    if int(row[basinid_fld]) in setBasinID and fld in tbl_fld_var.keys():
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
                    print "   ", var, "(", data_d[var].size, "):", data_d[var]


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
            orderedflds = dict(zip(doctbl_d[tbl]['fieldorder'], doctbl_d[tbl]['varlst']))
            for ord,var in sorted(orderedflds.items()): 
                if data_d.has_key(var) and \
                doc_d.has_key(var) and doc_d[var]['flgwrite']:
                    fldnameseq.append(doc_d[var]['fieldname'])
                    writeseq.append("data_d['" + var + "']")

            # write requested fields to csv table
            fp = open(doctbl_d[tbl]['filepath'], "wb")
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
            if genvars_d.has_key(gv):
                genvars_d[gv]['p'].append(gvpar)
                genvars_d[gv]['var'].append(var)
            else:
                genvars_d[gv] = {}
                genvars_d[gv]['p'] = [gvpar]
                genvars_d[gv]['var'] = [var]

    # sort lists in the correct relative order using RUN['p'] & RUN['param_ord']
    for gv in genvars_d:
        if FLAGS['verbose']: print "genvars: ", gv, genvars_d[gv]['p'], genvars_d[gv]['var']
        genvars_d[gv]['p'].sort(key=lambda p: RUN['param_ord'][RUN['p'].index(p)])
        genvars_d[gv]['var'].sort(key=lambda v: \
                RUN['param_ord'][RUN['p'].index(doc_d[v]['genvar_p'])])
        if FLAGS['verbose']: print "genvars sorted: ", gv, genvars_d[gv]['p'], genvars_d[gv]['var']

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



if __name__ == '__main__':
    # These functions are here as a test only...
    # In reality, gncore.py can't be run by itself
    cfg_simple_sections("MODEL")
    PopulateCfgVars(fname_cfg_var, "MODEL")

    print __version__
