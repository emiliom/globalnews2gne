""" gncfg.py
Global NEWS 2 model, GNE implementation.
This module includes declarations for the primary global variables and 
data structures used in GNE/Global NEWS 2 models.
This includes the listing of nutrient forms (called "parameters" 
in this file and in GNE core", and abbreviated as "p") and
common nutrient form groupings such as by element (eg, "nitrogen").

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

1/18/2010: Removed extraneous comments, improved documentation for distribution.
10/16-24/2008: Added DSi parameter to PARAMETERS and PGRP dictionaries.
Added AllFormModel FLAGS key to support the optional use of model code file
allformmodel.py, called from globalnews.py, for model functionality performed
after all element form sub-models have been completed.
10/18/2007: Added DIC parameter to dictionaries
5/10/2007
"""


__version__ = '$Revision: 2010-01-18$'

#fpath_dev = r"N:\newsmodel\code"
fpath_dev = "."

# Configuration file names
fname_cfg_gen = "gensetup.cfg"
fname_cfg_cal = "constants.cfg"
fname_cfg_var = "vars.cfg"
fname_cfg_gis = "gis2tbls.cfg"

# Global, temporary working file path, to write intermediate files to
FPathTmpSpace = fpath_dev


# To be set in globalnews.py/main from command-line arg
# currently defined keys: "verbose", "AllFormModel"
# Add new keys: "debug", "warning"
FLAGS = {}

# Initialize/declare global dictionaries (for gis2tbls)
BASAREA = {}
"""
BASAREA['BasinAreas']
    ['FLAG']      (True/False)
    ['outtable']  (str)
    ['varname']   (str)
"""

# Initialize/declare global dictionaries
CCAL = {}
RUN = {}
INDOC_TBL = {}
INDOC = {}
IN = {}
# for writing out variables to tables, does it need a set of
# data structures completely parallel to the ones used for reading tables/vars?
# (INDOC_TBL, INDOC, IN) It looks that way...
OUTDOC_TBL = {}
OUTDOC = {}
OUT = {}

"""
CCAL[param][constant] (all floats, loaded from constants.cfg)
RUN['p']         (str param list)
RUN['param_ord'] (int list, base 0, though input in vars.cfg is base 1)
  param_ord gets reduced from an all-parameters interpretation to 
  the actual requested list of parameters, RUN['p']

INDOC/OUTDOC & INDOC_TBL/OUTDOC_TBL dictionaries
doc_d[varname]
    ['srctable']   (str list)
    ['fieldname']  (str)
    ['fieldtype']  (str)
    ['flgwrite']   (Bool)
    ['genvarname'] (str)
    ['genvar_p']   (str)

doctbl_d[tblname]
    ['varlst']     (str list)
    ['fieldorder'] (int list)
    ['filepath']   (str)
    ['basis']      (str)
"""

# parameter groupings dictionary ('aliases')
# (excluding TSS, because it's not treated as a true nutrient form)
# element (N,P,C) vs. organic (org,inorg,*total*) vs. phase (diss,part)
PARAMETERS = ('DIN','DIP','DIC','DSi','DON','DOP','DOC','PN','PP','POC')
PGRP = { \
'all':        PARAMETERS, \
'nitrogen':   ('DIN','DON','PN'), \
'phosphorus': ('DIP','DOP','PP'), \
'carbon':     ('DOC','DIC','POC'), \
'silicon':    ('DSi'), \
'inorganic':  ('DIN','DIP','DIC','DSi','PP'), \
'organic':    ('DON','DOP','DOC','POC','PN'), \
'dissolved':  ('DIN','DIP','DIC','DSi','DON','DOP','DOC'), \
'particulate':('POC','PN','PP') \
}
"""
Example of selectors/filters that can be applied on PARAMETERS:
 filter(lambda p: p[0] == 'D', PARAMETERS)
('DIN', 'DIP', 'DON', 'DOP', 'DOC')
 filter(lambda p: p[-1] == 'P', PARAMETERS)
('DIP', 'DOP', 'PP')
Can also use list comprehension.
"""