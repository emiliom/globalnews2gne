# gngis2tbls.py
""" gncore.py
Global NEWS 2 model, GNE implementation.
This module implements the raster, GIS pre-processing functionality,
which currently relies on the ArcGIS GeoProcessing library.
Outline of functionality (somewhat outdated):

PARSE CONFIG FILE, gis2tbls.cfg
- create/populate global dictionaries

LOOP THROUGH GIS INPUT GRIDS
- Run zonalstats to create dbf tables
  * Multiply grid by global cellarea grid, areagrd
  * If grid includes a cell fraction (clfr*) grid scaling, apply it in
    the multiplication
  * Run zonalstatsastable

CREATE OUTPUT CSV TABLES
- Loop through each output table
- Load each dbf (zonalstats output)
- Join "mean" field in dbf to basinid field from basinstbl
  * Write a "jointables" function to do this
  * If a previous join has been done already, join current tbl
    to the output from the previous join (ie, build cumulative table)
  * If basinid is missing from dbf, add a zero or nodata value?
- Write out csv, with correct field order

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
5/17/2007
"""


import numpy as ny
from gncfg import *
import gncore

__version__ = '$Revision: 2010-01-18$'


coreINFILESvars = ('tblbasins','tblareas','grdbasins','grdarea')
#if var not in coreINFILESvars and not var.startswith('clfr'):


def LoadBasinIDArea(doctbl_d, data_d, out_data_d):
    ''' Load BasinID and BasinArea from csv tables into 
    IN['BasinID'] and IN['BasinArea'] numpy arrays
    Then copy IN['BasinID'] to OUT['BasinID'] numpy array,
    and IN['BasinArea'] to OUT['BasinArea'] numpy array if requested.
    Note that while IN will have a 'BasinArea' value (array),
    INDOC won't have a corresponding 'BasinArea' value.
    So, this is creating something of an exception...
    '''
    import csv
    from sets import Set as set

    # read csv table and load basinid field
    fp = open(doctbl_d['tblbasins']['filepath'], "rb")
    csvreader = csv.DictReader(fp)
    # Test to ensure field is present in the file, aborting if not present?
    data_d['BasinID'] = ny.array([int(row['BASINID']) for row in csvreader], \
                        dtype="int32")
    fp.close()

    # Copy to OUT['BasinID'] numpy array
    out_data_d['BasinID'] = data_d['BasinID']

    if not BASAREA['BasinAreas']['FLAG']:
        # Create set out of global BasinID's array
        setBasinID = set(data_d['BasinID'])

        # read csv table and load area field
        fp = open(doctbl_d['tblareas']['filepath'], "rb")
        csvreader = csv.DictReader(fp)
        # Test to ensure field is present in the file, aborting if not present?
        # As done in BasinStatsToOUTvarArrays(), retain only rows whose
        # Basin ID is in setBasinID.
        basarea_lst = [float(row['area']) for row in csvreader \
                       if int(row['BASINID']) in setBasinID]
        fp.close()

        data_d['BasinArea'] = ny.array(basarea_lst, dtype="float32")

        # Copy to OUT['BasinArea'] numpy array
        # Unlike out_data_d['BasinID'], writing this array to a csv table
        # is optional, so this array may never be used!
        out_data_d['BasinArea'] = data_d['BasinArea']


def CalcBasinStats(doctbl_d, doc_d):

    import os, os.path, shutil

    # Initialize the gp object to work between versions (9x vs 8x)
    try:
        import arcgisscripting
        gp = arcgisscripting.create()
    except:
        import win32com.client
        gp = win32com.client.Dispatch("esriGeoprocessing.GpDispatch.1")
    
    #try:
    gp.CheckOutExtension("Spatial")

    gp.Workspace = FPathTmpSpace 
    ValGrid   = "valgridtmp"
    ValGridCF = "valgridtmp0"
    ZoneGrid   = doctbl_d['grdbasins']['filepath']
    ClAreaGrid = doctbl_d['grdarea']['filepath']
    print "ZONALSTATS 0:", FPathTmpSpace, ZoneGrid, ClAreaGrid

    for var in doc_d:
        # perform zonal stats on "value" grids only
        grd_key = doc_d[var]['srctable'][0]
        ValRawGrid = doctbl_d[grd_key]['filepath']
        ValGridItem = doc_d[var]['fieldname']
        # write zonalstats dbf table to the Workspace
        # (is this path-joining step needed? Isn't the Workspace used?)
        outTbl = os.path.join(FPathTmpSpace, var + ".dbf")
        if os.path.exists(outTbl):
            os.remove(outTbl)

        print "ZONALSTATS:", var, ValRawGrid, ValGridItem, outTbl

        # Check for and include ValRawGrid item names other than "VALUE"
        if ValGridItem.upper() != "VALUE":
            ValRawGrid += '.' + ValGridItem
        
        # If CREATEBASAREA is requested, no area scaling is needed
        if BASAREA['BasinAreas']['FLAG']:
            # Perform zonal statistics
            gp.ZonalStatisticsAsTable_sa(ZoneGrid, "Value", ValRawGrid, outTbl, "DATA")
        else:
            # create a temporary (on-the-fly) grid that's the product of
            # the raw ValueGrid and one or two area scaling grids.
            # This temporary grid will be deleted once the zonal table is created
            gp.Times_sa(ValRawGrid, ClAreaGrid, ValGrid)
            if doc_d[var]['fieldtype'] == 'all':
                ValGridRun = ValGrid
            else:
                CFAreaGrid = doctbl_d[doc_d[var]['fieldtype']]['filepath']
                print "ZONALSTATS Cell Fr grid:", ValGrid, CFAreaGrid
                gp.Times_sa(ValGrid, CFAreaGrid, ValGridCF)
                # delete the temporary grid
                gp.Delete_management(ValGrid)
                ValGridRun = ValGridCF

            # Perform zonal statistics
            gp.ZonalStatisticsAsTable_sa(ZoneGrid, "Value", ValGridRun, outTbl, "DATA")

            # delete the temporary grid
            gp.Delete_management(ValGridRun)
    
    # Final GIS cleanup: delete info directory & log file
    # Otherwise the model run folder retains this litter...
    shutil.rmtree(os.path.join(".", "info"))
    logfile = os.path.join(".", "log")
    if os.path.exists(logfile):
        os.remove(logfile)

    #except:
    #    print gp.GetMessages()
    
    # delete geoprocessing object, just to be safe
    del gp


def BasinStatsToOUTvarArrays(doctbl_d, doc_d, data_d, in_data_d):
    ''' ....
    '''
    import os, os.path
    from operator import itemgetter
    from sets import Set as set
    import dbf

    # function to extract column i from 2D sequence; eg: acol2 = GetCol(a, 2)
    GetCol = lambda seq, i: map(itemgetter(i), seq)
    
    NoData = 0.0
    ExpFldsIdx = {'ID':0, 'mean':6, 'sum':8}
    IDIdx = 0

    # Create set out of global BasinID's array
    setBasinID = set(in_data_d['BasinID'])

    # Create list of OUT vars that are the result of zonalstats output
    # These varnames must be found in the IN vars as well, but can't be
    # one of ['BasinID', 'BasinArea']
    SetINvar, SetOUTvar = set(INDOC.keys()), set(OUTDOC.keys())
    SetCommon = SetINvar.intersection(SetOUTvar)
    commonvars = list(SetCommon.difference(['BasinID', 'BasinArea']))

    for var in commonvars:
        # Read temporary zonalstats dbf file
        # SrcTbl[2:] holds the table data (records as rows)
        # fieldnames = SrcTbl[0]   and     fieldspecs = SrcTbl[1]
        f_SrcTbl = os.path.join(FPathTmpSpace, var + ".dbf")
        f = open(f_SrcTbl, 'rb')
        SrcTbl = list(dbf.dbfreader(f))
        f.close()
        # Remove dbf file and associated ArcGIS XML metadata file
        os.remove(f_SrcTbl)
        os.remove(f_SrcTbl + ".xml")

        # Export basinid and basin stats (MEAN) fields to numpy arrays.
        # In the list-comprehension BasFlds statement, retain only rows
        # whose ID is found in the global BasinID's array
        stat = 'sum'
        BasFlds = [[row[ExpFldsIdx['ID']], float(row[ExpFldsIdx[stat]])] \
                for row in SrcTbl[2:] if row[ExpFldsIdx['ID']] in setBasinID]

        # Identify missing BasinID's, add them to array, insert corresponding
        # NoData value for missing BasinID's, then sort by BasinID
        basids = set(GetCol(BasFlds, IDIdx))
        missingbasids = setBasinID.difference(basids)
        BasFlds.extend(zip(missingbasids, [NoData] * len(missingbasids)))
        BasFlds.sort(key=itemgetter(IDIdx))

        # Convert to float32 numpy array and load into OUT
        print "    ", var, type(BasFlds), len(BasFlds), len(BasFlds[0]), BasFlds[0:5]
        data_d[var] = ny.array(GetCol(BasFlds, 1), dtype="float32")

        # For normal arrays (not basin areas), numpy-divide by basin area
        if not BASAREA['BasinAreas']['FLAG']:
            data_d[var] /= in_data_d['BasinArea']



if __name__ == '__main__':
    # These functions are here as a test only...
    # In reality, gngis2tbls.py can't be run by itself
    gncfg.cfg_simple_sections("GIS2TBLS")
    gncfg.PopulateCfgVars(fname_cfg_var, "GIS2TBLS")

    print __version__
